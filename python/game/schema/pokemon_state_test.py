"""Unit tests for PokemonState."""

import json
import unittest

from python.game.schema.enums import Stat, Status
from python.game.schema.pokemon_state import (
    STAT_STAGE_MULTIPLIERS,
    PokemonMove,
    PokemonState,
)


class PokemonStateTest(unittest.IsolatedAsyncioTestCase):
    """Test PokemonState functionality."""

    def test_stat_boost_calculations_various_stages(self) -> None:
        """Test stat boost calculations at various stages."""
        test_cases = [
            (-6, 0.25),
            (-3, 0.4),
            (-2, 0.5),
            (-1, 2.0 / 3.0),
            (0, 1.0),
            (1, 1.5),
            (3, 2.5),
            (4, 3.0),
            (5, 3.5),
            (6, 4.0),
        ]

        for stage, expected_mult in test_cases:
            self.assertAlmostEqual(
                STAT_STAGE_MULTIPLIERS[stage],
                expected_mult,
                places=2,
                msg=f"Stage {stage} should have multiplier {expected_mult}",
            )

    def test_effective_stat_with_boost(self) -> None:
        """Test effective stat calculation with boosts."""
        landorus = PokemonState(
            species="Landorus-Therian",
            stat_boosts={Stat.ATK: -1},
        )

        effective_atk = landorus.get_effective_stat(Stat.ATK, 145)
        self.assertEqual(effective_atk, 96)

        gliscor = PokemonState(
            species="Gliscor",
            stat_boosts={Stat.ATK: 2},
        )
        effective_atk = gliscor.get_effective_stat(Stat.ATK, 95)
        self.assertEqual(effective_atk, 190)

    def test_status_condition_burn(self) -> None:
        raging_bolt = PokemonState(
            species="Raging Bolt",
            status=Status.BURN,
            current_hp=56,
            max_hp=100,
        )

        self.assertEqual(raging_bolt.status, Status.BURN)
        self.assertTrue(raging_bolt.is_alive())

    def test_hp_updates_and_fainted_state(self) -> None:
        landorus = PokemonState(
            species="Landorus-Therian",
            current_hp=29,
            max_hp=100,
        )

        self.assertTrue(landorus.is_alive())
        self.assertEqual(landorus.current_hp, 29)

        fainted_landorus = PokemonState(
            species="Landorus-Therian",
            current_hp=0,
            max_hp=100,
        )

        self.assertFalse(fainted_landorus.is_alive())
        self.assertFalse(fainted_landorus.can_switch())

    def test_volatile_conditions_protect(self) -> None:
        """Test volatile conditions like Protect."""
        gliscor = PokemonState(
            species="Gliscor",
            volatile_conditions={"protect_count": 1},
        )

        stats = gliscor.get_all_stats({Stat.ATK: 95, Stat.DEF: 125})
        self.assertEqual(stats["protect_count"], 1)

    def test_accumulated_stat_boosts(self) -> None:
        """Test multiple accumulated stat boosts (e.g., 3 Calm Minds)."""
        raging_bolt = PokemonState(
            species="Raging Bolt",
            stat_boosts={Stat.SPA: 3, Stat.SPD: 3},
            status=Status.BURN,
            current_hp=88,
            max_hp=100,
        )

        effective_spa = raging_bolt.get_effective_stat(Stat.SPA, 137)
        self.assertEqual(effective_spa, 342)

        effective_spd = raging_bolt.get_effective_stat(Stat.SPD, 113)
        self.assertEqual(effective_spd, 282)

        raging_bolt_after = PokemonState(
            species="Raging Bolt",
            stat_boosts={Stat.SPA: 1, Stat.SPD: 3},  # +3-2 = +1
            status=Status.BURN,
            current_hp=82,
            max_hp=100,
        )

        # Base 137 SpA, +1 stage = 137 * 1.5 = 205.5 -> 205
        effective_spa_after = raging_bolt_after.get_effective_stat(Stat.SPA, 137)
        self.assertEqual(effective_spa_after, 205)

    def test_get_all_stats_complete(self) -> None:
        """Test get_all_stats returns complete stat dictionary."""
        pokemon = PokemonState(
            species="Dragonite",
            current_hp=84,
            max_hp=100,
            stat_boosts={Stat.ATK: 1, Stat.SPE: 1},
            status=Status.NONE,
        )

        base_stats = {
            Stat.ATK: 134,
            Stat.DEF: 95,
            Stat.SPA: 100,
            Stat.SPD: 100,
            Stat.SPE: 80,
        }

        stats = pokemon.get_all_stats(base_stats)

        self.assertEqual(stats["hp"]["current"], 84)
        self.assertEqual(stats["hp"]["max"], 100)
        self.assertEqual(stats["atk"], 201)  # 134 * 1.5 = 201
        self.assertEqual(stats["spe"], 120)  # 80 * 1.5 = 120
        self.assertEqual(stats["status"], "none")
        self.assertEqual(stats["accuracy_stage"], 0)
        self.assertEqual(stats["evasion_stage"], 0)

    def test_json_serialization(self) -> None:
        """Test JSON serialization via __str__."""
        pokemon = PokemonState(
            species="Iron Crown",
            level=100,
            current_hp=76,
            max_hp=100,
            stat_boosts={Stat.DEF: 1},
            item="Leftovers",
            ability="Quark Drive",
            has_terastallized=True,
            tera_type="Fairy",
        )

        json_str = str(pokemon)
        parsed = json.loads(json_str)

        self.assertEqual(parsed["species"], "Iron Crown")
        self.assertEqual(parsed["hp"]["current"], 76)
        self.assertEqual(parsed["stat_boosts"]["def"], 1)
        self.assertEqual(parsed["has_terastallized"], True)
        self.assertEqual(parsed["tera_type"], "Fairy")

    def test_active_effects_supreme_overlord(self) -> None:
        """Test active effects tracking (e.g., Supreme Overlord)."""
        kingambit = PokemonState(
            species="Kingambit",
            current_hp=74,
            max_hp=100,
            has_terastallized=True,
            tera_type="Fairy",
            active_effects={"supreme_overlord_fallen": 4},
        )

        stats = kingambit.get_all_stats({Stat.ATK: 135})
        self.assertEqual(stats["supreme_overlord_fallen"], 4)


if __name__ == "__main__":
    unittest.main()
