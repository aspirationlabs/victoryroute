"""Unit tests for battle simulator."""

from typing import Dict, List, Optional

from absl.testing import absltest, parameterized

from python.agents.tools.battle_simulator import (
    BattleSimulator,
    EffortValues,
    IndividualValues,
    MoveResult,
)
from python.game.data.game_data import GameData
from python.game.schema.enums import SideCondition, Stat, Status, Terrain, Weather
from python.game.schema.field_state import FieldState
from python.game.schema.pokemon_state import PokemonMove, PokemonState


class BattleSimulatorTest(parameterized.TestCase):
    def setUp(self) -> None:
        game_data = GameData()
        self.simulator = BattleSimulator(game_data)

    @parameterized.named_parameters(
        (
            "abomasnow",
            "Abomasnow",
            100,
            IndividualValues(31, 31, 31, 31, 31, 31),
            EffortValues(248, 0, 252, 0, 0, 8),
            "Bashful",
            {
                "hp": 383,
                "attack": 220,
                "defense": 249,
                "special_attack": 220,
                "special_defense": 206,
                "speed": 158,
            },
        ),
        (
            "blaziken",
            "Blaziken",
            100,
            IndividualValues(31, 31, 31, 31, 31, 31),
            EffortValues(0, 252, 4, 0, 0, 252),
            "Bashful",
            {
                "hp": 301,
                "attack": 339,
                "defense": 177,
                "special_attack": 256,
                "special_defense": 176,
                "speed": 259,
            },
        ),
        (
            "alakazam",
            "Alakazam",
            100,
            IndividualValues(31, 0, 31, 31, 31, 31),
            EffortValues(0, 0, 4, 252, 0, 252),
            "Bashful",
            {
                "hp": 251,
                "attack": 105,
                "defense": 127,
                "special_attack": 369,
                "special_defense": 226,
                "speed": 339,
            },
        ),
        (
            "kyogre",
            "Kyogre",
            100,
            IndividualValues(31, 0, 31, 31, 31, 31),
            EffortValues(248, 0, 164, 80, 0, 16),
            "Bashful",
            {
                "hp": 403,
                "attack": 205,
                "defense": 257,
                "special_attack": 356,
                "special_defense": 316,
                "speed": 220,
            },
        ),
        (
            "ragingbolt",
            "Raging Bolt",
            100,
            IndividualValues(31, 20, 31, 31, 31, 31),
            EffortValues(0, 0, 4, 252, 0, 252),
            "Bashful",
            {
                "hp": 391,
                "attack": 171,
                "defense": 219,
                "special_attack": 373,
                "special_defense": 214,
                "speed": 249,
            },
        ),
        (
            "porygonz",
            "Porygon-Z",
            100,
            IndividualValues(31, 31, 31, 31, 31, 31),
            EffortValues(156, 0, 72, 144, 0, 136),
            "Bashful",
            {
                "hp": 350,
                "attack": 196,
                "defense": 194,
                "special_attack": 342,
                "special_defense": 186,
                "speed": 250,
            },
        ),
        (
            "darmanitan_galar",
            "Darmanitan-Galar",
            100,
            IndividualValues(31, 31, 31, 31, 31, 31),
            EffortValues(0, 252, 0, 0, 4, 252),
            "Jolly",
            {
                "hp": 351,
                "attack": 379,
                "defense": 146,
                "special_attack": 86,
                "special_defense": 147,
                "speed": 317,
            },
        ),
    )
    def test_get_pokemon_stats(
        self,
        species: str,
        level: int,
        ivs: IndividualValues,
        evs: EffortValues,
        nature: str,
        expected_stats: Dict[str, int],
    ) -> None:
        pokemon = PokemonState(species=species, level=level)
        stats = self.simulator.get_pokemon_stats(
            pokemon, level=level, ivs=ivs, evs=evs, nature=nature
        )

        self.assertEqual(stats.hp, expected_stats["hp"])
        self.assertEqual(stats.attack, expected_stats["attack"])
        self.assertEqual(stats.defense, expected_stats["defense"])
        self.assertEqual(stats.special_attack, expected_stats["special_attack"])
        self.assertEqual(stats.special_defense, expected_stats["special_defense"])
        self.assertEqual(stats.speed, expected_stats["speed"])

    @parameterized.named_parameters(
        (
            "basic_physical",
            PokemonState(
                species="Landorus-Therian", level=100, current_hp=300, max_hp=300
            ),
            PokemonState(species="Incineroar", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            None,
            MoveResult(
                min_damage=303,
                max_damage=357,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=455,
                crit_max_damage=535,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "basic_special",
            PokemonState(species="Kyogre", level=100, current_hp=300, max_hp=300),
            PokemonState(species="Groudon", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Water Spout", current_pp=5, max_pp=8),
            None,
            MoveResult(
                min_damage=464,
                max_damage=546,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=696,
                crit_max_damage=819,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "stab_bonus",
            PokemonState(species="Garchomp", level=100, current_hp=300, max_hp=300),
            PokemonState(species="Incineroar", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            None,
            MoveResult(
                min_damage=280,
                max_damage=330,
                knockout_probability=0.5,
                critical_hit_probability=1 / 24,
                crit_min_damage=420,
                crit_max_damage=495,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "super_effective",
            PokemonState(
                species="Landorus-Therian", level=100, current_hp=300, max_hp=300
            ),
            PokemonState(species="Heatran", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            None,
            MoveResult(
                min_damage=545,
                max_damage=642,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=818,
                crit_max_damage=963,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "not_very_effective",
            PokemonState(
                species="Landorus-Therian", level=100, current_hp=300, max_hp=300
            ),
            PokemonState(species="Tornadus", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            None,
            MoveResult(
                min_damage=0,
                max_damage=0,
                knockout_probability=0.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=0,
                crit_max_damage=0,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "choice_band_physical",
            PokemonState(
                species="Landorus-Therian",
                level=100,
                current_hp=300,
                max_hp=300,
                item="Choice Band",
            ),
            PokemonState(species="Incineroar", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            None,
            MoveResult(
                min_damage=455,
                max_damage=535,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=682,
                crit_max_damage=803,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "choice_specs_special",
            PokemonState(
                species="Kyogre",
                level=100,
                current_hp=300,
                max_hp=300,
                item="Choice Specs",
            ),
            PokemonState(species="Groudon", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Water Spout", current_pp=5, max_pp=8),
            None,
            MoveResult(
                min_damage=696,
                max_damage=819,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=1044,
                crit_max_damage=1228,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "life_orb_physical",
            PokemonState(
                species="Landorus-Therian",
                level=100,
                current_hp=300,
                max_hp=300,
                item="Life Orb",
            ),
            PokemonState(species="Incineroar", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            None,
            MoveResult(
                min_damage=394,
                max_damage=464,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=591,
                crit_max_damage=696,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "expert_belt_super_effective",
            PokemonState(
                species="Landorus-Therian",
                level=100,
                current_hp=300,
                max_hp=300,
                item="Expert Belt",
            ),
            PokemonState(species="Heatran", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            None,
            MoveResult(
                min_damage=654,
                max_damage=770,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=982,
                crit_max_damage=1155,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "mystic_water_special",
            PokemonState(
                species="Kyogre",
                level=100,
                current_hp=300,
                max_hp=300,
                item="Mystic Water",
            ),
            PokemonState(species="Groudon", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Water Spout", current_pp=5, max_pp=8),
            None,
            MoveResult(
                min_damage=556,
                max_damage=655,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=835,
                crit_max_damage=982,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "choice_specs_no_effect_on_physical",
            PokemonState(
                species="Landorus-Therian",
                level=100,
                current_hp=300,
                max_hp=300,
                item="Choice Specs",
            ),
            PokemonState(species="Incineroar", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            None,
            MoveResult(
                min_damage=303,
                max_damage=357,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=455,
                crit_max_damage=535,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "choice_band_no_effect_on_special",
            PokemonState(
                species="Kyogre",
                level=100,
                current_hp=300,
                max_hp=300,
                item="Choice Band",
            ),
            PokemonState(species="Groudon", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Water Spout", current_pp=5, max_pp=8),
            None,
            MoveResult(
                min_damage=464,
                max_damage=546,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=696,
                crit_max_damage=819,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "type_boost_no_match",
            PokemonState(
                species="Landorus-Therian",
                level=100,
                current_hp=300,
                max_hp=300,
                item="Charcoal",
            ),
            PokemonState(species="Incineroar", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            None,
            MoveResult(
                min_damage=303,
                max_damage=357,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=455,
                crit_max_damage=535,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "stat_boost_attack",
            PokemonState(
                species="Landorus-Therian",
                level=100,
                current_hp=300,
                max_hp=300,
                stat_boosts={Stat.ATK: 2},
            ),
            PokemonState(species="Incineroar", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            None,
            MoveResult(
                min_damage=601,
                max_damage=708,
                knockout_probability=1.0,
                critical_hit_probability=1.0 / 24,
                crit_min_damage=902,
                crit_max_damage=1062,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "stat_boost_defense",
            PokemonState(
                species="Landorus-Therian", level=100, current_hp=300, max_hp=300
            ),
            PokemonState(
                species="Incineroar",
                level=100,
                current_hp=300,
                max_hp=300,
                stat_boosts={Stat.DEF: 2},
            ),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            None,
            MoveResult(
                min_damage=153,
                max_damage=180,
                knockout_probability=0.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=455,
                crit_max_damage=535,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "burn_reduces_physical",
            PokemonState(
                species="Landorus-Therian",
                level=100,
                current_hp=300,
                max_hp=300,
                status=Status.BURN,
            ),
            PokemonState(species="Incineroar", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            None,
            MoveResult(
                min_damage=151,
                max_damage=178,
                knockout_probability=0.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=227,
                crit_max_damage=267,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "rain_boosts_water",
            PokemonState(species="Kyogre", level=100, current_hp=300, max_hp=300),
            PokemonState(species="Groudon", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Water Spout", current_pp=5, max_pp=8),
            FieldState(weather=Weather.RAIN, weather_turns_remaining=5),
            MoveResult(
                min_damage=696,
                max_damage=819,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=1044,
                crit_max_damage=1228,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "sun_reduces_water",
            PokemonState(species="Kyogre", level=100, current_hp=300, max_hp=300),
            PokemonState(species="Groudon", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Water Spout", current_pp=5, max_pp=8),
            FieldState(weather=Weather.SUN, weather_turns_remaining=5),
            MoveResult(
                min_damage=232,
                max_damage=273,
                knockout_probability=0.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=348,
                crit_max_damage=409,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "tera_stab_boost",
            PokemonState(
                species="Landorus-Therian",
                level=100,
                current_hp=300,
                max_hp=300,
                has_terastallized=True,
                tera_type="Ground",
            ),
            PokemonState(species="Incineroar", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            None,
            MoveResult(
                min_damage=404,
                max_damage=476,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=606,
                crit_max_damage=714,
                status_effects={},
                additional_effects=[],
            ),
        ),
    )
    def test_estimate_move_result(
        self,
        attacker: PokemonState,
        defender: PokemonState,
        move: PokemonMove,
        field_state: FieldState,
        expected_result: MoveResult,
    ) -> None:
        result = self.simulator.estimate_move_result(
            attacker, defender, move, field_state
        )

        self.assertEqual(result, expected_result)

    def test_estimate_move_result_status_move(self) -> None:
        attacker = PokemonState(
            species="Amoonguss", level=100, current_hp=300, max_hp=300
        )
        defender = PokemonState(
            species="Landorus-Therian", level=100, current_hp=300, max_hp=300
        )
        move = PokemonMove(name="Spore", current_pp=15, max_pp=24)

        result = self.simulator.estimate_move_result(attacker, defender, move)

        self.assertEqual(result.min_damage, 0)
        self.assertEqual(result.max_damage, 0)
        self.assertEqual(result.knockout_probability, 0.0)

    def test_estimate_move_result_knockout_probability(self) -> None:
        attacker = PokemonState(
            species="Landorus-Therian", level=100, current_hp=300, max_hp=300
        )
        defender = PokemonState(
            species="Incineroar", level=100, current_hp=50, max_hp=300
        )
        move = PokemonMove(name="Earthquake", current_pp=10, max_pp=16)

        result = self.simulator.estimate_move_result(attacker, defender, move)

        self.assertEqual(result.knockout_probability, 1.0)

    @parameterized.named_parameters(
        (
            "body_press",
            PokemonState(species="Corviknight", level=100, current_hp=300, max_hp=300),
            PokemonState(species="Blissey", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Body Press", current_pp=10, max_pp=16),
            MoveResult(
                min_damage=299,
                max_damage=352,
                knockout_probability=0.5,
                critical_hit_probability=1 / 24,
                crit_min_damage=448,
                crit_max_damage=528,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "psyshock",
            PokemonState(species="Alakazam", level=100, current_hp=300, max_hp=300),
            PokemonState(species="Blissey", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Psyshock", current_pp=10, max_pp=16),
            MoveResult(
                min_damage=267,
                max_damage=315,
                knockout_probability=0.5,
                critical_hit_probability=1 / 24,
                crit_min_damage=401,
                crit_max_damage=472,
                status_effects={},
                additional_effects=[],
            ),
        ),
    )
    def test_stat_override_moves(
        self,
        attacker: PokemonState,
        defender: PokemonState,
        move: PokemonMove,
        expected_result: MoveResult,
    ) -> None:
        result = self.simulator.estimate_move_result(attacker, defender, move)

        self.assertEqual(result, expected_result)

    @parameterized.named_parameters(
        (
            "electric_terrain",
            PokemonState(species="Zapdos", level=100, current_hp=300, max_hp=300),
            PokemonState(species="Gyarados", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Thunderbolt", current_pp=15, max_pp=24),
            FieldState(terrain=Terrain.ELECTRIC, terrain_turns_remaining=5),
            MoveResult(
                min_damage=459,
                max_damage=540,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=688,
                crit_max_damage=810,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "grassy_terrain",
            PokemonState(species="Venusaur", level=100, current_hp=300, max_hp=300),
            PokemonState(species="Blastoise", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Solar Beam", current_pp=10, max_pp=16),
            FieldState(terrain=Terrain.GRASSY, terrain_turns_remaining=5),
            MoveResult(
                min_damage=328,
                max_damage=386,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=492,
                crit_max_damage=579,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "psychic_terrain",
            PokemonState(species="Alakazam", level=100, current_hp=300, max_hp=300),
            PokemonState(species="Machamp", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Psychic", current_pp=10, max_pp=16),
            FieldState(terrain=Terrain.PSYCHIC, terrain_turns_remaining=5),
            MoveResult(
                min_damage=348,
                max_damage=409,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=522,
                crit_max_damage=614,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "misty_terrain",
            PokemonState(species="Dragonite", level=100, current_hp=300, max_hp=300),
            PokemonState(species="Togekiss", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Dragon Claw", current_pp=15, max_pp=24),
            FieldState(terrain=Terrain.MISTY, terrain_turns_remaining=5),
            MoveResult(
                min_damage=0,
                max_damage=0,
                knockout_probability=0.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=0,
                crit_max_damage=0,
                status_effects={},
                additional_effects=[],
            ),
        ),
    )
    def test_terrain_effects(
        self,
        attacker: PokemonState,
        defender: PokemonState,
        move: PokemonMove,
        field_state: FieldState,
        expected_result: MoveResult,
    ) -> None:
        result = self.simulator.estimate_move_result(
            attacker, defender, move, field_state
        )

        self.assertEqual(result, expected_result)

    @parameterized.named_parameters(
        (
            "reflect_physical",
            PokemonState(
                species="Landorus-Therian", level=100, current_hp=300, max_hp=300
            ),
            PokemonState(species="Incineroar", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            [SideCondition.REFLECT],
            MoveResult(
                min_damage=151,
                max_damage=178,
                knockout_probability=0.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=227,
                crit_max_damage=267,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "light_screen_special",
            PokemonState(species="Kyogre", level=100, current_hp=300, max_hp=300),
            PokemonState(species="Groudon", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Water Spout", current_pp=5, max_pp=8),
            [SideCondition.LIGHT_SCREEN],
            MoveResult(
                min_damage=232,
                max_damage=273,
                knockout_probability=0.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=348,
                crit_max_damage=409,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "aurora_veil_physical",
            PokemonState(
                species="Landorus-Therian", level=100, current_hp=300, max_hp=300
            ),
            PokemonState(species="Incineroar", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            [SideCondition.AURORA_VEIL],
            MoveResult(
                min_damage=151,
                max_damage=178,
                knockout_probability=0.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=227,
                crit_max_damage=267,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "aurora_veil_special",
            PokemonState(species="Kyogre", level=100, current_hp=300, max_hp=300),
            PokemonState(species="Incineroar", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Surf", current_pp=15, max_pp=24),
            [SideCondition.AURORA_VEIL],
            MoveResult(
                min_damage=140,
                max_damage=165,
                knockout_probability=0.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=210,
                crit_max_damage=247,
                status_effects={},
                additional_effects=[],
            ),
        ),
    )
    def test_screen_effects(
        self,
        attacker: PokemonState,
        defender: PokemonState,
        move: PokemonMove,
        screens: List[SideCondition],
        expected_result: MoveResult,
    ) -> None:
        result = self.simulator.estimate_move_result(
            attacker, defender, move, None, screens
        )

        self.assertEqual(result, expected_result)

    @parameterized.named_parameters(
        (
            "negative_attack_boost_ignored_on_crit",
            PokemonState(
                species="Landorus-Therian",
                level=100,
                current_hp=300,
                max_hp=300,
                stat_boosts={Stat.ATK: -2},
            ),
            PokemonState(species="Incineroar", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            MoveResult(
                min_damage=153,
                max_damage=180,
                knockout_probability=0.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=455,
                crit_max_damage=535,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "positive_defense_boost_ignored_on_crit",
            PokemonState(
                species="Landorus-Therian", level=100, current_hp=300, max_hp=300
            ),
            PokemonState(
                species="Incineroar",
                level=100,
                current_hp=300,
                max_hp=300,
                stat_boosts={Stat.DEF: 2},
            ),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            MoveResult(
                min_damage=153,
                max_damage=180,
                knockout_probability=0.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=455,
                crit_max_damage=535,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "positive_attack_boost_kept_on_crit",
            PokemonState(
                species="Landorus-Therian",
                level=100,
                current_hp=300,
                max_hp=300,
                stat_boosts={Stat.ATK: 2},
            ),
            PokemonState(species="Incineroar", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            MoveResult(
                min_damage=601,
                max_damage=708,
                knockout_probability=1.0,
                critical_hit_probability=1.0 / 24,
                crit_min_damage=902,
                crit_max_damage=1062,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "negative_defense_boost_kept_on_crit",
            PokemonState(
                species="Landorus-Therian", level=100, current_hp=300, max_hp=300
            ),
            PokemonState(
                species="Incineroar",
                level=100,
                current_hp=300,
                max_hp=300,
                stat_boosts={Stat.DEF: -2},
            ),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            MoveResult(
                min_damage=604,
                max_damage=711,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=906,
                crit_max_damage=1066,
                status_effects={},
                additional_effects=[],
            ),
        ),
    )
    def test_critical_hit_stat_boosts(
        self,
        attacker: PokemonState,
        defender: PokemonState,
        move: PokemonMove,
        expected_result: MoveResult,
    ) -> None:
        result = self.simulator.estimate_move_result(attacker, defender, move)

        self.assertEqual(result, expected_result)

    @parameterized.named_parameters(
        dict(
            testcase_name="adaptability_stab",
            attacker=PokemonState(
                species="Porygon-Z",
                level=100,
                current_hp=300,
                max_hp=300,
                ability="Adaptability",
            ),
            defender=PokemonState(
                species="Blissey", level=100, current_hp=300, max_hp=300
            ),
            move=PokemonMove(name="Tri Attack", current_pp=10, max_pp=16),
            baseline_attacker=PokemonState(
                species="Porygon-Z", level=100, current_hp=300, max_hp=300
            ),
            baseline_defender=None,
            field_state=None,
            defender_side_conditions=None,
            expected_ratio=4 / 3,
        ),
        dict(
            testcase_name="technician_low_base_power_boost",
            attacker=PokemonState(
                species="Scizor",
                level=100,
                current_hp=300,
                max_hp=300,
                ability="Technician",
            ),
            defender=PokemonState(
                species="Togekiss", level=100, current_hp=300, max_hp=300
            ),
            move=PokemonMove(name="Bullet Punch", current_pp=10, max_pp=16),
            baseline_attacker=PokemonState(
                species="Scizor", level=100, current_hp=300, max_hp=300
            ),
            baseline_defender=None,
            field_state=None,
            defender_side_conditions=None,
            expected_ratio=1.5,
        ),
        dict(
            testcase_name="huge_power_attack_doubling",
            attacker=PokemonState(
                species="Azumarill",
                level=100,
                current_hp=300,
                max_hp=300,
                ability="Huge Power",
            ),
            defender=PokemonState(
                species="Garchomp", level=100, current_hp=300, max_hp=300
            ),
            move=PokemonMove(name="Play Rough", current_pp=10, max_pp=16),
            baseline_attacker=PokemonState(
                species="Azumarill", level=100, current_hp=300, max_hp=300
            ),
            baseline_defender=None,
            field_state=None,
            defender_side_conditions=None,
            expected_ratio=2.0,
        ),
        dict(
            testcase_name="guts_ignores_burn_penalty",
            attacker=PokemonState(
                species="Conkeldurr",
                level=100,
                current_hp=300,
                max_hp=300,
                ability="Guts",
                status=Status.BURN,
            ),
            defender=PokemonState(
                species="Heatran", level=100, current_hp=300, max_hp=300
            ),
            move=PokemonMove(name="Close Combat", current_pp=5, max_pp=8),
            baseline_attacker=PokemonState(
                species="Conkeldurr",
                level=100,
                current_hp=300,
                max_hp=300,
                status=Status.BURN,
            ),
            baseline_defender=None,
            field_state=None,
            defender_side_conditions=None,
            expected_ratio=3.0,
        ),
        dict(
            testcase_name="thick_fat_halves_fire_damage",
            attacker=PokemonState(
                species="Charizard", level=100, current_hp=300, max_hp=300
            ),
            defender=PokemonState(
                species="Snorlax",
                level=100,
                current_hp=300,
                max_hp=300,
                ability="Thick Fat",
            ),
            move=PokemonMove(name="Flamethrower", current_pp=15, max_pp=24),
            baseline_attacker=None,
            baseline_defender=PokemonState(
                species="Snorlax", level=100, current_hp=300, max_hp=300
            ),
            field_state=None,
            defender_side_conditions=None,
            expected_ratio=0.5,
        ),
        dict(
            testcase_name="mold_breaker_ignores_fur_coat",
            attacker=PokemonState(
                species="Haxorus",
                level=100,
                current_hp=300,
                max_hp=300,
                ability="Mold Breaker",
            ),
            defender=PokemonState(
                species="Furfrou",
                level=100,
                current_hp=300,
                max_hp=300,
                ability="Fur Coat",
            ),
            move=PokemonMove(name="Outrage", current_pp=10, max_pp=16),
            baseline_attacker=PokemonState(
                species="Haxorus", level=100, current_hp=300, max_hp=300
            ),
            baseline_defender=PokemonState(
                species="Furfrou", level=100, current_hp=300, max_hp=300
            ),
            field_state=None,
            defender_side_conditions=None,
            expected_ratio=1.0,
        ),
        dict(
            testcase_name="levitate_grants_ground_immunity",
            attacker=PokemonState(
                species="Landorus-Therian", level=100, current_hp=300, max_hp=300
            ),
            defender=PokemonState(
                species="Gengar",
                level=100,
                current_hp=300,
                max_hp=300,
                ability="Levitate",
            ),
            move=PokemonMove(name="Earthquake", current_pp=10, max_pp=16),
            baseline_attacker=None,
            baseline_defender=PokemonState(
                species="Gengar", level=100, current_hp=300, max_hp=300
            ),
            field_state=None,
            defender_side_conditions=None,
            expected_ratio=0.0,
        ),
        dict(
            testcase_name="tinted_lens_doubles_resisted_damage",
            attacker=PokemonState(
                species="Yanmega",
                level=100,
                current_hp=300,
                max_hp=300,
                ability="Tinted Lens",
            ),
            defender=PokemonState(
                species="Rotom-Heat", level=100, current_hp=300, max_hp=300
            ),
            move=PokemonMove(name="Air Slash", current_pp=15, max_pp=24),
            baseline_attacker=PokemonState(
                species="Yanmega", level=100, current_hp=300, max_hp=300
            ),
            baseline_defender=None,
            field_state=None,
            defender_side_conditions=None,
            expected_ratio=2.0,
        ),
        dict(
            testcase_name="solid_rock_reduces_super_effective_damage",
            attacker=PokemonState(
                species="Greninja", level=100, current_hp=300, max_hp=300
            ),
            defender=PokemonState(
                species="Rhyperior",
                level=100,
                current_hp=300,
                max_hp=300,
                ability="Solid Rock",
            ),
            move=PokemonMove(name="Surf", current_pp=15, max_pp=24),
            baseline_attacker=None,
            baseline_defender=PokemonState(
                species="Rhyperior", level=100, current_hp=300, max_hp=300
            ),
            field_state=None,
            defender_side_conditions=None,
            expected_ratio=0.75,
        ),
        dict(
            testcase_name="multiscale_halves_when_healthy",
            attacker=PokemonState(
                species="Lapras", level=100, current_hp=300, max_hp=300
            ),
            defender=PokemonState(
                species="Dragonite",
                level=100,
                current_hp=300,
                max_hp=300,
                ability="Multiscale",
            ),
            move=PokemonMove(name="Ice Beam", current_pp=10, max_pp=16),
            baseline_attacker=None,
            baseline_defender=PokemonState(
                species="Dragonite", level=100, current_hp=300, max_hp=300
            ),
            field_state=None,
            defender_side_conditions=None,
            expected_ratio=0.5,
        ),
    )
    def test_common_ability_modifiers(
        self,
        attacker: PokemonState,
        defender: PokemonState,
        move: PokemonMove,
        baseline_attacker: Optional[PokemonState],
        baseline_defender: Optional[PokemonState],
        field_state: Optional[FieldState],
        defender_side_conditions: Optional[List[SideCondition]],
        expected_ratio: float,
        delta: float = 0.05,
    ) -> None:
        ability_result = self.simulator.estimate_move_result(
            attacker, defender, move, field_state, defender_side_conditions
        )

        comparison_attacker = baseline_attacker or attacker
        comparison_defender = baseline_defender or defender

        baseline_result = self.simulator.estimate_move_result(
            comparison_attacker,
            comparison_defender,
            move,
            field_state,
            defender_side_conditions,
        )

        baseline_max = baseline_result.max_damage
        ability_max = ability_result.max_damage

        if baseline_max == 0:
            self.assertEqual(expected_ratio, 0.0)
            self.assertEqual(ability_max, 0)
        else:
            ratio = ability_max / baseline_max
            self.assertAlmostEqual(ratio, expected_ratio, delta=delta)
            if expected_ratio > 1:
                self.assertGreater(ability_max, baseline_max)
            elif expected_ratio < 1:
                self.assertLess(ability_max, baseline_max)

        if expected_ratio == 0.0:
            self.assertEqual(ability_result.min_damage, 0)
            self.assertEqual(ability_result.max_damage, 0)

    @parameterized.named_parameters(
        (
            "sandstorm_rock_spdef_boost",
            PokemonState(species="Alakazam", level=100, current_hp=300, max_hp=300),
            PokemonState(species="Golem", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Psychic", current_pp=10, max_pp=16),
            FieldState(weather=Weather.SANDSTORM, weather_turns_remaining=5),
            MoveResult(
                min_damage=105,
                max_damage=124,
                knockout_probability=0.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=158,
                crit_max_damage=186,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "sandstorm_no_boost_physical",
            PokemonState(species="Machamp", level=100, current_hp=300, max_hp=300),
            PokemonState(species="Tyranitar", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Cross Chop", current_pp=5, max_pp=8),
            FieldState(weather=Weather.SANDSTORM, weather_turns_remaining=5),
            MoveResult(
                min_damage=489,
                max_damage=576,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=734,
                crit_max_damage=864,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "snow_ice_def_boost",
            PokemonState(species="Machamp", level=100, current_hp=300, max_hp=300),
            PokemonState(species="Glaceon", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Cross Chop", current_pp=5, max_pp=8),
            FieldState(weather=Weather.SNOW, weather_turns_remaining=5),
            MoveResult(
                min_damage=165,
                max_damage=195,
                knockout_probability=0.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=248,
                crit_max_damage=292,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "snow_no_boost_special",
            PokemonState(species="Alakazam", level=100, current_hp=300, max_hp=300),
            PokemonState(species="Glaceon", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Psychic", current_pp=10, max_pp=16),
            FieldState(weather=Weather.SNOW, weather_turns_remaining=5),
            MoveResult(
                min_damage=124,
                max_damage=147,
                knockout_probability=0.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=187,
                crit_max_damage=220,
                status_effects={},
                additional_effects=[],
            ),
        ),
    )
    def test_weather_stat_boosts(
        self,
        attacker: PokemonState,
        defender: PokemonState,
        move: PokemonMove,
        field_state: FieldState,
        expected_result: MoveResult,
    ) -> None:
        result = self.simulator.estimate_move_result(
            attacker, defender, move, field_state
        )

        self.assertEqual(result, expected_result)

    @parameterized.named_parameters(
        (
            "double_kick_fixed_2_hits",
            PokemonState(species="Hitmonlee", level=100, current_hp=300, max_hp=300),
            PokemonState(species="Blissey", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Double Kick", current_pp=30, max_pp=48),
            MoveResult(
                min_damage=372,
                max_damage=438,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=558,
                crit_max_damage=656,
                hit_count=2,
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "bullet_seed_variable_hits",
            PokemonState(species="Breloom", level=100, current_hp=300, max_hp=300),
            PokemonState(species="Blastoise", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Bullet Seed", current_pp=30, max_pp=48),
            MoveResult(
                min_damage=210,
                max_damage=251,
                knockout_probability=0.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=319,
                crit_max_damage=375,
                hit_count="2-5",
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "bullet_seed_with_technician",
            PokemonState(
                species="Breloom",
                level=100,
                current_hp=300,
                max_hp=300,
                ability="Technician",
            ),
            PokemonState(species="Blastoise", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Bullet Seed", current_pp=30, max_pp=48),
            MoveResult(
                min_damage=306,
                max_damage=362,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=461,
                crit_max_damage=542,
                hit_count="2-5",
                status_effects={},
                additional_effects=[],
            ),
        ),
        (
            "rock_blast_variable_hits",
            PokemonState(species="Rhyperior", level=100, current_hp=300, max_hp=300),
            PokemonState(species="Charizard", level=100, current_hp=300, max_hp=300),
            PokemonMove(name="Rock Blast", current_pp=10, max_pp=16),
            MoveResult(
                min_damage=520,
                max_damage=613,
                knockout_probability=1.0,
                critical_hit_probability=1 / 24,
                crit_min_damage=781,
                crit_max_damage=920,
                hit_count="2-5",
                status_effects={},
                additional_effects=[],
            ),
        ),
    )
    def test_multihit_moves(
        self,
        attacker: PokemonState,
        defender: PokemonState,
        move: PokemonMove,
        expected_result: MoveResult,
    ) -> None:
        result = self.simulator.estimate_move_result(attacker, defender, move)

        self.assertEqual(result, expected_result)


if __name__ == "__main__":
    absltest.main()
