"""
A zero-shot agent that uses a foundation model to make decisions.
The prompt includes no examples of past battles, team/move priors, or common combinations,
but does include historical actions from the current battle.
"""

import os
from typing import Dict, Optional

import litellm
from google.adk.agents import LlmAgent
from google.adk.planners import BuiltInPlanner
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, InMemorySessionService, Session
from google.genai import types

from python.agents.agent_interface import Agent
from python.agents.battle_action_generator import (
    BattleActionGenerator,
    BattleActionResponse,
)
from python.agents.tools.get_object_game_data import get_object_game_data
from python.agents.tools.llm_event_logger import LlmEventLogger
from python.agents.zero_shot.zero_shot_prompt_builder import ZeroShotPromptBuilder
from python.game.data.game_data import GameData
from python.game.environment.battle_stream_store import BattleStreamStore
from python.game.interface.battle_action import BattleAction
from python.game.schema.battle_state import BattleState

# Configure LiteLLM global retry settings for rate limit handling
# LiteLLM automatically uses exponential backoff for rate limits
litellm.num_retries = 5


def _load_static_system_instruction(mode: str = "gen9ou") -> str:
    """Load static system instruction from markdown files.

    This loads the static portions of the prompt (game rules, mechanics, output format)
    without any turn-specific data. Turn-specific data should be provided in the
    user message instead.

    Args:
        mode: Battle mode (e.g., "gen9ou"). Defaults to "gen9ou".

    Returns:
        Static system instruction with mode rules and examples embedded.

    Raises:
        FileNotFoundError: If prompt files are not found.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prompts_dir = os.path.join(current_dir, "..", "prompts")

    base_prompt_path = os.path.join(prompts_dir, "zero_shot_agent.md")
    with open(base_prompt_path, "r", encoding="utf-8") as f:
        base_prompt = f.read()

    mode_prompt_path = os.path.join(prompts_dir, "modes", f"{mode}.md")
    with open(mode_prompt_path, "r", encoding="utf-8") as f:
        mode_rules = f.read()

    examples_path = os.path.join(prompts_dir, "battle_action_examples.md")
    with open(examples_path, "r", encoding="utf-8") as f:
        battle_examples = f.read()

    system_instruction = base_prompt.replace("{{MODE_RULES}}", mode_rules)
    system_instruction = system_instruction.replace(
        "{{BATTLE_ACTION_EXAMPLES}}", battle_examples
    )

    return system_instruction


class ZeroShotAgent(Agent):
    """Zero-shot LLM agent that uses current battle history but no prior battle data."""

    def __init__(
        self,
        session_service: BaseSessionService = InMemorySessionService(),
        model_name: str = "openrouter/google/gemini-2.5-flash-lite-preview-09-2025",
        mode: str = "gen9ou",
        past_actions_count: int = 5,
        max_retries: int = 3,
    ):
        """Initialize the zero-shot agent.

        Args:
            model_name: LiteLLM model name
            mode: Battle mode for loading mode-specific rules (default: "gen9ou")
            max_retries: Maximum number of retries for invalid actions (default: 2)
        """
        self._model_name: str = model_name
        self._app_name: str = "zero_shot_pokemon_trainer_agent"
        self._game_data: GameData = GameData()
        self._max_retries: int = max_retries
        self._battle_room_to_logger: Dict[str, LlmEventLogger] = {}
        self._battle_room_to_session: Dict[str, Session] = {}
        self._battle_room_to_action_generator: Dict[str, BattleActionGenerator] = {}
        self._session_service: BaseSessionService = session_service
        self._past_actions_count: int = past_actions_count
        self._system_instruction: str = _load_static_system_instruction(mode)
        self._agent: LlmAgent = self._create_llm_agent(
            model_name, self._app_name, self._system_instruction
        )

    def _create_llm_agent(self, model_name, app_name, system_instructions) -> LlmAgent:
        def tool_get_object_game_data(name: str) -> str:
            """Look up game data for Pokemon, Move, Ability, Item, or Nature.

            Returns detailed stats, types, effects, and descriptions. Use to check:
            type matchups, move power/effects, ability mechanics, item effects.

            Args:
                name: Object name (e.g., "Landorus", "Earthquake", "Intimidate", "Choice Scarf")
            """
            return get_object_game_data(name, self._game_data)

        return LlmAgent(
            model=LiteLlm(model=model_name),
            name=app_name,
            instruction=system_instructions,
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    include_thoughts=True,
                    thinking_budget=1024,
                )
            ),
            include_contents="none",
            tools=[tool_get_object_game_data],
            output_schema=BattleActionResponse,
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
        )

    def _get_action_generator(
        self, battle_room: str, player_name: str
    ) -> BattleActionGenerator:
        """Get a action generator for a battle room."""
        if battle_room not in self._battle_room_to_action_generator:
            runner = Runner(
                agent=self._agent,
                app_name=self._app_name,
                session_service=self._session_service,
            )
            logger = LlmEventLogger(
                player_name=player_name,
                model_name=self._model_name,
                battle_room=battle_room,
            )
            self._battle_room_to_action_generator[battle_room] = BattleActionGenerator(
                runner=runner,
                logger=logger,
            )
            logger.log_system_instruction(
                turn_number=0, instruction=self._system_instruction
            )
        return self._battle_room_to_action_generator[battle_room]

    async def choose_action(
        self,
        state: BattleState,
        battle_room: str,
        battle_stream_store: BattleStreamStore,
    ) -> BattleAction:
        """Choose a battle action using LLM reasoning with retry logic.

        Args:
            state: Current battle state
            battle_room: Battle room identifier
            battle_stream_store: BattleStreamStore with all battle events

        Returns:
            BattleAction chosen by the LLM

        Raises:
            ValueError: If LLM fails after max retries or returns invalid action
        """
        if state.our_player_id is None:
            raise ValueError("our_player_id must be set in the battle state")
        opponent_player_id = "p2" if state.our_player_id == "p1" else "p1"

        session = self._battle_room_to_session.get(battle_room)
        if session is None:
            session = await self._session_service.create_session(
                app_name=self._app_name,
                user_id=battle_room,
            )
            self._battle_room_to_session[battle_room] = session

        turn_context = ZeroShotPromptBuilder(battle_stream_store).build_turn_context(
            state, opponent_player_id
        )
        content = types.Content(
            parts=[types.Part(text=turn_context)],
            role="player_" + state.our_player_id,
        )
        action_generator = self._get_action_generator(
            battle_room, state.player_usernames[state.our_player_id]
        )
        action = await action_generator.generate_action(
            user_query=content,
            state=state,
            user_id=battle_room,
            session_id=session.id,
            max_retries=self._max_retries,
        )
        return action

    async def retry_action_on_server_error(
        self,
        error_text: str,
        state: BattleState,
        battle_room: str,
        battle_stream_store: BattleStreamStore,
    ) -> Optional[BattleAction]:
        return await self.choose_action(state, battle_room, battle_stream_store)

    async def cleanup_battle(self, battle_room: str) -> None:
        if battle_room in self._battle_room_to_logger:
            self._battle_room_to_logger[battle_room].close()
            del self._battle_room_to_logger[battle_room]
        if battle_room in self._battle_room_to_session:
            await self._session_service.delete_session(
                app_name=self._app_name,
                user_id=battle_room,
                session_id=self._battle_room_to_session[battle_room].id,
            )
            del self._battle_room_to_session[battle_room]
        if battle_room in self._battle_room_to_action_generator:
            del self._battle_room_to_action_generator[battle_room]
