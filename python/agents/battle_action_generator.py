"""
BattleActionGenerator encapsulates the logic for generating, validating, and retrying
battle actions from LLM responses. This can be reused across different ADK agents.
"""

import json
import logging
import time
from typing import Any, Dict, Optional

from google.adk.runners import Runner
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

from python.agents.tools.llm_event_logger import LlmEventLogger
from python.game.interface.battle_action import ActionType, BattleAction
from python.game.schema.battle_state import BattleState


class BattleActionResponse(BaseModel):
    """Structured response format for battle action decisions."""

    action_type: str = Field(
        description="Type of action: 'move', 'switch', or 'team_order'"
    )
    move_name: Optional[str] = Field(
        default=None,
        description="Name of the move to use (required for 'move' actions)",
    )
    switch_pokemon_name: Optional[str] = Field(
        default=None,
        description="Name of Pokemon to switch to (required for 'switch' actions)",
    )
    team_order: Optional[str] = Field(
        default=None,
        description="Team order as 6 digits, e.g. '123456' (required for 'team_order' actions)",
    )
    mega: bool = Field(
        default=False, description="Whether to Mega Evolve (only with 'move' actions)"
    )
    tera: bool = Field(
        default=False,
        description="Whether to Terastallize (only with 'move' actions)",
    )
    reasoning: str = Field(description="Explanation of why this action was chosen")


