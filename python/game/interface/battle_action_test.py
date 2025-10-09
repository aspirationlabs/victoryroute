"""Unit tests for BattleAction."""

import unittest

from absl.testing import parameterized

from python.game.interface.battle_action import ActionType, BattleAction


class BattleActionTest(parameterized.TestCase):
    """Test BattleAction functionality."""

    @parameterized.parameters(
        ("Earthquake", "/choose move earthquake"),
        ("Flamethrower", "/choose move flamethrower"),
        ("Surf", "/choose move surf"),
        ("Thunderbolt", "/choose move thunderbolt"),
        ("Stealth Rock", "/choose move stealthrock"),
        ("U-turn", "/choose move uturn"),
        ("Will-O-Wisp", "/choose move willowisp"),
    )
    def test_basic_move_action(self, move_name: str, expected_command: str) -> None:
        """Test basic move actions convert to correct commands with normalization."""
        action = BattleAction(action_type=ActionType.MOVE, move_name=move_name)
        self.assertEqual(action.to_showdown_command(), expected_command)

    @parameterized.parameters(
        ("Pikachu", "/choose switch pikachu"),
        ("Charizard", "/choose switch charizard"),
        ("Blastoise", "/choose switch blastoise"),
        ("Venusaur", "/choose switch venusaur"),
        ("Mewtwo", "/choose switch mewtwo"),
        ("Dragonite", "/choose switch dragonite"),
        ("Slowking-Galar", "/choose switch slowkinggalar"),
        ("Toxapex", "/choose switch toxapex"),
    )
    def test_basic_switch_action(
        self, switch_pokemon_name: str, expected_command: str
    ) -> None:
        """Test basic switch actions convert to correct commands with normalization."""
        action = BattleAction(
            action_type=ActionType.SWITCH, switch_pokemon_name=switch_pokemon_name
        )
        self.assertEqual(action.to_showdown_command(), expected_command)

    @parameterized.parameters(
        ("Earthquake", "/choose move earthquake mega"),
        ("Flamethrower", "/choose move flamethrower mega"),
        ("Surf", "/choose move surf mega"),
        ("Thunderbolt", "/choose move thunderbolt mega"),
    )
    def test_mega_evolution_move(self, move_name: str, expected_command: str) -> None:
        """Test move with Mega Evolution and normalization."""
        action = BattleAction(
            action_type=ActionType.MOVE, move_name=move_name, mega=True
        )
        self.assertEqual(action.to_showdown_command(), expected_command)

    @parameterized.parameters(
        ("Earthquake", "/choose move earthquake terastallize"),
        ("Flamethrower", "/choose move flamethrower terastallize"),
        ("Surf", "/choose move surf terastallize"),
        ("Thunderbolt", "/choose move thunderbolt terastallize"),
    )
    def test_terastallization_move(self, move_name: str, expected_command: str) -> None:
        """Test move with Terastallization and normalization."""
        action = BattleAction(
            action_type=ActionType.MOVE, move_name=move_name, tera=True
        )
        self.assertEqual(action.to_showdown_command(), expected_command)

    @parameterized.parameters(
        # Opponent targeting (target_index 0-1 maps to +1, +2)
        ("Earthquake", 0, "/choose move earthquake +1"),
        ("Earthquake", 1, "/choose move earthquake +2"),
        ("Flamethrower", 0, "/choose move flamethrower +1"),
        ("Surf", 1, "/choose move surf +2"),
        # Ally targeting (target_index 2-3 maps to -1, -2)
        ("Flamethrower", 2, "/choose move flamethrower -1"),
        ("Surf", 3, "/choose move surf -2"),
        ("Thunderbolt", 2, "/choose move thunderbolt -1"),
    )
    def test_targeted_move_doubles(
        self, move_name: str, target_index: int, expected_command: str
    ) -> None:
        """Test targeted moves for doubles battles with +/- protocol syntax and normalization."""
        action = BattleAction(
            action_type=ActionType.MOVE,
            move_name=move_name,
            target_index=target_index,
        )
        self.assertEqual(action.to_showdown_command(), expected_command)

    def test_move_with_mega_and_target(self) -> None:
        """Test move with both Mega Evolution and target with normalization."""
        action = BattleAction(
            action_type=ActionType.MOVE,
            move_name="Flamethrower",
            target_index=0,
            mega=True,
        )
        self.assertEqual(
            action.to_showdown_command(), "/choose move flamethrower +1 mega"
        )

    def test_move_with_tera_and_target(self) -> None:
        """Test move with both Terastallization and target with normalization."""
        action = BattleAction(
            action_type=ActionType.MOVE,
            move_name="Earthquake",
            target_index=1,
            tera=True,
        )
        self.assertEqual(
            action.to_showdown_command(), "/choose move earthquake +2 terastallize"
        )

    def test_move_without_name_raises_error(self) -> None:
        """Test that MOVE action without move_name raises error."""
        action = BattleAction(action_type=ActionType.MOVE)
        with self.assertRaises(ValueError) as context:
            action.to_showdown_command()
        self.assertIn("move_name", str(context.exception))

    def test_switch_without_name_raises_error(self) -> None:
        """Test that SWITCH action without switch_pokemon_name raises error."""
        action = BattleAction(action_type=ActionType.SWITCH)
        with self.assertRaises(ValueError) as context:
            action.to_showdown_command()
        self.assertIn("switch_pokemon_name", str(context.exception))

    def test_action_is_frozen(self) -> None:
        """Test that BattleAction is immutable."""
        action = BattleAction(action_type=ActionType.MOVE, move_name="Earthquake")
        with self.assertRaises(Exception):
            action.move_name = "Flamethrower"  # type: ignore

    def test_action_type_enum_values(self) -> None:
        """Test ActionType enum has expected values."""
        self.assertEqual(ActionType.MOVE.value, "move")
        self.assertEqual(ActionType.SWITCH.value, "switch")

    def test_default_flags_are_false(self) -> None:
        """Test that mega and tera flags default to False."""
        action = BattleAction(action_type=ActionType.MOVE, move_name="Earthquake")
        self.assertFalse(action.mega)
        self.assertFalse(action.tera)

    def test_optional_fields_default_to_none(self) -> None:
        """Test that optional fields default to None."""
        move_action = BattleAction(action_type=ActionType.MOVE, move_name="Earthquake")
        self.assertIsNone(move_action.switch_pokemon_name)
        self.assertIsNone(move_action.target_index)

        switch_action = BattleAction(
            action_type=ActionType.SWITCH, switch_pokemon_name="Pikachu"
        )
        self.assertIsNone(switch_action.move_name)
        self.assertIsNone(switch_action.target_index)


if __name__ == "__main__":
    unittest.main()
