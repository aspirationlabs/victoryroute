"""Unit tests for battle simulator."""

from typing import Dict

from absl.testing import absltest, parameterized

from python.agents.tools.battle_simulator import (
    BattleSimulator,
    EffortValues,
    IndividualValues,
)
from python.game.data.game_data import GameData
from python.game.schema.pokemon_state import PokemonState


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


if __name__ == "__main__":
    absltest.main()