class BattleActionGenerator:
    """Generates battle actions from LLM responses with validation and retry logic."""

    def __init__(self, runner: Runner, logger: LlmEventLogger):
        """Initialize the BattleActionGenerator.

        Args:
            runner: ADK Runner instance for executing LLM queries
            logger: Logger for tracking events and token usage
        """
        self._runner = runner
        self._logger = logger

    def _validate_action(
        self, action_response: BattleActionResponse, state: BattleState
    ) -> Optional[str]:
        """Validate that the action is legal given the current battle state.

        Args:
            action_response: Parsed Pydantic action response from LLM
            state: Current battle state

        Returns:
            Error message if invalid, None if valid
        """
        if state.our_player_id is None:
            return "Invalid state: our_player_id is not set"

        action_type = action_response.action_type.lower()

        if action_type == "team_order":
            if not state.team_preview:
                return (
                    "Invalid action: chose 'team_order' but team_preview is false. "
                    "Available action types: 'move' or 'switch'"
                )
            team_order = action_response.team_order
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
            move_name = action_response.move_name
            if not move_name or not isinstance(move_name, str):
                return "Invalid action: 'move' requires string 'move_name'"

            if move_name not in state.available_moves:
                return (
                    f"Invalid action: move '{move_name}' is not in available moves list {state.available_moves}. "
                    f"This move may be disabled, out of PP, or locked by choice item. "
                    f"Choose a different move_name that is in the available moves list."
                )

            mega = action_response.mega
            if mega and not state.can_mega:
                return (
                    "Invalid action: 'mega' is true but can_mega is false. "
                    "You cannot Mega Evolve this turn."
                )

            tera = action_response.tera
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
            switch_pokemon_name = action_response.switch_pokemon_name
            if not switch_pokemon_name or not isinstance(switch_pokemon_name, str):
                return "Invalid action: 'switch' requires string 'switch_pokemon_name'"

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

    def _construct_battle_action(
        self, action_response: BattleActionResponse
    ) -> BattleAction:
        """Construct a BattleAction from validated action response.

        Args:
            action_response: Validated Pydantic action response

        Returns:
            BattleAction object
        """
        action_type_str = action_response.action_type.lower()

        if action_type_str == "move":
            return BattleAction(
                action_type=ActionType.MOVE,
                move_name=action_response.move_name,
                mega=action_response.mega,
                tera=action_response.tera,
            )
        elif action_type_str == "switch":
            return BattleAction(
                action_type=ActionType.SWITCH,
                switch_pokemon_name=action_response.switch_pokemon_name,
            )
        elif action_type_str == "team_order":
            return BattleAction(
                action_type=ActionType.TEAM_ORDER,
                team_order=action_response.team_order,
            )
        else:
            raise ValueError(f"Unknown action_type: {action_type_str}")

    def _extract_json(self, response_text: str) -> Dict[str, Any]:
        """Extract and parse JSON from response text.

        Handles both clean JSON responses and responses with extra text before/after JSON.

        Args:
            response_text: Raw response text from LLM

        Returns:
            Parsed JSON as dictionary

        Raises:
            json.JSONDecodeError: If no valid JSON found
        """
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            start_idx = response_text.find("{")
            if start_idx == -1:
                raise json.JSONDecodeError(
                    "No JSON object found in response", response_text, 0
                )

            brace_count = 0
            end_idx = -1
            for i in range(start_idx, len(response_text)):
                if response_text[i] == "{":
                    brace_count += 1
                elif response_text[i] == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break

            if end_idx == -1:
                raise json.JSONDecodeError(
                    "No matching closing brace found", response_text, start_idx
                )

            json_str = response_text[start_idx:end_idx]
            return json.loads(json_str)

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
        return json.dumps(available_actions, indent=2)

    async def generate_action(
        self,
        user_query: types.Content,
        state: BattleState,
        user_id: str,
        session_id: str,
        max_retries: int = 3,
    ) -> BattleAction:
        """Generate a battle action from LLM with validation and retry logic.

        Args:
            user_query: Initial user query content to send to LLM
            state: Current battle state for validation
            user_id: User ID for the session
            session_id: Session ID for the runner
            max_retries: Maximum number of retry attempts

        Returns:
            Validated BattleAction

        Raises:
            ValueError: If unable to generate valid action after max retries
        """
        start_time: float = time.time()
        total_prompt_tokens: int = 0
        total_completion_tokens: int = 0
        total_tokens: int = 0

        action: Optional[BattleAction] = None
        last_error: Optional[str] = None
        turn_number = state.field_state.turn_number if state.field_state else 0

        for retry_attempt in range(max_retries + 1):
            if retry_attempt == 0:
                content = user_query
            else:
                # On retry, provide error feedback
                available_moves_data = self._format_available_actions(state)
                retry_text = (
                    f"RETRY {retry_attempt}/{max_retries} - Previous action INVALID:\n"
                    f"{last_error}\n\n"
                    f"Available actions:\n{available_moves_data}\n\n"
                    f"Choose a valid action. Keep reasoning to 1-2 sentences."
                )
                content = types.Content(
                    parts=[types.Part(text=retry_text)],
                    role="user",
                )

            query_text = content.parts[0].text if content.parts else ""
            if query_text:
                self._logger.log_user_query(turn_number, query_text, retry_attempt)

            action_response: Optional[BattleActionResponse] = None
            event_count: int = 0
            last_event_time: float = time.time()

            events = self._runner.run(
                user_id=user_id,
                session_id=session_id,
                new_message=content,
            )

            for event in events:
                event_count += 1
                event_start_time: float = time.time()
                event_latency: float = event_start_time - last_event_time

                # Serialize event with proper structure
                serialized_event = self._logger._serialize_event(event)
                event_info: Dict[str, Any] = {
                    "event_number": event_count,
                    "retry_attempt": retry_attempt,
                    "latency_seconds": round(event_latency, 3),
                    **serialized_event,
                }
                self._logger.log_event(turn_number, event_info)

                if event.usage_metadata:
                    total_prompt_tokens += event.usage_metadata.prompt_token_count or 0
                    total_completion_tokens += (
                        event.usage_metadata.candidates_token_count or 0
                    )
                    total_tokens += event.usage_metadata.total_token_count or 0

                if event.is_final_response() and event.content and event.content.parts:
                    response_text = event.content.parts[0].text
                    if response_text:
                        try:
                            response_data = self._extract_json(response_text)
                            action_response = BattleActionResponse(**response_data)
                        except (json.JSONDecodeError, ValidationError) as e:
                            last_error = (
                                f"Failed to parse response as BattleActionResponse: {e}\n"
                                f"Response: {response_text}"
                            )

                last_event_time = event_start_time

            if not action_response:
                if not last_error:
                    last_error = "No valid BattleActionResponse received from LLM"
                continue

            validation_error = self._validate_action(action_response, state)
            if validation_error:
                last_error = validation_error
                continue
            action = self._construct_battle_action(action_response)
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
        self._logger.log_turn_summary(turn_number, summary_info)
        logging.info(
            f"Turn {turn_number}: total_tokens: {total_tokens}, "
            f"total_latency_seconds: {total_latency}, retry_attempts: {retry_attempt}"
        )

        if action is None:
            raise ValueError(
                f"Failed to get valid action after {max_retries + 1} attempts. "
                f"Last error: {last_error}"
            )

        return action
