"""
A zero-shot agent that uses a foundation model to make decisions.
The prompt includes no examples of past battles, team/move priors, common combinations, etc.
"""

import json
import os
import re
import time
from typing import Any, Dict, List, Optional

import litellm
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from python.agents.agent_interface import Agent
from python.agents.tools.get_available_moves import get_available_moves
from python.agents.tools.get_object_game_data import get_object_game_data
from python.agents.tools.llm_event_logger import LlmEventLogger
from python.game.data.game_data import GameData
from python.game.interface.battle_action import ActionType, BattleAction
from python.game.schema.battle_state import BattleState

# Configure LiteLLM global retry settings for rate limit handling
# LiteLLM automatically uses exponential backoff for rate limits
litellm.num_retries = 10


def _extract_json_from_response(response: str) -> str:
    """Extract JSON from LLM response, handling various formats.

    Handles:
    - Pure JSON responses
    - JSON within markdown code blocks (```json ... ```)
    - JSON after analysis/reasoning text
    - Multiple code blocks (takes the last one)

    Args:
        response: Raw LLM response text

    Returns:
        Extracted JSON string

    Raises:
        ValueError: If no valid JSON object (dict) can be extracted
    """
    response = response.strip()

    # Try to find JSON within markdown code blocks (```json ... ``` or ``` ... ```)
    code_block_pattern = r"```(?:json)?\s*\n(.*?)\n```"
    matches = list(re.finditer(code_block_pattern, response, re.DOTALL))
    if matches:
        json_str = matches[-1].group(1).strip()
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict):
                return json_str
        except json.JSONDecodeError:
            pass

    # Try to find raw JSON object {...} in the response
    json_object_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
    matches = list(re.finditer(json_object_pattern, response, re.DOTALL))
    if matches:
        json_str = matches[-1].group(0).strip()
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict):
                return json_str
        except json.JSONDecodeError:
            pass

    # If nothing found, return original (will fail downstream with better error)
    return response


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
        model_name: str = "openrouter/google/gemini-2.5-flash-lite-preview-09-2025",
        mode: str = "gen9ou",
        max_retries: int = 3,
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
        self._battle_room_to_actions: Dict[str, List[BattleAction]] = {}

        self._static_instruction: str = _load_static_system_instruction(mode=mode)

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
        available_moves_data = get_available_moves(state)

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

    def _validate_action(self, action_data: Any, state: BattleState) -> Optional[str]:
        """Validate that the action is legal given the current battle state.

        Args:
            action_data: Parsed action data from LLM (should be a dict)
            state: Current battle state

        Returns:
            Error message if invalid, None if valid
        """
        if state.our_player_id is None:
            return "Invalid state: our_player_id is not set"

        if not isinstance(action_data, dict):
            return (
                f"Invalid action: expected JSON object (dict), but got {type(action_data).__name__}. "
                f"Value: {action_data}. You must return a JSON object like "
                '{"action_type": "move", "move_name": "earthquake"}'
            )

        action_type = action_data.get("action_type", "").lower()

        if action_type == "team_order":
            if not state.team_preview:
                return (
                    "Invalid action: chose 'team_order' but team_preview is false. "
                    "Available action types: 'move' or 'switch'"
                )
            team_order = action_data.get("team_order")
            if not team_order or not isinstance(team_order, str):
                return "Invalid action: 'team_order' requires a string like '123456'"
            if len(team_order) != 6 or not team_order.isdigit():
                return "Invalid action: 'team_order' must be 6 digits (1-6)"

        elif action_type == "move":
            if state.team_preview:
                return (
                    "Invalid action: chose 'move' but team_preview is true. "
                    "You must choose 'team_order' instead"
                )
            if state.force_switch:
                return (
                    "Invalid action: chose 'move' but force_switch is true. "
                    "You must choose 'switch' instead"
                )
            move_name = action_data.get("move_name")
            if not move_name or not isinstance(move_name, str):
                return "Invalid action: 'move' requires string 'move_name'"

            if move_name not in state.available_moves:
                return (
                    f"Invalid action: move '{move_name}' is not in available moves list {state.available_moves}. "
                    f"This move may be disabled, out of PP, or locked by choice item. "
                    f"Choose a different move_name that is in the available moves list."
                )

            mega = action_data.get("mega", False)
            if mega and not state.can_mega:
                return (
                    "Invalid action: 'mega' is true but can_mega is false. "
                    "You cannot Mega Evolve this turn."
                )

            tera = action_data.get("tera", False)
            if tera and not state.can_tera:
                return (
                    "Invalid action: 'tera' is true but can_tera is false. "
                    "You cannot Terastallize this turn."
                )

        elif action_type == "switch":
            if state.team_preview:
                return (
                    "Invalid action: chose 'switch' but team_preview is true. "
                    "You must choose 'team_order' instead"
                )
            switch_pokemon_name = action_data.get("switch_pokemon_name")
            if not switch_pokemon_name or not isinstance(switch_pokemon_name, str):
                return "Invalid action: 'switch' requires string 'switch_pokemon_name'"

            # Verify that the Pokemon exists in the team and is available to switch
            team = state.get_team(state.our_player_id)
            pokemon_index = None
            for i, pokemon in enumerate(team.pokemon):
                if pokemon.species.lower() == switch_pokemon_name.lower():
                    pokemon_index = i
                    break

            if pokemon_index is None:
                return (
                    f"Invalid action: Pokemon '{switch_pokemon_name}' not found in team. "
                    f"Available Pokemon: {[p.species for p in team.pokemon]}"
                )

            if pokemon_index not in state.available_switches:
                return (
                    f"Invalid action: Pokemon '{switch_pokemon_name}' (index {pokemon_index}) "
                    f"is not in available switches {state.available_switches}. "
                    f"Available switches: {[team.pokemon[i].species for i in state.available_switches]}"
                )

        else:
            return (
                f"Invalid action: unknown action_type '{action_type}'. "
                "Must be 'move', 'switch', or 'team_order'"
            )

        return None

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
        if state.our_player_id is None:
            raise ValueError("our_player_id must be set in the battle state")

        if battle_room not in self._battle_room_to_logger:
            self._battle_room_to_logger[battle_room] = LlmEventLogger(
                player_name=state.player_usernames[state.our_player_id],
                model_name=self._model_name,
                battle_room=battle_room,
            )
        logger = self._battle_room_to_logger[battle_room]

        if battle_room not in self._battle_room_to_actions:
            self._battle_room_to_actions[battle_room] = []

        past_actions = self._battle_room_to_actions[battle_room]
        past_actions_xml = self._format_past_actions(past_actions, state.our_player_id)

        turn_number = state.field_state.turn_number if state.field_state else 0

        def tool_get_object_game_data(name: str) -> str:
            """Look up detailed game data for a Pokemon, Move, Ability, Item, or Nature.

            WHEN TO USE:
            Call this tool whenever you need detailed information about specific game objects
            to make informed strategic decisions. Maximum 2 calls per turn.

            WHAT IT DOES:
            Queries the game database and returns comprehensive information about any game
            object by name. The tool automatically determines the object type (Pokemon, Move,
            Ability, Item, or Nature) and returns all relevant data fields.

            USE THIS TO LOOK UP:
            - Pokemon base stats, types, and capabilities
            - Opponent's revealed Pokemon information
            - Move details (power, accuracy, type, category, PP, effects)
            - Ability effects and descriptions
            - Item effects and descriptions
            - Nature stat modifications

            This is essential for understanding type matchups, calculating damage potential,
            and planning strategic decisions.

            Args:
                name: Name of the object to look up (e.g., "Landorus", "Earthquake",
                      "Intimidate", "Choice Scarf", "Adamant")
            """
            return get_object_game_data(name, game_data)

        llm_agent = LlmAgent(
            model=LiteLlm(model=self._model_name),
            name=self._app_name,
            instruction=self._static_instruction,
            tools=[tool_get_object_game_data],
        )

        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name=self._app_name,
            user_id=battle_room,
        )

        runner = Runner(
            agent=llm_agent,
            app_name=self._app_name,
            session_service=session_service,
        )

        start_time: float = time.time()
        total_prompt_tokens: int = 0
        total_completion_tokens: int = 0
        total_tokens: int = 0

        action: Optional[BattleAction] = None
        last_error: Optional[str] = None

        for retry_attempt in range(self._max_retries + 1):
            if retry_attempt == 0:
                turn_context = self._format_turn_context(
                    state, turn_number, past_actions_xml
                )
            else:
                # On retry, only send error + available actions (not full state)
                available_moves_data = get_available_moves(state)
                turn_context = (
                    f"=== RETRY {retry_attempt}/{self._max_retries} ===\n\n"
                    f"Previous action INVALID:\n{last_error}\n\n"
                    f"Available Actions:\n{available_moves_data}\n\n"
                    f"Provide a valid action from the list above."
                )

            content = types.Content(
                parts=[types.Part(text=turn_context)],
                role="user",
            )

            final_response: Optional[str] = None
            event_count: int = 0
            last_event_time: float = time.time()

            events = runner.run(
                user_id=battle_room,
                session_id=session.id,
                new_message=content,
            )

            try:
                for event in events:
                    event_count += 1
                    event_start_time: float = time.time()
                    event_latency: float = event_start_time - last_event_time

                    event_info: Dict[str, Any] = {
                        "event_number": event_count,
                        "retry_attempt": retry_attempt,
                        "id": event.id,
                        "content": str(event.content),
                        "actions": str(event.actions),
                        "invocation_id": event.invocation_id,
                        "author": event.author,
                        "latency_seconds": round(event_latency, 3),
                        "error_code": event.error_code,
                        "error_message": event.error_message,
                        "custom_metadata": event.custom_metadata,
                        "usage_metadata": (
                            str(event.usage_metadata) if event.usage_metadata else None
                        ),
                    }

                    if event.usage_metadata:
                        usage = event.usage_metadata
                        prompt_tokens: int = usage.prompt_token_count or 0
                        completion_tokens: int = usage.candidates_token_count or 0
                        event_total_tokens: int = usage.total_token_count or 0

                        total_prompt_tokens += prompt_tokens
                        total_completion_tokens += completion_tokens
                        total_tokens += event_total_tokens

                        event_info["prompt_tokens"] = prompt_tokens
                        event_info["completion_tokens"] = completion_tokens
                        event_info["total_tokens"] = event_total_tokens

                    logger.log_event(event_info)

                    if (
                        event.is_final_response()
                        and event.content
                        and event.content.parts
                    ):
                        final_response = event.content.parts[0].text

                    last_event_time = event_start_time

            except json.JSONDecodeError as e:
                last_error = (
                    f"Tool call JSON parsing error: {e}. "
                    "The LLM generated a tool call with malformed JSON arguments. "
                    "Please provide your action as JSON text WITHOUT using any tools."
                )
                continue

            if not final_response:
                last_error = "No final response received from LLM"
                continue

            # Extract JSON from response
            json_str: str = ""
            try:
                json_str = _extract_json_from_response(final_response)
                action_data = json.loads(json_str)
            except json.JSONDecodeError as e:
                last_error = (
                    f"Failed to parse LLM response as JSON: {e}\n"
                    f"Extracted: {json_str}\n"
                    f"Full response: {final_response}"
                )
                continue

            validation_error = self._validate_action(action_data, state)
            if validation_error:
                last_error = validation_error
                continue

            # Extract reasoning from JSON (optional field)
            reasoning = action_data.get("reasoning", "No reasoning provided")
            reasoning_info = {
                "action_decision": "reasoning",
                "turn": turn_number,
                "action_type": action_data.get("action_type"),
                "reasoning": reasoning,
                "full_action": action_data,
            }
            logger.log_event(reasoning_info)

            action_type_str = action_data.get("action_type", "").lower()

            if action_type_str == "move":
                action = BattleAction(
                    action_type=ActionType.MOVE,
                    move_name=action_data.get("move_name"),
                    mega=action_data.get("mega", False),
                    tera=action_data.get("tera", False),
                )
            elif action_type_str == "switch":
                action = BattleAction(
                    action_type=ActionType.SWITCH,
                    switch_pokemon_name=action_data.get("switch_pokemon_name"),
                )
            elif action_type_str == "team_order":
                action = BattleAction(
                    action_type=ActionType.TEAM_ORDER,
                    team_order=action_data.get("team_order"),
                )

            break

        total_latency: float = time.time() - start_time

        summary_info = {
            "summary": "turn_complete",
            "turn": turn_number,
            "total_latency_seconds": round(total_latency, 3),
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "retry_attempts": retry_attempt,
            "success": action is not None,
        }
        logger.log_event(summary_info)

        await session_service.delete_session(
            app_name=self._app_name,
            user_id=battle_room,
            session_id=session.id,
        )

        if action is None:
            raise ValueError(
                f"Failed to get valid action after {self._max_retries + 1} attempts. "
                f"Last error: {last_error}"
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
            del self._battle_room_to_logger[battle_room]

        if battle_room in self._battle_room_to_actions:
            del self._battle_room_to_actions[battle_room]
