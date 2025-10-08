"""Unit tests for BattleAction."""

import unittest

from absl.testing import parameterized

from python.game.interface.battle_action import ActionType, BattleAction


class BattleActionTest(parameterized.TestCase):
    """Test BattleAction functionality."""

    @parameterized.parameters(
        (0, "/choose move 1"),
        (1, "/choose move 2"),
        (2, "/choose move 3"),
        (3, "/choose move 4"),
    )
    def test_basic_move_action(self, move_index: int, expected_command: str) -> None:
        """Test basic move actions convert to correct commands."""
        action = BattleAction(action_type=ActionType.MOVE, move_index=move_index)
        self.assertEqual(action.to_showdown_command(), expected_command)

    @parameterized.parameters(
        (0, "/choose switch 1"),
        (1, "/choose switch 2"),
        (2, "/choose switch 3"),
        (3, "/choose switch 4"),
        (4, "/choose switch 5"),
        (5, "/choose switch 6"),
    )
    def test_basic_switch_action(
        self, switch_index: int, expected_command: str
    ) -> None:
        """Test basic switch actions convert to correct commands."""
        action = BattleAction(action_type=ActionType.SWITCH, switch_index=switch_index)
        self.assertEqual(action.to_showdown_command(), expected_command)

    @parameterized.parameters(
        (0, "/choose move 1 mega"),
        (1, "/choose move 2 mega"),
        (2, "/choose move 3 mega"),
        (3, "/choose move 4 mega"),
    )
    def test_mega_evolution_move(self, move_index: int, expected_command: str) -> None:
        """Test move with Mega Evolution."""
        action = BattleAction(
            action_type=ActionType.MOVE, move_index=move_index, mega=True
        )
        self.assertEqual(action.to_showdown_command(), expected_command)

    @parameterized.parameters(
        (0, "/choose move 1 tera"),
        (1, "/choose move 2 tera"),
        (2, "/choose move 3 tera"),
        (3, "/choose move 4 tera"),
    )
    def test_terastallization_move(
        self, move_index: int, expected_command: str
    ) -> None:
        """Test move with Terastallization."""
        action = BattleAction(
            action_type=ActionType.MOVE, move_index=move_index, tera=True
        )
        self.assertEqual(action.to_showdown_command(), expected_command)

    @parameterized.parameters(
        # Opponent targeting (target_index 0-1 maps to +1, +2)
        (0, 0, "/choose move 1 +1"),
        (0, 1, "/choose move 1 +2"),
        (1, 0, "/choose move 2 +1"),
        (2, 1, "/choose move 3 +2"),
        # Ally targeting (target_index 2-3 maps to -1, -2)
        (1, 2, "/choose move 2 -1"),
        (2, 3, "/choose move 3 -2"),
        (3, 2, "/choose move 4 -1"),
    )
    def test_targeted_move_doubles(
        self, move_index: int, target_index: int, expected_command: str
    ) -> None:
        """Test targeted moves for doubles battles with +/- protocol syntax."""
        action = BattleAction(
            action_type=ActionType.MOVE,
            move_index=move_index,
            target_index=target_index,
        )
        self.assertEqual(action.to_showdown_command(), expected_command)

    def test_move_with_mega_and_target(self) -> None:
        """Test move with both Mega Evolution and target."""
        action = BattleAction(
            action_type=ActionType.MOVE, move_index=1, target_index=0, mega=True
        )
        self.assertEqual(action.to_showdown_command(), "/choose move 2 +1 mega")

    def test_move_with_tera_and_target(self) -> None:
        """Test move with both Terastallization and target."""
        action = BattleAction(
            action_type=ActionType.MOVE, move_index=0, target_index=1, tera=True
        )
        self.assertEqual(action.to_showdown_command(), "/choose move 1 +2 tera")

    def test_move_without_index_raises_error(self) -> None:
        """Test that MOVE action without move_index raises error."""
        action = BattleAction(action_type=ActionType.MOVE)
        with self.assertRaises(ValueError) as context:
            action.to_showdown_command()
        self.assertIn("move_index", str(context.exception))

    def test_switch_without_index_raises_error(self) -> None:
        """Test that SWITCH action without switch_index raises error."""
        action = BattleAction(action_type=ActionType.SWITCH)
        with self.assertRaises(ValueError) as context:
            action.to_showdown_command()
        self.assertIn("switch_index", str(context.exception))

    def test_action_is_frozen(self) -> None:
        """Test that BattleAction is immutable."""
        action = BattleAction(action_type=ActionType.MOVE, move_index=0)
        with self.assertRaises(Exception):
            action.move_index = 1  # type: ignore

    def test_action_type_enum_values(self) -> None:
        """Test ActionType enum has expected values."""
        self.assertEqual(ActionType.MOVE.value, "move")
        self.assertEqual(ActionType.SWITCH.value, "switch")

    def test_default_flags_are_false(self) -> None:
        """Test that mega and tera flags default to False."""
        action = BattleAction(action_type=ActionType.MOVE, move_index=0)
        self.assertFalse(action.mega)
        self.assertFalse(action.tera)

    def test_optional_fields_default_to_none(self) -> None:
        """Test that optional fields default to None."""
        move_action = BattleAction(action_type=ActionType.MOVE, move_index=0)
        self.assertIsNone(move_action.switch_index)
        self.assertIsNone(move_action.target_index)

        switch_action = BattleAction(action_type=ActionType.SWITCH, switch_index=0)
        self.assertIsNone(switch_action.move_index)
        self.assertIsNone(switch_action.target_index)


if __name__ == "__main__":
    unittest.main()
