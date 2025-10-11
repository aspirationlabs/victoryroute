"""Unit tests for ZeroShotAgent._format_past_actions_from_store()."""

import json
import unittest
from unittest.mock import Mock

from python.agents.zero_shot_agent import ZeroShotAgent
from python.game.environment.battle_stream_store import BattleStreamStore
from python.game.interface.battle_action import ActionType, BattleAction


class ZeroShotAgentTest(unittest.TestCase):
    """Test ZeroShotAgent formatting methods."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.agent = ZeroShotAgent()

    def test_format_past_actions_empty_store(self) -> None:
        """Test formatting with empty battle stream store."""
        mock_store = Mock(spec=BattleStreamStore)
        mock_store.get_past_battle_actions.return_value = {}

        result = self.agent._format_past_actions_from_store(
            mock_store, "p1", "p2", past_turns=5
        )

        self.assertEqual(result, "No actions have been taken yet in this battle.")

    def test_format_past_actions_single_player(self) -> None:
        """Test formatting with actions from only one player."""
        mock_store = Mock(spec=BattleStreamStore)
        p1_actions = {
            1: [BattleAction(action_type=ActionType.MOVE, move_name="thunderbolt")],
            2: [BattleAction(action_type=ActionType.MOVE, move_name="earthquake")],
        }
        p2_actions = {}

        def get_actions_side_effect(player_id: str, past_turns: int):
            return p1_actions if player_id == "p1" else p2_actions

        mock_store.get_past_battle_actions.side_effect = get_actions_side_effect

        result = self.agent._format_past_actions_from_store(
            mock_store, "p1", "p2", past_turns=5
        )

        self.assertIn("<past_actions>", result)
        self.assertIn("<p1>", result)
        self.assertIn("</p1>", result)
        self.assertIn("<p2>", result)
        self.assertIn("</p2>", result)
        self.assertIn("thunderbolt", result)
        self.assertIn("earthquake", result)
        self.assertIn("<turn_1>", result)
        self.assertIn("<turn_2>", result)

        self.assertIn('"action_type": "move"', result)

    def test_format_past_actions_both_players(self) -> None:
        """Test formatting with actions from both players."""
        mock_store = Mock(spec=BattleStreamStore)
        p1_actions = {
            1: [BattleAction(action_type=ActionType.MOVE, move_name="thunderbolt")],
            2: [
                BattleAction(
                    action_type=ActionType.SWITCH, switch_pokemon_name="pikachu"
                )
            ],
        }
        p2_actions = {
            1: [BattleAction(action_type=ActionType.MOVE, move_name="flamethrower")],
            2: [BattleAction(action_type=ActionType.MOVE, move_name="fireblast")],
        }

        def get_actions_side_effect(player_id: str, past_turns: int):
            return p1_actions if player_id == "p1" else p2_actions

        mock_store.get_past_battle_actions.side_effect = get_actions_side_effect

        result = self.agent._format_past_actions_from_store(
            mock_store, "p1", "p2", past_turns=5
        )

        self.assertIn("thunderbolt", result)
        self.assertIn("pikachu", result)
        self.assertIn("flamethrower", result)
        self.assertIn("fireblast", result)

        self.assertIn('"action_type": "move"', result)
        self.assertIn('"action_type": "switch"', result)

    def test_format_past_actions_limits_turns(self) -> None:
        """Test that past_turns parameter limits number of turns shown."""
        mock_store = Mock(spec=BattleStreamStore)
        p1_actions = {
            1: [BattleAction(action_type=ActionType.MOVE, move_name="move1")],
            2: [BattleAction(action_type=ActionType.MOVE, move_name="move2")],
            3: [BattleAction(action_type=ActionType.MOVE, move_name="move3")],
            4: [BattleAction(action_type=ActionType.MOVE, move_name="move4")],
            5: [BattleAction(action_type=ActionType.MOVE, move_name="move5")],
            6: [BattleAction(action_type=ActionType.MOVE, move_name="move6")],
            7: [BattleAction(action_type=ActionType.MOVE, move_name="move7")],
        }
        p2_actions = {}

        def get_actions_side_effect(player_id: str, past_turns: int):
            return p1_actions if player_id == "p1" else p2_actions

        mock_store.get_past_battle_actions.side_effect = get_actions_side_effect

        result = self.agent._format_past_actions_from_store(
            mock_store, "p1", "p2", past_turns=3
        )

        self.assertNotIn("move1", result)
        self.assertNotIn("move2", result)
        self.assertNotIn("move3", result)
        self.assertNotIn("move4", result)
        self.assertIn("move5", result)
        self.assertIn("move6", result)
        self.assertIn("move7", result)

    def test_format_past_actions_multiple_actions_per_turn(self) -> None:
        """Test formatting when multiple actions occur in same turn (e.g., volt switch)."""
        mock_store = Mock(spec=BattleStreamStore)
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

        def get_actions_side_effect(player_id: str, past_turns: int):
            return p1_actions if player_id == "p1" else p2_actions

        mock_store.get_past_battle_actions.side_effect = get_actions_side_effect

        result = self.agent._format_past_actions_from_store(
            mock_store, "p1", "p2", past_turns=5
        )

        self.assertIn("voltswitch", result)
        self.assertIn("raichu", result)
        self.assertIn("earthquake", result)

        turn_1_count = result.count("<turn_1>")
        self.assertEqual(
            turn_1_count, 3, "Should have 3 actions in turn 1 (2 for p1, 1 for p2)"
        )

    def test_format_past_actions_json_structure(self) -> None:
        """Test that action JSON has correct structure using asdict()."""
        mock_store = Mock(spec=BattleStreamStore)
        p1_actions = {
            1: [
                BattleAction(
                    action_type=ActionType.MOVE,
                    move_name="thunderbolt",
                    mega=True,
                    tera=False,
                )
            ],
        }
        p2_actions = {}

        def get_actions_side_effect(player_id: str, past_turns: int):
            return p1_actions if player_id == "p1" else p2_actions

        mock_store.get_past_battle_actions.side_effect = get_actions_side_effect

        result = self.agent._format_past_actions_from_store(
            mock_store, "p1", "p2", past_turns=5
        )

        action_start = result.find("<turn_1>") + len("<turn_1>")
        action_end = result.find("</turn_1>")
        action_json = result[action_start:action_end]

        action_dict = json.loads(action_json)

        self.assertEqual(action_dict["action_type"], "move")
        self.assertEqual(action_dict["move_name"], "thunderbolt")
        self.assertEqual(action_dict["mega"], True)
        self.assertEqual(action_dict["tera"], False)
        self.assertIsNone(action_dict["switch_pokemon_name"])
        self.assertIsNone(action_dict["target_index"])
        self.assertIsNone(action_dict["team_order"])

    def test_format_past_actions_xml_structure(self) -> None:
        """Test that XML structure is correct with proper tags."""
        mock_store = Mock(spec=BattleStreamStore)
        p1_actions = {
            1: [BattleAction(action_type=ActionType.MOVE, move_name="tackle")],
        }
        p2_actions = {
            1: [BattleAction(action_type=ActionType.MOVE, move_name="scratch")],
        }

        def get_actions_side_effect(player_id: str, past_turns: int):
            return p1_actions if player_id == "p1" else p2_actions

        mock_store.get_past_battle_actions.side_effect = get_actions_side_effect

        result = self.agent._format_past_actions_from_store(
            mock_store, "p1", "p2", past_turns=5
        )

        lines = result.split("\n")
        self.assertEqual(lines[0], "<past_actions>")
        self.assertEqual(lines[1], "<p1>")
        self.assertIn("</p1>", lines)
        self.assertIn("<p2>", lines)
        self.assertEqual(lines[-1], "</past_actions>")

        p1_start = lines.index("<p1>")
        p1_end = lines.index("</p1>")
        p2_start = lines.index("<p2>")
        p2_end = lines.index("</p2>")

        self.assertTrue(p1_start < p1_end < p2_start < p2_end)

    def test_format_past_raw_events_empty_store(self) -> None:
        """Test formatting raw events with empty battle stream store."""
        mock_store = Mock(spec=BattleStreamStore)
        mock_store.get_past_raw_events.return_value = {}

        result = self.agent._format_past_raw_events_from_store(mock_store, past_turns=5)

        self.assertEqual(result, "No server events have occurred yet in this battle.")

    def test_format_past_raw_events_single_turn(self) -> None:
        """Test formatting raw events from a single turn."""
        mock_store = Mock(spec=BattleStreamStore)
        raw_events = {
            1: [
                "|turn|1",
                "|move|p1a: Pikachu|Thunderbolt|p2a: Charizard",
                "|-damage|p2a: Charizard|50/100",
            ]
        }
        mock_store.get_past_raw_events.return_value = raw_events

        result = self.agent._format_past_raw_events_from_store(mock_store, past_turns=5)

        self.assertIn("<past_server_events>", result)
        self.assertIn("</past_server_events>", result)
        self.assertIn("<turn_1>", result)
        self.assertIn("</turn_1>", result)
        self.assertIn("<event>|turn|1</event>", result)
        self.assertIn(
            "<event>|move|p1a: Pikachu|Thunderbolt|p2a: Charizard</event>", result
        )
        self.assertIn("<event>|-damage|p2a: Charizard|50/100</event>", result)

    def test_format_past_raw_events_multiple_turns(self) -> None:
        """Test formatting raw events from multiple turns."""
        mock_store = Mock(spec=BattleStreamStore)
        raw_events = {
            1: ["|turn|1", "|move|p1a: Pikachu|Thunderbolt|p2a: Charizard"],
            2: ["|turn|2", "|switch|p1a: Raichu|Raichu, L50|100/100"],
            3: ["|turn|3", "|move|p2a: Charizard|Flamethrower|p1a: Raichu"],
        }
        mock_store.get_past_raw_events.return_value = raw_events

        result = self.agent._format_past_raw_events_from_store(mock_store, past_turns=5)

        self.assertIn("<turn_1>", result)
        self.assertIn("<turn_2>", result)
        self.assertIn("<turn_3>", result)
        self.assertIn("Thunderbolt", result)
        self.assertIn("Raichu", result)
        self.assertIn("Flamethrower", result)

    def test_format_past_raw_events_xml_structure(self) -> None:
        """Test that XML structure is correct with proper event tags."""
        mock_store = Mock(spec=BattleStreamStore)
        raw_events = {
            1: ["|turn|1", "|move|p1a: Pikachu|Tackle|p2a: Bulbasaur"],
        }
        mock_store.get_past_raw_events.return_value = raw_events

        result = self.agent._format_past_raw_events_from_store(mock_store, past_turns=5)

        lines = result.split("\n")
        self.assertEqual(lines[0], "<past_server_events>")
        self.assertEqual(lines[1], "<turn_1>")
        self.assertIn("<event>", lines[2])
        self.assertIn("</event>", lines[2])
        self.assertIn("</turn_1>", lines)
        self.assertEqual(lines[-1], "</past_server_events>")


if __name__ == "__main__":
    unittest.main()
