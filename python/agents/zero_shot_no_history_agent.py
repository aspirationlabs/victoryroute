"""
A zero-shot agent that uses a foundation model to make decisions.
The prompt includes no examples of past battles, team/move priors, common combinations, etc.
"""

import json
import os
from collections import defaultdict
from typing import Any, Dict, List

import litellm
from google.adk.agents import LlmAgent
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
from python.game.data.game_data import GameData
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
    prompts_dir = os.path.join(current_dir, "prompts")

    base_prompt_path = os.path.join(prompts_dir, "zero_shot_no_history_agent.md")
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


class ZeroShotNoHistoryAgent(Agent):
    """Zero-shot LLM agent with no historical battle data."""

    def __init__(
        self,
        session_service: BaseSessionService = InMemorySessionService(),
        model_name: str = "openrouter/google/gemini-2.5-flash-lite-preview-09-2025",
        mode: str = "gen9ou",
        max_retries: int = 3,
        reuse_sessions: bool = False,
    ):
        """Initialize the zero-shot agent.

        Args:
            model_name: LiteLLM model name
            mode: Battle mode for loading mode-specific rules (default: "gen9ou")
            max_retries: Maximum number of retries for invalid actions (default: 2)
        """
        self._app_name: str = "zero_shot_no_history_agent"
        self._model_name: str = model_name
        self._mode: str = mode
        self._game_data: GameData = GameData()
        self._max_retries: int = max_retries
        self._battle_room_to_logger: Dict[str, LlmEventLogger] = {}
        self._battle_room_to_session: Dict[str, Session] = {}
        self._battle_room_to_actions: Dict[str, List[BattleAction]] = defaultdict(list)
        self._system_instruction: str = _load_static_system_instruction(mode=mode)
        self._session_service: BaseSessionService = session_service
        self._reuse_sessions: bool = reuse_sessions

    def _format_past_actions(
        self,
        actions: List[BattleAction],
        our_player_id: str,
    ) -> str:
        """Format past actions as XML for inclusion in prompt.

        Args:
            actions: List of BattleAction objects for this battle
            our_player_id: Our player ID (p1 or p2)

        Returns:
            XML-formatted string of past actions
        """
        if not actions:
            return "No actions have been taken yet in this battle."

        lines = ["<past_actions>"]
        lines.append(f"<{our_player_id}>")

        for turn_idx, action in enumerate(actions, start=1):
            action_json = json.dumps(
                {
                    "action_type": action.action_type.value,
                    "move_name": action.move_name,
                    "switch_pokemon_name": action.switch_pokemon_name,
                    "mega": action.mega,
                    "tera": action.tera,
                    "team_order": action.team_order,
                }
            )
            lines.append(f"<turn_{turn_idx}>{action_json}</turn_{turn_idx}>")

        lines.append(f"</{our_player_id}>")
        lines.append("</past_actions>")

        return "\n".join(lines)

    def _format_available_actions(self, state: BattleState) -> str:
        """Format available actions as JSON string.

        Args:
            state: Current battle state

        Returns:
            JSON formatted string of available actions
        """
        available_actions: Dict[str, Any] = {
            "moves": state.available_moves,
            "switches": state.available_switches,
            "can_mega": state.can_mega,
            "can_tera": state.can_tera,
            "can_dynamax": state.can_dynamax,
            "force_switch": state.force_switch,
            "team_preview": state.team_preview,
        }
        return json.dumps(available_actions)

    def _format_turn_context(
        self,
        state: BattleState,
        turn_number: int,
        past_actions_xml: str,
    ) -> str:
        """Format turn-specific context for the user message.

        Args:
            state: Current battle state
            turn_number: Current turn number
            past_actions_xml: Formatted past actions

        Returns:
            Formatted user message with all turn-specific context
        """
        available_moves_data = self._format_available_actions(state)

        parts = [
            f"=== Turn {turn_number} - Choose Your Action ===",
            "",
            f"Your Player ID: {state.our_player_id}",
            "",
            "Available Actions This Turn:",
            available_moves_data,
            "",
            "Current Battle State:",
            str(state),
            "",
            "Past Actions This Battle:",
            past_actions_xml,
            "",
            "Based on the available actions above, choose your optimal battle action and return it as JSON.",
        ]

        return "\n".join(parts)

    async def choose_action(
        self, state: BattleState, game_data: GameData, battle_room: str
    ) -> BattleAction:
        """Choose a battle action using LLM reasoning with retry logic.

        Args:
            state: Current battle state
            game_data: Game data for lookups
            battle_room: Battle room identifier

        Returns:
            BattleAction chosen by the LLM

        Raises:
            ValueError: If LLM fails after max retries or returns invalid action
        """

        def tool_get_object_game_data(name: str) -> str:
            """Look up game data for Pokemon, Move, Ability, Item, or Nature.

            Returns detailed stats, types, effects, and descriptions. Use to check:
            type matchups, move power/effects, ability mechanics, item effects.

            Args:
                name: Object name (e.g., "Landorus", "Earthquake", "Intimidate", "Choice Scarf")
            """
            return get_object_game_data(name, game_data)

        if state.our_player_id is None:
            raise ValueError("our_player_id must be set in the battle state")

        if battle_room not in self._battle_room_to_logger:
            logger = LlmEventLogger(
                player_name=state.player_usernames[state.our_player_id],
                model_name=self._model_name,
                battle_room=battle_room,
            )
            self._battle_room_to_logger[battle_room] = logger
            # Log system instruction once at battle start
            logger.log_system_instruction(
                turn_number=0, instruction=self._system_instruction
            )
        logger = self._battle_room_to_logger[battle_room]

        session = self._battle_room_to_session.get(battle_room)
        if session is None:
            session = await self._session_service.create_session(
                app_name=self._app_name,
                user_id=battle_room,
            )
            if self._reuse_sessions:
                self._battle_room_to_session[battle_room] = session

        # TODO: Add past actions from the opponent too.
        past_actions = self._battle_room_to_actions[battle_room]
        past_actions_xml = self._format_past_actions(past_actions, state.our_player_id)
        turn_number = state.field_state.turn_number if state.field_state else 0
        llm_agent = LlmAgent(
            model=LiteLlm(model=self._model_name),
            name=self._app_name,
            instruction=self._system_instruction,
            tools=[tool_get_object_game_data],
            output_schema=BattleActionResponse,
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
        )
        runner = Runner(
            agent=llm_agent,
            app_name=self._app_name,
            session_service=self._session_service,
        )
        turn_context = self._format_turn_context(state, turn_number, past_actions_xml)
        content = types.Content(
            parts=[types.Part(text=turn_context)],
            role="user",
        )
        action_generator = BattleActionGenerator(runner=runner, logger=logger)
        action = await action_generator.generate_action(
            user_query=content,
            state=state,
            user_id=battle_room,
            session_id=session.id,
            max_retries=self._max_retries,
        )
        self._battle_room_to_actions[battle_room].append(action)

        return action

    async def cleanup_battle(self, battle_room: str) -> None:
        """Clean up resources for a completed battle.

        This should be called when a battle ends to free up memory.

        Args:
            battle_room: The battle room identifier to clean up
        """
        if battle_room in self._battle_room_to_logger:
            self._battle_room_to_logger[battle_room].close()
            del self._battle_room_to_logger[battle_room]

        if battle_room in self._battle_room_to_actions:
            del self._battle_room_to_actions[battle_room]

        if battle_room in self._battle_room_to_session:
            await self._session_service.delete_session(
                app_name=self._app_name,
                user_id=battle_room,
                session_id=self._battle_room_to_session[battle_room].id,
            )
            del self._battle_room_to_session[battle_room]
