"""Unit tests for TeamState."""

import json
import unittest

from python.game.schema.enums import SideCondition, Status
from python.game.schema.pokemon_state import PokemonState
from python.game.schema.team_state import TeamState


class TeamStateTest(unittest.IsolatedAsyncioTestCase):
    """Test TeamState functionality."""

    def test_side_condition_tracking_stealth_rock(self) -> None:
        """Test Stealth Rock side condition tracking."""
        team = TeamState(
            player_id="p1",
            side_conditions={SideCondition.STEALTH_ROCK: 1},
            pokemon=[],
        )

        self.assertTrue(team.has_side_condition(SideCondition.STEALTH_ROCK))
        self.assertEqual(team.get_side_condition_value(SideCondition.STEALTH_ROCK), 1)

    def test_side_condition_spikes_layers(self) -> None:
        """Test Spikes with multiple layers."""
        team = TeamState(
            player_id="p2",
            side_conditions={SideCondition.SPIKES: 2},  # 2 layers
            pokemon=[],
        )

        self.assertTrue(team.has_side_condition(SideCondition.SPIKES))
        self.assertEqual(team.get_side_condition_value(SideCondition.SPIKES), 2)

    def test_light_screen_and_reflect_combo(self) -> None:
        """Test Light Screen + Reflect combo active."""
        team = TeamState(
            player_id="p1",
            side_conditions={
                SideCondition.LIGHT_SCREEN: 5,  # 5 turns remaining
                SideCondition.REFLECT: 5,  # 5 turns remaining
            },
            pokemon=[],
        )

        self.assertTrue(team.has_side_condition(SideCondition.LIGHT_SCREEN))
        self.assertTrue(team.has_side_condition(SideCondition.REFLECT))

        conditions = team.get_side_conditions()
        self.assertEqual(len(conditions), 2)
        self.assertEqual(conditions[SideCondition.LIGHT_SCREEN], 5)
        self.assertEqual(conditions[SideCondition.REFLECT], 5)

    def test_tailwind_side_condition(self) -> None:
        """Test Tailwind side condition."""
        team = TeamState(
            player_id="p1",
            side_conditions={SideCondition.TAILWIND: 4},  # 4 turns remaining
            pokemon=[],
        )

        self.assertTrue(team.has_side_condition(SideCondition.TAILWIND))
        self.assertEqual(team.get_side_condition_value(SideCondition.TAILWIND), 4)

    def test_active_pokemon_switching(self) -> None:
        """Test active Pokemon tracking."""
        pokemon_list = [
            PokemonState(species="Landorus-Therian", current_hp=88, max_hp=100),
            PokemonState(species="Iron Crown", current_hp=100, max_hp=100),
            PokemonState(species="Raging Bolt", current_hp=75, max_hp=100),
        ]

        team = TeamState(
            player_id="p1",
            pokemon=pokemon_list,
            active_pokemon_index=0,
        )

        active = team.get_active_pokemon()
        self.assertIsNotNone(active)
        self.assertEqual(active.species, "Landorus-Therian")  # type: ignore

        # Switch to different Pokemon
        team_switched = TeamState(
            player_id="p1",
            pokemon=pokemon_list,
            active_pokemon_index=2,
        )

        active_switched = team_switched.get_active_pokemon()
        self.assertIsNotNone(active_switched)
        self.assertEqual(active_switched.species, "Raging Bolt")  # type: ignore

    def test_fainted_count_tracking(self) -> None:
        """Test fainted Pokemon counting."""
        pokemon_list = [
            PokemonState(species="Landorus-Therian", current_hp=0, max_hp=100),
            PokemonState(species="Iron Moth", current_hp=0, max_hp=100),
            PokemonState(species="Zamazenta", current_hp=37, max_hp=100),
            PokemonState(species="Iron Crown", current_hp=15, max_hp=100),
            PokemonState(species="Ogerpon-Wellspring", current_hp=35, max_hp=100),
            PokemonState(species="Raging Bolt", current_hp=56, max_hp=100),
        ]

        team = TeamState(
            player_id="p1",
            pokemon=pokemon_list,
        )

        alive = team.get_alive_pokemon()
        self.assertEqual(len(alive), 4)

        fainted = team.get_fainted_pokemon()
        self.assertEqual(len(fainted), 2)
        self.assertEqual(fainted[0].species, "Landorus-Therian")
        self.assertEqual(fainted[1].species, "Iron Moth")

    def test_get_pokemon_team(self) -> None:
        """Test getting all Pokemon with statuses."""
        pokemon_list = [
            PokemonState(
                species="Gliscor",
                status=Status.TOXIC,
                current_hp=59,
                max_hp=100,
                is_active=True,
            ),
            PokemonState(
                species="Toxapex", status=Status.NONE, current_hp=69, max_hp=100
            ),
            PokemonState(
                species="Blissey", status=Status.NONE, current_hp=91, max_hp=100
            ),
            PokemonState(
                species="Talonflame", status=Status.NONE, current_hp=0, max_hp=100
            ),
            PokemonState(
                species="Jirachi", status=Status.NONE, current_hp=94, max_hp=100
            ),
            PokemonState(
                species="Dondozo", status=Status.SLEEP, current_hp=72, max_hp=100
            ),
        ]

        team = TeamState(
            player_id="p1",
            pokemon=pokemon_list,
            active_pokemon_index=0,
        )

        all_pokemon = team.get_pokemon_team()
        self.assertEqual(len(all_pokemon), 6)
        self.assertTrue(all_pokemon[0].is_active)
        self.assertEqual(all_pokemon[0].status, Status.TOXIC)
        self.assertFalse(all_pokemon[3].is_alive())

    def test_json_serialization(self) -> None:
        """Test JSON serialization via __str__."""
        pokemon_list = [
            PokemonState(species="Kingambit", current_hp=74, max_hp=100),
        ]

        team = TeamState(
            player_id="p2",
            pokemon=pokemon_list,
            active_pokemon_index=0,
            side_conditions={
                SideCondition.STEALTH_ROCK: 1,
                SideCondition.REFLECT: 3,
            },
        )

        json_str = str(team)
        parsed = json.loads(json_str)

        self.assertEqual(parsed["player_id"], "p2")
        self.assertEqual(parsed["active_pokemon_index"], 0)
        self.assertEqual(parsed["fainted_count"], 0)
        self.assertIn("stealthrock", parsed["side_conditions"])
        self.assertIn("reflect", parsed["side_conditions"])


if __name__ == "__main__":
    unittest.main()
