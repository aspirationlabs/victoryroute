"""Unit tests for battle simulator."""

from typing import Dict, List

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


if __name__ == "__main__":
    absltest.main()
