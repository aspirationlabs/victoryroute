import json
from dataclasses import asdict
from typing import Any, Optional

from absl import logging
from google.adk.agents import BaseAgent, LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.adk.planners import BuiltInPlanner
from google.genai import types

from python.agents.tools.get_object_game_data import get_object_game_data
from python.agents.turn_predictor.turn_predictor_state import (
    OpponentPokemonPrediction,
    TurnPredictorState,
)
from python.agents.turn_predictor.turn_predictor_prompt_builder import (
    TurnPredictorPromptBuilder,
)
from python.agents.tools.pokemon_state_priors_reader import PokemonStatePriorsReader
from python.game.data.game_data import GameData


class TeamPredictorAgent:
    def __init__(
        self,
        priors_reader: PokemonStatePriorsReader,
        prompt_builder: TurnPredictorPromptBuilder,
        game_data: GameData,
        model_name: str = "openrouter/google/gemini-2.5-flash-lite-preview-09-2025",
        max_retries: int = 3,
    ):
        self._game_data: GameData = GameData()

        def tool_get_object_game_data(name: str) -> str:
            """Look up game data for Pokemon, Move, Ability, Item, or Nature.
            Returns detailed stats, types, effects, and descriptions. Use to check:
            Pokemon base stats, move power/effects, ability mechanics, item effects, nature effects.
            Args:
                name: Object name (e.g., "Landorus", "Earthquake", "Intimidate", "Choice Scarf")
            """
            return get_object_game_data(name, self._game_data)

        def tool_get_pokemon_usage_stats(pokemon_species: str) -> str:
            priors = priors_reader.get_pokemon_state_priors(pokemon_species)
            if priors is None:
                return json.dumps({"pokemon_species": pokemon_species, "priors": None})
            return json.dumps(
                {
                    "pokemon_species": pokemon_species,
                    "priors": asdict(priors),
                }
            )

        def log_and_validate_input_state(
            callback_context: CallbackContext,
        ) -> Optional[types.Content]:
            state = _coerce_turn_predictor_state(callback_context.state)
            logging.info(
                f"[TeamPredictorAgent] Turn {state.turn_number}, state: {state}"
            )
            state.validate_input_state()
            return None

        def log_agent_response(
            callback_context: CallbackContext,
        ) -> Optional[types.Content]:
            state = _coerce_turn_predictor_state(callback_context.state)
            logging.info(
                f"[TeamPredictorAgent] Turn {state.turn_number}, opponent predicted active pokemon: {state.opponent_predicted_active_pokemon}"
            )
            return None

        self._model_name: str = model_name
        self._max_retries: int = max_retries
        self._agent = LlmAgent(
            model=LiteLlm(model=model_name),
            name="opponent_pokemon_predictor",
            instruction=prompt_builder.get_team_predictor_system_prompt(),
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    include_thoughts=True,
                    thinking_budget=1024,
                )
            ),
            include_contents="none",
            tools=[tool_get_object_game_data, tool_get_pokemon_usage_stats],
            output_schema=OpponentPokemonPrediction,
            output_key="opponent_predicted_active_pokemon",
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
            before_agent_callback=log_and_validate_input_state,
            after_agent_callback=log_agent_response,
        )

    @property
    def get_adk_agent(self) -> BaseAgent:
        return self._agent


def _coerce_turn_predictor_state(raw_state: Any) -> TurnPredictorState:
    """Convert an ADK callback state into a TurnPredictorState."""
    if isinstance(raw_state, TurnPredictorState):
        return raw_state
    if hasattr(raw_state, "model_dump"):
        return TurnPredictorState.from_state(raw_state)  # type: ignore[arg-type]
    if hasattr(raw_state, "to_dict"):
        return TurnPredictorState.model_validate(raw_state.to_dict())
    if isinstance(raw_state, dict):
        return TurnPredictorState.model_validate(raw_state)
    raise TypeError(
        f"Unsupported state type {type(raw_state)!r}; cannot convert to TurnPredictorState"
    )
