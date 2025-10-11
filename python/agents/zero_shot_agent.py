"""
A zero-shot agent that uses a foundation model to make decisions.
The prompt includes no examples of past battles, team/move priors, or common combinations,
but does include historical actions from the current battle.
"""

import json
import os
from dataclasses import asdict
from enum import Enum
from typing import Any, Dict, Optional

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
    prompts_dir = os.path.join(current_dir, "prompts")

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
        reuse_sessions: bool = False,
    ):
        """Initialize the zero-shot agent.

        Args:
            model_name: LiteLLM model name
            mode: Battle mode for loading mode-specific rules (default: "gen9ou")
            max_retries: Maximum number of retries for invalid actions (default: 2)
        """
        self._app_name: str = "zero_shot_agent"
        self._model_name: str = model_name
        self._mode: str = mode
        self._game_data: GameData = GameData()
        self._max_retries: int = max_retries
        self._battle_room_to_logger: Dict[str, LlmEventLogger] = {}
        self._battle_room_to_session: Dict[str, Session] = {}
        self._system_instruction: str = _load_static_system_instruction(mode=mode)
        self._session_service: BaseSessionService = session_service
        self._reuse_sessions: bool = reuse_sessions
        self._past_actions_count: int = past_actions_count

    def _format_past_actions_from_store(
        self,
        store: BattleStreamStore,
        our_player_id: str,
        opponent_player_id: str,
        past_turns: int = 5,
    ) -> str:
        """Format past actions from BattleStreamStore as XML for inclusion in prompt.

        Args:
            store: BattleStreamStore containing battle events
            our_player_id: Our player ID (p1 or p2)
            opponent_player_id: Opponent player ID (p1 or p2)
            past_turns: Number of past turns to include (default: 5)

        Returns:
            XML-formatted string of past actions for both players
        """
        our_actions = store.get_past_battle_actions(our_player_id, past_turns=0)
        opponent_actions = store.get_past_battle_actions(
            opponent_player_id, past_turns=0
        )

        if not our_actions and not opponent_actions:
            return "No actions have been taken yet in this battle."

        all_turn_ids = sorted(set(our_actions.keys()) | set(opponent_actions.keys()))
        recent_turn_ids = (
            all_turn_ids[-past_turns:]
            if len(all_turn_ids) > past_turns
            else all_turn_ids
        )

        if not recent_turn_ids:
            return "No actions have been taken yet in this battle."

        def format_player_actions(player_id: str, actions: Dict[int, list]) -> list:
            """Format actions for a single player."""
            lines = [f"<{player_id}>"]
            for turn_id in recent_turn_ids:
                if turn_id in actions:
                    for action in actions[turn_id]:
                        action_json = json.dumps(
                            asdict(action),
                            default=lambda obj: obj.value
                            if isinstance(obj, Enum)
                            else obj,
                        )
                        lines.append(f"<turn_{turn_id}>{action_json}</turn_{turn_id}>")
            lines.append(f"</{player_id}>")
            return lines

        lines = [
            "<past_actions>",
            *format_player_actions(our_player_id, our_actions),
            *format_player_actions(opponent_player_id, opponent_actions),
            "</past_actions>",
        ]

        return "\n".join(lines)

    def _format_past_raw_events_from_store(
        self,
        store: BattleStreamStore,
        past_turns: int = 1,
    ) -> str:
        """Format past raw server events from BattleStreamStore as XML for inclusion in prompt.

        Args:
            store: BattleStreamStore containing battle events
            past_turns: Number of past turns to include (default: 5)

        Returns:
            XML-formatted string of past raw server events grouped by turn
        """
        raw_events_by_turn = store.get_past_raw_events(past_turns=past_turns)

        if not raw_events_by_turn:
            return "No server events have occurred yet in this battle."

        lines = ["<past_server_events>"]

        for turn_id in sorted(raw_events_by_turn.keys()):
            events = raw_events_by_turn[turn_id]
            lines.append(f"<turn_{turn_id}>")
            for event_str in events:
                lines.append(f"<event>{event_str}</event>")
            lines.append(f"</turn_{turn_id}>")

        lines.append("</past_server_events>")

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

    def _format_opponent_potential_actions(self, state: BattleState) -> str:
        """Format opponent potential actions as JSON string.

        Args:
            state: Current battle state

        Returns:
            JSON formatted string of opponent potential actions
        """
        try:
            actions = state.get_opponent_potential_actions()
            actions_data = [asdict(action) for action in actions]
            return json.dumps(
                actions_data,
                default=lambda obj: obj.value if isinstance(obj, Enum) else obj,
            )
        except ValueError:
            return "[]"

    def _format_turn_context(
        self,
        state: BattleState,
        past_actions_xml: str,
        past_raw_events_xml: str = "",
    ) -> str:
        """Format turn-specific context for the user message using template.

        Args:
            state: Current battle state
            past_actions_xml: Formatted past actions
            past_raw_events_xml: Formatted past raw server events

        Returns:
            Formatted user message with all turn-specific context
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(
            current_dir, "prompts", "zero_shot_agent_turn_prompt.md"
        )

        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()

        available_moves_data = self._format_available_actions(state)
        opponent_actions_data = self._format_opponent_potential_actions(state)

        return (
            template.replace("{{TURN_NUMBER}}", str(state.field_state.turn_number))
            .replace("{{OUR_PLAYER_ID}}", str(state.our_player_id))
            .replace("{{AVAILABLE_ACTIONS}}", available_moves_data)
            .replace("{{BATTLE_STATE}}", str(state))
            .replace("{{OPPONENT_POTENTIAL_ACTIONS}}", opponent_actions_data)
            .replace("{{PAST_ACTIONS}}", past_actions_xml)
            .replace("{{PAST_RAW_EVENTS}}", past_raw_events_xml)
            .replace("{{PAST_SERVER_COUNT}}", str(2))
            .replace("{{PAST_ACTIONS_COUNT}}", str(self._past_actions_count))
        )

    async def choose_action(
        self,
        state: BattleState,
        battle_room: str,
        battle_stream_store: Optional[BattleStreamStore] = None,
    ) -> BattleAction:
        """Choose a battle action using LLM reasoning with retry logic.

        Args:
            state: Current battle state
            battle_room: Battle room identifier
            battle_stream_store: Optional store with all battle events

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
            return get_object_game_data(name, self._game_data)

        if state.our_player_id is None:
            raise ValueError("our_player_id must be set in the battle state")

        if battle_room not in self._battle_room_to_logger:
            logger = LlmEventLogger(
                player_name=state.player_usernames[state.our_player_id],
                model_name=self._model_name,
                battle_room=battle_room,
            )
            self._battle_room_to_logger[battle_room] = logger
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

        opponent_player_id = "p2" if state.our_player_id == "p1" else "p1"

        past_actions_xml = ""
        past_raw_events_xml = ""
        if battle_stream_store:
            past_actions_xml = self._format_past_actions_from_store(
                battle_stream_store,
                state.our_player_id,
                opponent_player_id,
                past_turns=5,
            )
            past_raw_events_xml = self._format_past_raw_events_from_store(
                battle_stream_store, past_turns=2
            )

        llm_agent = LlmAgent(
            model=LiteLlm(model=self._model_name),
            name=self._app_name,
            instruction=self._system_instruction,
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    include_thoughts=True,
                    thinking_budget=1024,
                )
            ),
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
        turn_context = self._format_turn_context(
            state, past_actions_xml, past_raw_events_xml
        )
        content = types.Content(
            parts=[types.Part(text=turn_context)],
            role="bot",
        )
        action_generator = BattleActionGenerator(runner=runner, logger=logger)
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
        battle_stream_store: Optional[BattleStreamStore] = None,
    ) -> Optional[BattleAction]:
        """Handle server error by retrying with choose_action.

        This method is called when the server returns an error. The ZeroShotAgent
        will retry by calling choose_action again with the same state.

        Args:
            error_text: The error message from the server (not used for now)
            state: Current battle state
            battle_room: The battle room identifier
            battle_stream_store: Optional store containing all battle events

        Returns:
            A new BattleAction from choose_action, or None if choose_action fails
        """
        try:
            return await self.choose_action(state, battle_room, battle_stream_store)
        except Exception:
            return None

    async def cleanup_battle(self, battle_room: str) -> None:
        """Clean up resources for a completed battle.

        This should be called when a battle ends to free up memory.

        Args:
            battle_room: The battle room identifier to clean up
        """
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
