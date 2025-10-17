from __future__ import annotations

import json
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from python.agents.turn_predictor.simulation_result import SimulationResult
from python.game.schema.pokemon_state import PokemonState
from python.game.schema.battle_state import BattleState
from python.game.interface.battle_action import BattleAction
from python.game.schema.battle_state import BattleState
from python.game.schema.pokemon_state import PokemonState


class MovePrediction(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str = Field(description="Move name.")
    confidence: float = Field(description="Confidence, between 0 and 1.")


class OpponentPokemonPrediction(BaseModel):
    model_config = ConfigDict(frozen=True)
    species: str = Field(description="Pokemon species.")
    moves: List[MovePrediction] = Field(description="Active pokemon moves (up to 4).")
    item: str = Field(description="Item name.")
    ability: str = Field(description="Ability name.")
    tera_type: str = Field(description="Tera type name.")


class TurnPredictorState(BaseModel):
    """
    Class to manage session state for the turn predictor agent.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    our_player_id: str
    turn_number: int
    opponent_active_pokemon: PokemonState
    past_battle_event_logs: str
    past_player_actions: str
    battle_state: BattleState
    available_actions: List[BattleAction]
    opponent_predicted_active_pokemon: Optional[OpponentPokemonPrediction] = None
    simulation_actions: Optional[List[SimulationResult]] = None

    @classmethod
    def from_session(cls, session: Any) -> "TurnPredictorState":
        """Create from any object by extracting matching fields."""
        if not hasattr(session, "state"):
            raise AttributeError("Session object must have a 'state' attribute")
        state = session.state
        if isinstance(state, BaseModel):
            return cls.from_state(state)
        return cls.model_validate(state)

    @classmethod
    def from_state(cls, state: BaseModel) -> "TurnPredictorState":
        if isinstance(state, cls):
            return state

        state_data = state.model_dump()
        return cls(
            our_player_id=state_data["our_player_id"],
            turn_number=state_data["turn_number"],
            opponent_active_pokemon=state_data["opponent_active_pokemon"],
            past_battle_event_logs=state_data["past_battle_event_logs"],
            past_player_actions=state_data["past_player_actions"],
            battle_state=state_data["battle_state"],
            available_actions=state_data["available_actions"],
            opponent_predicted_active_pokemon=state_data.get(
                "opponent_predicted_active_pokemon", None
            ),
        )

    def validate_input_state(self) -> None:
        if not self.our_player_id:
            raise ValueError("our_player_id is required")
        if not self.turn_number:
            raise ValueError("turn_number is required")
        if not self.opponent_active_pokemon:
            raise ValueError("opponent_active_pokemon is required")
        if self.past_battle_event_logs is None:
            raise ValueError("past_battle_event_logs is required")
        if self.past_player_actions is None:
            raise ValueError("past_player_actions is required")
        if not self.battle_state:
            raise ValueError("battle_state is required")
        if not self.available_actions:
            raise ValueError("available_actions is required")

    def update_session_state(self, session: Any) -> None:
        session.state.update(self.model_dump(mode="json"))

    def __str__(self) -> str:
        return json.dumps(self.model_dump(mode="json"))

    def __repr__(self) -> str:
        return self.__str__()
