import unittest
from typing import List, Optional

from absl.testing import parameterized

from python.game.data.game_data import GameData


class GameDataTest(parameterized.TestCase):
    def setUp(self) -> None:
        self.game_data = GameData()

    @parameterized.parameters(
        ("Pikachu", 25, ["Electric"], 35),
        ("Dragonite", 149, ["Dragon", "Flying"], 91),
        ("Landorus-Therian", 645, ["Ground", "Flying"], 89),
        ("Iron Crown", 1023, ["Steel", "Psychic"], 90),
        ("Kingambit", 983, ["Dark", "Steel"], 100),
        ("Gholdengo", 1000, ["Steel", "Ghost"], 87),
        ("Rotom-Wash", 479, ["Electric", "Water"], 50),
        ("Kommo-o", 784, ["Dragon", "Fighting"], 75),
        ("Ogerpon-Wellspring", 1017, ["Grass", "Water"], 80),
        ("Raging Bolt", 1021, ["Electric", "Dragon"], 125),
        ("Iron Moth", 994, ["Fire", "Poison"], 80),
        ("Zamazenta", 889, ["Fighting"], 92),
        ("Enamorus", 905, ["Fairy", "Flying"], 74),
        ("Gliscor", 472, ["Ground", "Flying"], 75),
        ("Blissey", 242, ["Normal"], 255),
        ("Talonflame", 663, ["Fire", "Flying"], 78),
        ("Toxapex", 748, ["Poison", "Water"], 50),
        ("Dondozo", 977, ["Water"], 150),
        ("Jirachi", 385, ["Steel", "Psychic"], 100),
        ("Glimmora", 970, ["Rock", "Poison"], 83),
    )
    def test_get_pokemon(
        self, name: str, expected_num: int, expected_types: List[str], expected_hp: int
    ) -> None:
        pokemon = self.game_data.get_pokemon(name)
        self.assertIsNotNone(pokemon)
        self.assertEqual(pokemon.name, name)
        self.assertEqual(pokemon.num, expected_num)
        self.assertEqual(pokemon.types, expected_types)
        self.assertEqual(pokemon.base_stats["hp"], expected_hp)

    @parameterized.parameters(
        ("Thunderbolt", "Electric", 90, 100),
        ("Ice Spinner", "Ice", 80, 100),
        ("Dragon Dance", "Dragon", 0, None),
        ("Stealth Rock", "Rock", 0, None),
        ("Protect", "Normal", 0, None),
        ("Volt Switch", "Electric", 70, 100),
        ("Earthquake", "Ground", 100, 100),
        ("Body Press", "Fighting", 80, 100),
        ("Crunch", "Dark", 80, 100),
        ("Hydro Pump", "Water", 110, 80),
        ("Will-O-Wisp", "Fire", 0, 85),
        ("Shadow Ball", "Ghost", 80, 100),
        ("Ivy Cudgel", "Grass", 100, 100),
        ("Tachyon Cutter", "Steel", 50, None),
        ("Tera Blast", "Normal", 80, 100),
        ("Sucker Punch", "Dark", 70, 100),
        ("Moonblast", "Fairy", 95, 100),
        ("Psychic Noise", "Psychic", 75, 100),
        ("Iron Defense", "Steel", 0, None),
        ("Future Sight", "Psychic", 120, 100),
    )
    def test_get_move(
        self,
        name: str,
        expected_type: str,
        expected_base_power: int,
        expected_accuracy: Optional[int],
    ) -> None:
        move = self.game_data.get_move(name)
        self.assertIsNotNone(move)
        self.assertEqual(move.name, name)
        self.assertEqual(move.type, expected_type)
        self.assertEqual(move.base_power, expected_base_power)
        self.assertEqual(move.accuracy, expected_accuracy)

    @parameterized.parameters(
        (
            "Intimidate",
            "On switch-in, this Pokemon lowers the Attack of opponents by 1 stage.",
        ),
        (
            "Poison Heal",
            "This Pokemon is healed by 1/8 of its max HP each turn when poisoned; no HP loss.",
        ),
        (
            "Quark Drive",
            "Electric Terrain active or Booster Energy used: highest stat is 1.3x, or 1.5x if Speed.",
        ),
        (
            "Supreme Overlord",
            "This Pokemon's moves have 10% more power for each fainted ally, up to 5 allies.",
        ),
        (
            "Toxic Debris",
            "If this Pokemon is hit by a physical attack, Toxic Spikes are set on the opposing side.",
        ),
        (
            "Dauntless Shield",
            "On switch-in, this Pokemon's Defense is raised by 1 stage. Once per battle.",
        ),
        (
            "Protosynthesis",
            "Sunny Day active or Booster Energy used: highest stat is 1.3x, or 1.5x if Speed.",
        ),
        ("Good as Gold", "This Pokemon is immune to Status moves."),
        (
            "Orichalcum Pulse",
            "On switch-in, summons Sunny Day. During Sunny Day, Attack is 1.3333x.",
        ),
        (
            "Contrary",
            "If this Pokemon has a stat stage raised it is lowered instead, and vice versa.",
        ),
    )
    def test_get_ability(self, name: str, expected_description: str) -> None:
        ability = self.game_data.get_ability(name)
        self.assertIsNotNone(ability)
        self.assertEqual(ability.name, name)
        self.assertEqual(ability.description, expected_description)

    @parameterized.parameters(
        ("Leftovers",),
        ("Rocky Helmet",),
        ("Focus Sash",),
        ("Toxic Orb",),
        ("Booster Energy",),
        ("Choice Scarf",),
        ("Choice Band",),
        ("Life Orb",),
        ("Assault Vest",),
        ("Heavy-Duty Boots",),
    )
    def test_get_item(self, name: str) -> None:
        item = self.game_data.get_item(name)
        self.assertIsNotNone(item)
        self.assertEqual(item.name, name)

    @parameterized.parameters(
        ("Adamant", "atk", "spa"),
        ("Modest", "spa", "atk"),
        ("Timid", "spe", "atk"),
        ("Jolly", "spe", "spa"),
        ("Hardy", None, None),
        ("Bold", "def", "atk"),
        ("Impish", "def", "spa"),
        ("Calm", "spd", "atk"),
        ("Careful", "spd", "spa"),
        ("Brave", "atk", "spe"),
    )
    def test_get_nature(
        self,
        name: str,
        expected_plus_stat: Optional[str],
        expected_minus_stat: Optional[str],
    ) -> None:
        nature = self.game_data.get_nature(name)
        self.assertIsNotNone(nature)
        self.assertEqual(nature.name, name)
        self.assertEqual(nature.plus_stat, expected_plus_stat)
        self.assertEqual(nature.minus_stat, expected_minus_stat)

    def test_get_pokemon_case_insensitive(self) -> None:
        pikachu_lower = self.game_data.get_pokemon("pikachu")
        pikachu_upper = self.game_data.get_pokemon("PIKACHU")
        pikachu_mixed = self.game_data.get_pokemon("PiKaChU")
        self.assertEqual(pikachu_lower.name, pikachu_upper.name)
        self.assertEqual(pikachu_lower.name, pikachu_mixed.name)

    def test_get_move_case_insensitive(self) -> None:
        thunderbolt_lower = self.game_data.get_move("thunderbolt")
        thunderbolt_upper = self.game_data.get_move("THUNDERBOLT")
        thunderbolt_spaced = self.game_data.get_move("Thunder Bolt")
        self.assertEqual(thunderbolt_lower.name, thunderbolt_upper.name)
        self.assertEqual(thunderbolt_lower.name, thunderbolt_spaced.name)

    def test_get_pokemon_with_hyphen(self) -> None:
        landorus = self.game_data.get_pokemon("Landorus-Therian")
        landorus_no_hyphen = self.game_data.get_pokemon("LandorusTherian")
        self.assertEqual(landorus.name, landorus_no_hyphen.name)

    def test_get_pokemon_not_found(self) -> None:
        with self.assertRaises(ValueError) as context:
            self.game_data.get_pokemon("NonexistentPokemon")
        self.assertIn("not found", str(context.exception))

    def test_get_move_not_found(self) -> None:
        with self.assertRaises(ValueError) as context:
            self.game_data.get_move("NonexistentMove")
        self.assertIn("not found", str(context.exception))

    def test_get_type_chart(self) -> None:
        type_chart = self.game_data.get_type_chart()
        self.assertIsNotNone(type_chart)
        self.assertEqual(type_chart.get_effectiveness("fire", "grass"), 2.0)
        self.assertEqual(type_chart.get_effectiveness("water", "fire"), 2.0)

    def test_get_item_normalized_formats(self) -> None:
        """Test that items can be retrieved with or without spaces/hyphens."""
        # Heavy-Duty Boots
        item_spaced = self.game_data.get_item("Heavy-Duty Boots")
        item_no_space = self.game_data.get_item("heavydutyboots")
        item_mixed = self.game_data.get_item("HeavyDutyBoots")
        self.assertEqual(item_spaced.name, "Heavy-Duty Boots")
        self.assertEqual(item_no_space.name, "Heavy-Duty Boots")
        self.assertEqual(item_mixed.name, "Heavy-Duty Boots")

        # Choice Scarf
        item_spaced2 = self.game_data.get_item("Choice Scarf")
        item_no_space2 = self.game_data.get_item("choicescarf")
        self.assertEqual(item_spaced2.name, "Choice Scarf")
        self.assertEqual(item_no_space2.name, "Choice Scarf")

    def test_get_move_normalized_formats(self) -> None:
        """Test that moves can be retrieved with or without spaces/hyphens."""
        # Will-O-Wisp
        move_spaced = self.game_data.get_move("Will-O-Wisp")
        move_no_space = self.game_data.get_move("willowisp")
        move_mixed = self.game_data.get_move("WillOWisp")
        self.assertEqual(move_spaced.name, "Will-O-Wisp")
        self.assertEqual(move_no_space.name, "Will-O-Wisp")
        self.assertEqual(move_mixed.name, "Will-O-Wisp")

        # Ice Spinner
        move_spaced2 = self.game_data.get_move("Ice Spinner")
        move_no_space2 = self.game_data.get_move("icespinner")
        self.assertEqual(move_spaced2.name, "Ice Spinner")
        self.assertEqual(move_no_space2.name, "Ice Spinner")

    def test_get_ability_normalized_formats(self) -> None:
        """Test that abilities can be retrieved with or without spaces."""
        # Poison Heal
        ability_spaced = self.game_data.get_ability("Poison Heal")
        ability_no_space = self.game_data.get_ability("poisonheal")
        ability_mixed = self.game_data.get_ability("PoisonHeal")
        self.assertEqual(ability_spaced.name, "Poison Heal")
        self.assertEqual(ability_no_space.name, "Poison Heal")
        self.assertEqual(ability_mixed.name, "Poison Heal")

        # Supreme Overlord
        ability_spaced2 = self.game_data.get_ability("Supreme Overlord")
        ability_no_space2 = self.game_data.get_ability("supremeoverlord")
        self.assertEqual(ability_spaced2.name, "Supreme Overlord")
        self.assertEqual(ability_no_space2.name, "Supreme Overlord")


if __name__ == "__main__":
    unittest.main()
