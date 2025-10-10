"""Integration tests for BattleStreamStore using real battle logs."""

import os
import unittest
from typing import Dict, List, Tuple

from absl.testing import absltest, parameterized

from python.game.environment.battle_stream_store import BattleStreamStore
from python.game.events.battle_event import BattleEvent
from python.game.interface.battle_action import ActionType, BattleAction
from python.game.protocol.message_parser import MessageParser


class BattleStreamStoreIntegrationTest(
    unittest.IsolatedAsyncioTestCase, parameterized.TestCase
):
    """Integration tests that validate BattleStreamStore with real battle logs."""

    def _load_battle_log(self, filename: str) -> List[str]:
        """Load battle log from testdata directory.

        Args:
            filename: Name of battle log file (e.g., 'battle1.txt')

        Returns:
            List of raw message lines from the battle log
        """
        testdata_dir = os.path.join(os.path.dirname(__file__), "testdata")
        filepath = os.path.join(testdata_dir, filename)

        with open(filepath, "r") as f:
            lines = f.readlines()

        return [line.strip() for line in lines if line.strip()]

    def _parse_events(self, raw_messages: List[str]) -> List[BattleEvent]:
        """Parse raw battle log messages into BattleEvent objects.

        Args:
            raw_messages: List of raw protocol messages

        Returns:
            List of parsed BattleEvent objects
        """
        parser = MessageParser()
        events = []

        for message in raw_messages:
            event = parser.parse(message)
            events.append(event)

        return events

    @parameterized.named_parameters(
        (
            "battle1",
            "battle1.txt",
            27,
            {
                1: {
                    "p1": [("switch", "ironcrown")],
                    "p2": [("move", "stealthrock")],
                },
                3: {
                    "p1": [("move", "voltswitch"), ("switch", "landorustherian")],
                    "p2": [("move", "shadowball")],
                },
                5: {
                    "p1": [("move", "uturn"), ("switch", "ragingbolt")],
                    "p2": [("move", "hydropump")],
                },
                10: {
                    "p1": [("move", "futuresight")],
                    "p2": [("move", "voltswitch"), ("switch", "gholdengo")],
                },
                12: {
                    "p1": [("move", "ivycudgel")],
                    "p2": [("switch", "kommoo")],
                },
                13: {
                    "p2": [("move", "dragondance")],
                },
            },
        ),
        (
            "live_battle_1",
            "live_battle_1.txt",
            20,
            {
                1: {
                    "p1": [("move", "flipturn"), ("switch", "clefable")],
                    "p2": [("move", "flamethrower")],
                },
                2: {
                    "p1": [("switch", "skarmory")],
                    "p2": [("move", "flamethrower")],
                },
                7: {
                    "p1": [("move", "partingshot"), ("switch", "walkingwake")],
                    "p2": [("move", "swordsdance")],
                },
                16: {
                    "p1": [("move", "closecombat")],
                    "p2": [("move", "headlongrush")],
                },
            },
        ),
    )
    def test_battle_with_expectations(
        self,
        battle_file: str,
        past_turns: int,
        expectations: Dict[int, Dict[str, List[Tuple[str, str]]]],
    ) -> None:
        """Test BattleStreamStore with specific battle files and validate expected actions."""
        raw_messages = self._load_battle_log(battle_file)
        events = self._parse_events(raw_messages)

        store = BattleStreamStore(events)

        past_events = store.get_past_events()
        self.assertIsInstance(past_events, dict)

        p1_actions = store.get_past_battle_actions("p1")
        p2_actions = store.get_past_battle_actions("p2")

        self.assertIsInstance(p1_actions, dict)
        self.assertIsInstance(p2_actions, dict)

        for turn_id, player_expectations in expectations.items():
            for player_id, expected_actions in player_expectations.items():
                actual_actions = (
                    p1_actions[turn_id] if player_id == "p1" else p2_actions[turn_id]
                )

                self.assertEqual(
                    len(actual_actions),
                    len(expected_actions),
                    f"Turn {turn_id} {player_id}: expected {len(expected_actions)} actions, got {len(actual_actions)}",
                )

                for i, (action_type, action_name) in enumerate(expected_actions):
                    actual_action = actual_actions[i]

                    if action_type == "move":
                        self.assertEqual(
                            actual_action.action_type,
                            ActionType.MOVE,
                            f"Turn {turn_id} {player_id} action {i}: expected MOVE",
                        )
                        self.assertEqual(
                            actual_action.move_name,
                            action_name,
                            f"Turn {turn_id} {player_id} action {i}: expected move {action_name}",
                        )
                    elif action_type == "switch":
                        self.assertEqual(
                            actual_action.action_type,
                            ActionType.SWITCH,
                            f"Turn {turn_id} {player_id} action {i}: expected SWITCH",
                        )
                        self.assertEqual(
                            actual_action.switch_pokemon_name,
                            action_name,
                            f"Turn {turn_id} {player_id} action {i}: expected switch to {action_name}",
                        )

    @parameterized.named_parameters(
        ("battle1", "battle1.txt"),
        ("battle2", "battle2.txt"),
        ("battle3", "battle3.txt"),
        ("battle5", "battle5.txt"),
        ("battle9", "battle9.txt"),
        ("battle10", "battle10.txt"),
        ("battle11", "battle11.txt"),
        ("battle12", "battle12.txt"),
        ("battle13", "battle13.txt"),
        ("live_battle_1", "live_battle_1.txt"),
        ("live_battle_2", "live_battle_2.txt"),
        ("live_battle_3", "live_battle_3.txt"),
    )
    def test_all_battles_smoke_test(self, battle_file: str) -> None:
        """Smoke test that BattleStreamStore can process all battle files without errors."""
        raw_messages = self._load_battle_log(battle_file)
        events = self._parse_events(raw_messages)

        store = BattleStreamStore(events)

        past_events = store.get_past_events()
        self.assertIsInstance(past_events, dict)
        max_turn = max(past_events.keys())
        p1_actions = store.get_past_battle_actions("p1", past_turns=max_turn)
        p2_actions = store.get_past_battle_actions("p2", past_turns=max_turn)

        self.assertIsInstance(p1_actions, dict)
        self.assertIsInstance(p2_actions, dict)

        for _, actions in p1_actions.items():
            self.assertIsInstance(actions, list)
            for action in actions:
                self.assertIsInstance(action, BattleAction)
                self.assertIn(
                    action.action_type,
                    [ActionType.MOVE, ActionType.SWITCH, ActionType.TEAM_ORDER],
                )

        for _, actions in p2_actions.items():
            self.assertIsInstance(actions, list)
            for action in actions:
                self.assertIsInstance(action, BattleAction)
                self.assertIn(
                    action.action_type,
                    [ActionType.MOVE, ActionType.SWITCH, ActionType.TEAM_ORDER],
                )


if __name__ == "__main__":
    absltest.main()
