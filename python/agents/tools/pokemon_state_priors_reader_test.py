import threading
import unittest

from absl.testing import parameterized

from python.agents.tools.pokemon_state_priors_reader import PokemonStatePriorsReader


class PokemonStatePriorsReaderTest(parameterized.TestCase):
    def setUp(self):  # type: ignore[override]
        super().setUp()
        self.reader = PokemonStatePriorsReader()

    def test_singleton_returns_same_instance(self) -> None:
        reader1 = PokemonStatePriorsReader()
        reader2 = PokemonStatePriorsReader()
        self.assertIs(reader1, reader2)

    def test_singleton_thread_safe(self) -> None:
        instances = []

        def create_instance() -> None:
            instances.append(PokemonStatePriorsReader())

        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        first_instance = instances[0]
        for instance in instances:
            self.assertIs(instance, first_instance)

    @parameterized.parameters(
        ("Kingambit", True, "Supreme Overlord", "Sucker Punch", 98.929),
        ("kingambit", True, "Supreme Overlord", "Sucker Punch", 98.929),
        ("KINGAMBIT", True, "Supreme Overlord", "Sucker Punch", 98.929),
        ("Great Tusk", True, "Protosynthesis", "Rapid Spin", 96.457),
        ("greattusk", True, "Protosynthesis", "Rapid Spin", 96.457),
        ("Gholdengo", True, "Good as Gold", "Shadow Ball", 85.28),
        ("Iron Valiant", True, "Quark Drive", "Moonblast", 79.946),
        ("Landorus-Therian", True, "Intimidate", "U-turn", 88.324),
        ("NonexistentPokemon", False, None, None, None),
    )
    def test_get_pokemon_state_priors(
        self,
        pokemon_name: str,
        should_exist: bool,
        expected_top_ability: str,
        expected_top_move: str,
        expected_move_percentage: float,
    ) -> None:
        priors = self.reader.get_pokemon_state_priors(pokemon_name)

        if should_exist:
            self.assertIsNotNone(priors)
            self.assertEqual(priors.abilities[0]["name"], expected_top_ability)
            self.assertEqual(priors.moves[0]["name"], expected_top_move)
            self.assertAlmostEqual(
                priors.moves[0]["percentage"], expected_move_percentage, places=3
            )
        else:
            self.assertIsNone(priors)

    def test_kingambit_has_expected_structure(self) -> None:
        priors = self.reader.get_pokemon_state_priors("Kingambit")
        self.assertIsNotNone(priors)
        assert priors is not None

        self.assertEqual(priors.abilities[0]["name"], "Supreme Overlord")
        self.assertAlmostEqual(priors.abilities[0]["percentage"], 95.982, places=3)

        self.assertEqual(priors.items[0]["name"], "Leftovers")
        self.assertAlmostEqual(priors.items[0]["percentage"], 42.929, places=3)

        self.assertEqual(priors.moves[0]["name"], "Sucker Punch")
        self.assertAlmostEqual(priors.moves[0]["percentage"], 98.929, places=3)

        self.assertEqual(priors.spreads[0]["nature"], "Adamant")
        self.assertEqual(priors.spreads[0]["stats"], [0, 252, 4, 0, 0, 252])
        self.assertAlmostEqual(priors.spreads[0]["percentage"], 19.339, places=3)

        self.assertEqual(priors.tera[0]["name"], "Ghost")
        self.assertAlmostEqual(priors.tera[0]["percentage"], 35.431, places=3)

        self.assertEqual(priors.teammates[0]["name"], "Great Tusk")
        self.assertAlmostEqual(priors.teammates[0]["percentage"], 33.92, places=3)

    def test_name_normalization_with_special_characters(self) -> None:
        priors_normal = self.reader.get_pokemon_state_priors("Landorus-Therian")
        priors_no_hyphen = self.reader.get_pokemon_state_priors("LandorusTherian")
        priors_lowercase = self.reader.get_pokemon_state_priors("landorustherian")

        self.assertEqual(priors_normal, priors_no_hyphen)
        self.assertEqual(priors_normal, priors_lowercase)

    def test_get_top_usage_spread_returns_best_spread(self) -> None:
        result = self.reader.get_top_usage_spread("Gholdengo")
        self.assertIsNotNone(result)
        nature, evs = result
        self.assertEqual(nature, "Timid")
        self.assertEqual(evs, (0, 0, 0, 252, 4, 252))

    def test_get_top_usage_spread_returns_none_for_missing_data(self) -> None:
        result = self.reader.get_top_usage_spread("NonexistentPokemon")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
