"""Unit tests for TurnPredictorState and related models."""

import json
import unittest
from types import SimpleNamespace

from python.agents.turn_predictor.turn_predictor_state import (
    MovePrediction,
    OpponentPokemonPrediction,
    TurnPredictorState,
)
from python.game.schema.battle_state import BattleState
from python.game.schema.field_state import FieldState
from python.game.schema.pokemon_state import PokemonState
from python.game.schema.team_state import TeamState


class TurnPredictorStateTest(unittest.TestCase):
    """Validate serialization helpers for turn predictor state."""

    def setUp(self) -> None:
        """Create reusable battle state fixtures."""
        self.our_pokemon = PokemonState(species="Rotom-Wash", is_active=True)
        self.opponent_pokemon = PokemonState(species="Garchomp", is_active=True)

        self.battle_state = BattleState(
            teams={
                "p1": TeamState(
                    pokemon=[self.our_pokemon],
                    active_pokemon_index=0,
                    player_id="p1",
                ),
                "p2": TeamState(
                    pokemon=[self.opponent_pokemon],
                    active_pokemon_index=0,
                    player_id="p2",
                ),
            },
            field_state=FieldState(turn_number=5),
            player_usernames={"p1": "Player One", "p2": "Player Two"},
            our_player_id="p1",
        )

        self.prediction = OpponentPokemonPrediction(
            species="Garchomp",
            moves=[
                MovePrediction(name="earthquake", confidence=0.9),
                MovePrediction(name="swordsdance", confidence=0.6),
            ],
            item="choice scarf",
            ability="rough skin",
            tera_type="ground",
        )

        self.base_kwargs = {
            "our_player_id": "p1",
            "turn_number": 5,
            "opponent_active_pokemon": self.opponent_pokemon,
            "past_battle_event_logs": "<past_server_events></past_server_events>",
            "past_player_actions": "<past_actions></past_actions>",
            "battle_state": self.battle_state,
            "opponent_predicted_active_pokemon": self.prediction,
        }

        self.state = TurnPredictorState(**self.base_kwargs)

    def test_validate_input_state_success(self) -> None:
        """State with required fields passes validation."""
        self.state.validate_input_state()

    def test_validate_input_state_missing_field(self) -> None:
        """Validation fails when mandatory fields are None."""
        invalid_state = self.state.model_copy(update={"past_player_actions": None})
        with self.assertRaises(ValueError):
            invalid_state.validate_input_state()

    def test_validate_input_state_empty_strings_allowed(self) -> None:
        """Empty strings for history fields are allowed (for first turn)."""
        valid_state = self.state.model_copy(
            update={"past_player_actions": "", "past_battle_event_logs": ""}
        )
        # Should not raise any exception
        valid_state.validate_input_state()

    def test_from_state_round_trip(self) -> None:
        """from_state reconstructs an equivalent model."""
        input_state = dict(self.base_kwargs)
        result = TurnPredictorState.from_state(input_state)
        self.assertEqual(result, self.state)

    def test_from_session_round_trip(self) -> None:
        """from_session uses session.state dict to rebuild model."""
        session = SimpleNamespace(state=dict(self.base_kwargs))
        result = TurnPredictorState.from_session(session)
        self.assertEqual(result, self.state)

    def test_update_session_state_serializes_fields(self) -> None:
        """update_session_state writes JSON-ready payload into session.state."""
        session = SimpleNamespace(state={})
        self.state.update_session_state(session)

        expected = self.state.model_dump(mode="json")
        self.assertEqual(session.state, expected)
        # Spot-check nested serialization
        self.assertIn("opponent_active_pokemon", session.state)
        self.assertIsInstance(session.state["opponent_active_pokemon"], dict)

    def test_string_representation_is_json(self) -> None:
        """__str__ returns JSON containing key fields."""
        payload = json.loads(str(self.state))
        self.assertEqual(payload["our_player_id"], "p1")
        self.assertEqual(payload["turn_number"], 5)

    def test_from_state_missing_optional_field(self) -> None:
        """from_state handles missing opponent_predicted_active_pokemon."""
        input_state = dict(self.base_kwargs)
        del input_state["opponent_predicted_active_pokemon"]
        result = TurnPredictorState.from_state(input_state)
        self.assertIsNone(result.opponent_predicted_active_pokemon)

    def test_from_session_missing_optional_field(self) -> None:
        """from_session handles missing opponent_predicted_active_pokemon."""
        state_dict = dict(self.base_kwargs)
        del state_dict["opponent_predicted_active_pokemon"]
        session = SimpleNamespace(state=state_dict)
        result = TurnPredictorState.from_session(session)
        self.assertIsNone(result.opponent_predicted_active_pokemon)


if __name__ == "__main__":
    unittest.main()
