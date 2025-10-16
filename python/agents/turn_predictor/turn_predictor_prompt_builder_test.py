"""Unit tests for TurnPredictorPromptBuilder formatting and state helpers."""

import json
import unittest
from unittest.mock import Mock

from python.agents.turn_predictor.turn_predictor_prompt_builder import (
    TurnPredictorPromptBuilder,
)
from python.agents.turn_predictor.turn_predictor_state import TurnPredictorState
from python.game.environment.battle_stream_store import BattleStreamStore
from python.game.interface.battle_action import ActionType, BattleAction
from python.game.schema.battle_state import BattleState
from python.game.schema.field_state import FieldState
from python.game.schema.pokemon_state import PokemonState
from python.game.schema.team_state import TeamState


class TurnPredictorPromptBuilderTest(unittest.TestCase):
    """Test TurnPredictorPromptBuilder formatting logic."""

    def setUp(self) -> None:
        """Create TurnPredictorPromptBuilder with mocked store."""
        self.mock_store = Mock(spec=BattleStreamStore)
        self.builder = TurnPredictorPromptBuilder(self.mock_store)

    def test_format_past_actions_empty_store(self) -> None:
        """Return empty string when no actions are stored."""
        self.mock_store.get_past_battle_actions.return_value = {}

        result = self.builder._format_past_actions_from_store("p1", "p2", past_turns=5)

        self.assertEqual(result, "")
        self.mock_store.get_past_battle_actions.assert_called()

    def test_format_past_actions_multiple_players(self) -> None:
        """Include actions for both players with proper tags."""
        p1_actions = {
            1: [BattleAction(action_type=ActionType.MOVE, move_name="thunderbolt")],
            2: [
                BattleAction(
                    action_type=ActionType.SWITCH, switch_pokemon_name="rotomwash"
                )
            ],
        }
        p2_actions = {
            1: [BattleAction(action_type=ActionType.MOVE, move_name="earthquake")],
            2: [BattleAction(action_type=ActionType.MOVE, move_name="surf")],
        }

        def get_actions(
            player_id: str, past_turns: int
        ) -> dict[int, list[BattleAction]]:
            return p1_actions if player_id == "p1" else p2_actions

        self.mock_store.get_past_battle_actions.side_effect = get_actions

        result = self.builder._format_past_actions_from_store("p1", "p2", past_turns=5)

        self.assertIn("<past_actions>", result)
        self.assertIn("<p1>", result)
        self.assertIn("<p2>", result)
        self.assertIn("thunderbolt", result)
        self.assertIn("earthquake", result)
        self.assertIn("rotomwash", result)
        self.assertIn("surf", result)

    def test_format_past_actions_turn_window(self) -> None:
        """Limit to the requested number of past turns."""
        p1_actions = {
            1: [BattleAction(action_type=ActionType.MOVE, move_name="move1")],
            2: [BattleAction(action_type=ActionType.MOVE, move_name="move2")],
            3: [BattleAction(action_type=ActionType.MOVE, move_name="move3")],
            4: [BattleAction(action_type=ActionType.MOVE, move_name="move4")],
        }

        self.mock_store.get_past_battle_actions.side_effect = (
            lambda player_id, past_turns: p1_actions
        )

        result = self.builder._format_past_actions_from_store("p1", "p2", past_turns=2)

        self.assertNotIn("move1", result)
        self.assertNotIn("move2", result)
        self.assertIn("move3", result)
        self.assertIn("move4", result)

    def test_format_past_actions_multiple_entries_same_turn(self) -> None:
        """Preserve multiple actions within the same turn."""
        p1_actions = {
            1: [
                BattleAction(action_type=ActionType.MOVE, move_name="voltswitch"),
                BattleAction(
                    action_type=ActionType.SWITCH, switch_pokemon_name="raichu"
                ),
            ],
        }
        p2_actions = {
            1: [BattleAction(action_type=ActionType.MOVE, move_name="earthquake")],
        }

        self.mock_store.get_past_battle_actions.side_effect = (
            lambda player_id, past_turns: p1_actions
            if player_id == "p1"
            else p2_actions
        )

        result = self.builder._format_past_actions_from_store("p1", "p2", past_turns=5)

        self.assertEqual(result.count("<turn_1>"), 3)
        self.assertIn("voltswitch", result)
        self.assertIn("raichu", result)
        self.assertIn("earthquake", result)

    def test_format_past_actions_json_structure(self) -> None:
        """Ensure JSON payload is serialized with expected keys."""
        p1_actions = {
            1: [
                BattleAction(
                    action_type=ActionType.MOVE,
                    move_name="thunderbolt",
                    mega=True,
                    tera=True,
                )
            ],
        }

        self.mock_store.get_past_battle_actions.side_effect = (
            lambda player_id, past_turns: p1_actions
        )

        result = self.builder._format_past_actions_from_store("p1", "p2", past_turns=5)

        start_idx = result.find("<turn_1>") + len("<turn_1>")
        end_idx = result.find("</turn_1>")
        action_payload = result[start_idx:end_idx]
        action_dict = json.loads(action_payload)

        self.assertEqual(action_dict["action_type"], "move")
        self.assertEqual(action_dict["move_name"], "thunderbolt")
        self.assertTrue(action_dict["mega"])
        self.assertTrue(action_dict["tera"])

    def test_format_past_raw_events_empty(self) -> None:
        """Return empty string when no raw events exist."""
        self.mock_store.get_past_raw_events.return_value = {}

        result = self.builder._format_past_raw_events(past_turns=3)

        self.assertEqual(result, "")
        self.mock_store.get_past_raw_events.assert_called_once_with(past_turns=3)

    def test_format_past_raw_events_multiple_turns(self) -> None:
        """Wrap raw events in XML tags per turn in chronological order."""
        self.mock_store.get_past_raw_events.return_value = {
            2: ["|-start|p1a: Clefable|move: Calm Mind"],
            1: ["|-weather|Sandstorm|[from] ability: Sand Stream"],
        }

        result = self.builder._format_past_raw_events(past_turns=4)

        self.assertTrue(result.startswith("<past_server_events>"))
        self.assertIn("<turn_1>", result)
        self.assertIn("<turn_2>", result)
        self.assertIn("Calm Mind", result)
        self.assertIn("Sandstorm", result)
        self.mock_store.get_past_raw_events.assert_called_once_with(past_turns=4)

    def test_get_system_prompts_read_from_disk(self) -> None:
        """System prompts should include expected headings from prompt files."""
        instructions = self.builder.get_system_instructions()
        team_prompt = self.builder.get_team_predictor_system_prompt()

        self.assertIn("Opponent Team Predictor", instructions)
        self.assertIn("Opponent Team Predictor", team_prompt)
        self.assertGreater(len(instructions), len(team_prompt))

    def test_get_new_turn_state_prompt(self) -> None:
        """Construct TurnPredictorState with opponent info and formatted history."""
        opponent_pokemon = PokemonState(species="Garchomp", is_active=True)
        our_pokemon = PokemonState(species="Rotom-Wash", is_active=True)

        battle_state = BattleState(
            teams={
                "p1": TeamState(
                    pokemon=[our_pokemon],
                    active_pokemon_index=0,
                    player_id="p1",
                ),
                "p2": TeamState(
                    pokemon=[opponent_pokemon],
                    active_pokemon_index=0,
                    player_id="p2",
                ),
            },
            field_state=FieldState(turn_number=7),
            player_usernames={"p1": "Player One", "p2": "Player Two"},
            our_player_id="p1",
        )

        self.mock_store.get_past_raw_events.return_value = {
            6: ["|-damage|p2a: Garchomp|184/358"],
        }
        self.mock_store.get_past_battle_actions.side_effect = (
            lambda player_id, past_turns: {
                6: [BattleAction(action_type=ActionType.MOVE, move_name="earthquake")]
            }
        )

        state = self.builder.get_new_turn_state_prompt(battle_state, past_turns=2)

        self.assertIsInstance(state, TurnPredictorState)
        self.assertEqual(state.our_player_id, "p1")
        self.assertEqual(state.turn_number, 7)
        self.assertEqual(state.opponent_active_pokemon.species, "Garchomp")
        self.assertIn("earthquake", state.past_player_actions)
        self.assertIn("past_server_events", state.past_battle_event_logs)
        self.assertIs(state.battle_state, battle_state)


if __name__ == "__main__":
    unittest.main()
