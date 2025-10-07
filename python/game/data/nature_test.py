import unittest

from python.game.data.nature import Nature


class NatureTest(unittest.TestCase):
    def test_adamant_nature(self) -> None:
        nature = Nature(name="Adamant", plus_stat="atk", minus_stat="spa")
        self.assertEqual(nature.name, "Adamant")
        self.assertEqual(nature.plus_stat, "atk")
        self.assertEqual(nature.minus_stat, "spa")

    def test_modest_nature(self) -> None:
        nature = Nature(name="Modest", plus_stat="spa", minus_stat="atk")
        self.assertEqual(nature.name, "Modest")
        self.assertEqual(nature.plus_stat, "spa")
        self.assertEqual(nature.minus_stat, "atk")

    def test_timid_nature(self) -> None:
        nature = Nature(name="Timid", plus_stat="spe", minus_stat="atk")
        self.assertEqual(nature.name, "Timid")
        self.assertEqual(nature.plus_stat, "spe")
        self.assertEqual(nature.minus_stat, "atk")

    def test_jolly_nature(self) -> None:
        nature = Nature(name="Jolly", plus_stat="spe", minus_stat="spa")
        self.assertEqual(nature.name, "Jolly")
        self.assertEqual(nature.plus_stat, "spe")
        self.assertEqual(nature.minus_stat, "spa")

    def test_hardy_neutral_nature(self) -> None:
        nature = Nature(name="Hardy", plus_stat=None, minus_stat=None)
        self.assertEqual(nature.name, "Hardy")
        self.assertIsNone(nature.plus_stat)
        self.assertIsNone(nature.minus_stat)

    def test_nature_is_frozen(self) -> None:
        nature = Nature(name="Adamant", plus_stat="atk", minus_stat="spa")
        with self.assertRaises(Exception):
            nature.name = "Different"


if __name__ == "__main__":
    unittest.main()
