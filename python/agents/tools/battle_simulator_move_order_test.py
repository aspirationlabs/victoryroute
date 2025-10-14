from typing import List, Optional

from absl.testing import absltest, parameterized

from python.agents.tools.battle_simulator import BattleSimulator
from python.game.data.game_data import GameData
from python.game.schema.enums import SideCondition, Stat, Status, Terrain, Weather
from python.game.schema.pokemon_state import PokemonMove, PokemonState


class BattleSimulatorMoveOrderTest(parameterized.TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.game_data = GameData()
        self.simulator = BattleSimulator(self.game_data)

    @parameterized.named_parameters(
        (
            "quick_attack_vs_tackle",
            PokemonState(species="Pikachu", ability="Static"),
            PokemonMove(name="Quick Attack", current_pp=30, max_pp=30),
            PokemonState(species="Raichu", ability="Static"),
            PokemonMove(name="Tackle", current_pp=35, max_pp=35),
            ["Quick Attack", "Tackle"],
        ),
        (
            "extreme_speed_vs_quick_attack",
            PokemonState(species="Pikachu", ability="Static"),
            PokemonMove(name="Extreme Speed", current_pp=5, max_pp=5),
            PokemonState(species="Dragonite", ability="Multiscale"),
            PokemonMove(name="Quick Attack", current_pp=30, max_pp=30),
            ["Extreme Speed", "Quick Attack"],
        ),
        (
            "prankster_status_vs_normal",
            PokemonState(species="Whimsicott", ability="Prankster"),
            PokemonMove(name="Taunt", current_pp=20, max_pp=20),
            PokemonState(species="Tyranitar", ability="Sand Stream"),
            PokemonMove(name="Stone Edge", current_pp=8, max_pp=8),
            ["Taunt", "Stone Edge"],
        ),
        (
            "gale_wings_full_hp",
            PokemonState(
                species="Talonflame",
                ability="Gale Wings",
                current_hp=300,
                max_hp=300,
            ),
            PokemonMove(name="Brave Bird", current_pp=15, max_pp=15),
            PokemonState(species="Dragapult", ability="Infiltrator"),
            PokemonMove(name="Dragon Darts", current_pp=10, max_pp=10),
            ["Brave Bird", "Dragon Darts"],
        ),
        (
            "gale_wings_not_full_hp",
            PokemonState(
                species="Talonflame",
                ability="Gale Wings",
                current_hp=299,
                max_hp=300,
            ),
            PokemonMove(name="Brave Bird", current_pp=15, max_pp=15),
            PokemonState(species="Dragapult", ability="Infiltrator"),
            PokemonMove(name="Dragon Darts", current_pp=10, max_pp=10),
            ["Dragon Darts", "Brave Bird"],
        ),
        (
            "triage_healing_move",
            PokemonState(species="Comfey", ability="Triage"),
            PokemonMove(name="Draining Kiss", current_pp=10, max_pp=10),
            PokemonState(species="Garchomp", ability="Rough Skin"),
            PokemonMove(name="Extreme Speed", current_pp=5, max_pp=5),
            ["Draining Kiss", "Extreme Speed"],
        ),
    )
    def test_move_priority(
        self,
        pokemon_1: PokemonState,
        move_1: PokemonMove,
        pokemon_2: PokemonState,
        move_2: PokemonMove,
        expected_order_moves: List[str],
    ) -> None:
        result = self.simulator.get_move_order(pokemon_1, move_1, pokemon_2, move_2)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].move.name, expected_order_moves[0])
        self.assertEqual(result[1].move.name, expected_order_moves[1])

    @parameterized.named_parameters(
        (
            "faster_pokemon_first",
            PokemonState(species="Alakazam", ability="Magic Guard"),
            PokemonMove(name="Psychic", current_pp=10, max_pp=10),
            PokemonState(species="Snorlax", ability="Thick Fat"),
            PokemonMove(name="Body Slam", current_pp=15, max_pp=15),
            ["Alakazam", "Snorlax"],
        ),
        (
            "slower_pokemon_second",
            PokemonState(species="Snorlax", ability="Thick Fat"),
            PokemonMove(name="Body Slam", current_pp=15, max_pp=15),
            PokemonState(species="Alakazam", ability="Magic Guard"),
            PokemonMove(name="Psychic", current_pp=10, max_pp=10),
            ["Alakazam", "Snorlax"],
        ),
    )
    def test_base_speed_differences(
        self,
        pokemon_1: PokemonState,
        move_1: PokemonMove,
        pokemon_2: PokemonState,
        move_2: PokemonMove,
        expected_order_species: List[str],
    ) -> None:
        result = self.simulator.get_move_order(pokemon_1, move_1, pokemon_2, move_2)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].pokemon.species, expected_order_species[0])
        self.assertEqual(result[1].pokemon.species, expected_order_species[1])

    @parameterized.named_parameters(
        (
            "plus_2_speed_vs_neutral",
            PokemonState(
                species="Dragonite",
                ability="Multiscale",
                stat_boosts={Stat.SPE: 2},
            ),
            PokemonMove(name="Extreme Speed", current_pp=5, max_pp=5),
            PokemonState(species="Dragonite", ability="Multiscale"),
            PokemonMove(name="Extreme Speed", current_pp=5, max_pp=5),
            ["pokemon_1", "pokemon_2"],
        ),
        (
            "neutral_vs_minus_1_speed",
            PokemonState(species="Landorus-Therian", ability="Intimidate"),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=10),
            PokemonState(
                species="Landorus-Therian",
                ability="Intimidate",
                stat_boosts={Stat.SPE: -1},
            ),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=10),
            ["pokemon_1", "pokemon_2"],
        ),
    )
    def test_stat_boosts(
        self,
        pokemon_1: PokemonState,
        move_1: PokemonMove,
        pokemon_2: PokemonState,
        move_2: PokemonMove,
        expected_order: List[str],
    ) -> None:
        result = self.simulator.get_move_order(pokemon_1, move_1, pokemon_2, move_2)

        self.assertEqual(len(result), 2)
        first_pokemon_key = (
            "pokemon_1" if result[0].pokemon == pokemon_1 else "pokemon_2"
        )
        second_pokemon_key = (
            "pokemon_1" if result[1].pokemon == pokemon_1 else "pokemon_2"
        )
        self.assertEqual([first_pokemon_key, second_pokemon_key], expected_order)

    @parameterized.named_parameters(
        (
            "paralyzed_vs_normal",
            PokemonState(
                species="Zapdos",
                ability="Pressure",
                status=Status.PARALYSIS,
            ),
            PokemonMove(name="Thunder", current_pp=10, max_pp=10),
            PokemonState(species="Pikachu", ability="Static"),
            PokemonMove(name="Thunder", current_pp=10, max_pp=10),
            ["Pikachu", "Zapdos"],
        ),
        (
            "paralyzed_vs_paralyzed",
            PokemonState(
                species="Gardevoir",
                ability="Synchronize",
                status=Status.PARALYSIS,
            ),
            PokemonMove(name="Psychic", current_pp=10, max_pp=10),
            PokemonState(species="Dragapult", ability="Infiltrator"),
            PokemonMove(name="Thunder", current_pp=10, max_pp=10),
            ["Dragapult", "Gardevoir"],
        ),
    )
    def test_status_effects(
        self,
        pokemon_1: PokemonState,
        move_1: PokemonMove,
        pokemon_2: PokemonState,
        move_2: PokemonMove,
        expected_order_species: List[str],
    ) -> None:
        result = self.simulator.get_move_order(pokemon_1, move_1, pokemon_2, move_2)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].pokemon.species, expected_order_species[0])
        self.assertEqual(result[1].pokemon.species, expected_order_species[1])

    @parameterized.named_parameters(
        (
            "swift_swim_in_rain",
            PokemonState(species="Kingdra", ability="Swift Swim"),
            PokemonMove(name="Hydro Pump", current_pp=5, max_pp=5),
            PokemonState(species="Dragapult", ability="Infiltrator"),
            PokemonMove(name="Dragon Darts", current_pp=10, max_pp=10),
            Weather.RAIN,
            None,
            ["Kingdra", "Dragapult"],
        ),
        (
            "swift_swim_no_rain",
            PokemonState(species="Kingdra", ability="Swift Swim"),
            PokemonMove(name="Hydro Pump", current_pp=5, max_pp=5),
            PokemonState(species="Dragapult", ability="Infiltrator"),
            PokemonMove(name="Dragon Darts", current_pp=10, max_pp=10),
            Weather.NONE,
            None,
            ["Dragapult", "Kingdra"],
        ),
        (
            "chlorophyll_in_sun",
            PokemonState(species="Venusaur", ability="Chlorophyll"),
            PokemonMove(name="Solar Beam", current_pp=10, max_pp=10),
            PokemonState(species="Charizard", ability="Blaze"),
            PokemonMove(name="Fire Blast", current_pp=5, max_pp=5),
            Weather.SUN,
            None,
            ["Venusaur", "Charizard"],
        ),
        (
            "sand_rush_in_sandstorm",
            PokemonState(species="Excadrill", ability="Sand Rush"),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=10),
            PokemonState(species="Garchomp", ability="Rough Skin"),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=10),
            Weather.SANDSTORM,
            None,
            ["Excadrill", "Garchomp"],
        ),
        (
            "slush_rush_in_snow",
            PokemonState(species="Sandslash-Alola", ability="Slush Rush"),
            PokemonMove(name="Iron Head", current_pp=15, max_pp=15),
            PokemonState(species="Weavile", ability="Pressure"),
            PokemonMove(name="Ice Shard", current_pp=30, max_pp=30),
            Weather.SNOW,
            None,
            ["Weavile", "Sandslash-Alola"],
        ),
        (
            "surge_surfer_in_electric_terrain",
            PokemonState(species="Raichu-Alola", ability="Surge Surfer"),
            PokemonMove(name="Thunderbolt", current_pp=15, max_pp=15),
            PokemonState(species="Alakazam", ability="Magic Guard"),
            PokemonMove(name="Psychic", current_pp=10, max_pp=10),
            Weather.NONE,
            Terrain.ELECTRIC,
            ["Raichu-Alola", "Alakazam"],
        ),
    )
    def test_weather_and_terrain_abilities(
        self,
        pokemon_1: PokemonState,
        move_1: PokemonMove,
        pokemon_2: PokemonState,
        move_2: PokemonMove,
        weather: Weather,
        terrain: Optional[Terrain],
        expected_order_species: List[str],
    ) -> None:
        result = self.simulator.get_move_order(
            pokemon_1, move_1, pokemon_2, move_2, weather=weather, terrain=terrain
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].pokemon.species, expected_order_species[0])
        self.assertEqual(result[1].pokemon.species, expected_order_species[1])

    @parameterized.named_parameters(
        (
            "choice_scarf",
            PokemonState(
                species="Tyranitar", ability="Sand Stream", item="Choice Scarf"
            ),
            PokemonMove(name="Stone Edge", current_pp=8, max_pp=8),
            PokemonState(species="Garchomp", ability="Rough Skin"),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=10),
            ["Tyranitar", "Garchomp"],
        ),
        (
            "lagging_tail",
            PokemonState(
                species="Dragapult", ability="Infiltrator", item="Lagging Tail"
            ),
            PokemonMove(name="Dragon Darts", current_pp=10, max_pp=10),
            PokemonState(species="Snorlax", ability="Thick Fat"),
            PokemonMove(name="Body Slam", current_pp=15, max_pp=15),
            ["Snorlax", "Dragapult"],
        ),
        (
            "iron_ball",
            PokemonState(species="Dragapult", ability="Infiltrator", item="Iron Ball"),
            PokemonMove(name="Dragon Darts", current_pp=10, max_pp=10),
            PokemonState(species="Tyranitar", ability="Sand Stream"),
            PokemonMove(name="Stone Edge", current_pp=8, max_pp=8),
            ["Tyranitar", "Dragapult"],
        ),
    )
    def test_speed_items(
        self,
        pokemon_1: PokemonState,
        move_1: PokemonMove,
        pokemon_2: PokemonState,
        move_2: PokemonMove,
        expected_order_species: List[str],
    ) -> None:
        result = self.simulator.get_move_order(pokemon_1, move_1, pokemon_2, move_2)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].pokemon.species, expected_order_species[0])
        self.assertEqual(result[1].pokemon.species, expected_order_species[1])

    @parameterized.named_parameters(
        (
            "tailwind_side_1",
            PokemonState(species="Tyranitar", ability="Sand Stream"),
            PokemonMove(name="Stone Edge", current_pp=8, max_pp=8),
            PokemonState(species="Garchomp", ability="Rough Skin"),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=10),
            {SideCondition.TAILWIND},
            set(),
            ["Tyranitar", "Garchomp"],
        ),
        (
            "tailwind_side_2",
            PokemonState(species="Tyranitar", ability="Sand Stream"),
            PokemonMove(name="Stone Edge", current_pp=8, max_pp=8),
            PokemonState(species="Garchomp", ability="Rough Skin"),
            PokemonMove(name="Earthquake", current_pp=10, max_pp=10),
            set(),
            {SideCondition.TAILWIND},
            ["Garchomp", "Tyranitar"],
        ),
    )
    def test_side_conditions(
        self,
        pokemon_1: PokemonState,
        move_1: PokemonMove,
        pokemon_2: PokemonState,
        move_2: PokemonMove,
        side_1_conditions: set,
        side_2_conditions: set,
        expected_order_species: List[str],
    ) -> None:
        result = self.simulator.get_move_order(
            pokemon_1,
            move_1,
            pokemon_2,
            move_2,
            side_1_conditions=side_1_conditions,
            side_2_conditions=side_2_conditions,
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].pokemon.species, expected_order_species[0])
        self.assertEqual(result[1].pokemon.species, expected_order_species[1])

    @parameterized.named_parameters(
        (
            "trick_room",
            PokemonState(species="Snorlax", ability="Thick Fat"),
            PokemonMove(name="Body Slam", current_pp=15, max_pp=15),
            PokemonState(species="Alakazam", ability="Magic Guard"),
            PokemonMove(name="Psychic", current_pp=10, max_pp=10),
            ["Snorlax", "Alakazam"],
        ),
        (
            "trick_room_with_priority_moves",
            PokemonState(species="Alakazam", ability="Magic Guard"),
            PokemonMove(name="Psychic", current_pp=10, max_pp=10),
            PokemonState(species="Pikachu", ability="Static"),
            PokemonMove(name="Quick Attack", current_pp=10, max_pp=10),
            ["Pikachu", "Alakazam"],
        ),
    )
    def test_trick_room(self, pokemon_1: PokemonState, move_1: PokemonMove, pokemon_2: PokemonState, move_2: PokemonMove, expected_order_species: List[str]) -> None:
        result = self.simulator.get_move_order(
            pokemon_1, move_1, pokemon_2, move_2, trick_room_active=True
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].pokemon.species, expected_order_species[0])
        self.assertEqual(result[1].pokemon.species, expected_order_species[1])


if __name__ == "__main__":
    absltest.main()
