import json
import unittest
from pathlib import Path

from python.game.data.type_chart import TypeChart


class TypeChartTest(unittest.TestCase):
    def setUp(self) -> None:
        data_dir = Path("data/game")
        with open(data_dir / "type_chart.json", "r") as f:
            data = json.load(f)
        self.type_chart = TypeChart(effectiveness=data[0]["effectiveness"])

    def test_super_effective_types(self) -> None:
        self.assertEqual(self.type_chart.get_effectiveness("fire", "grass"), 2.0)
        self.assertEqual(self.type_chart.get_effectiveness("water", "fire"), 2.0)
        self.assertEqual(self.type_chart.get_effectiveness("grass", "water"), 2.0)
        self.assertEqual(self.type_chart.get_effectiveness("ghost", "ghost"), 2.0)

    def test_not_very_effective_types(self) -> None:
        self.assertEqual(self.type_chart.get_effectiveness("fire", "water"), 0.5)
        self.assertEqual(self.type_chart.get_effectiveness("fire", "fire"), 0.5)
        self.assertEqual(self.type_chart.get_effectiveness("water", "grass"), 0.5)

    def test_immune_types(self) -> None:
        self.assertEqual(self.type_chart.get_effectiveness("ghost", "normal"), 0.0)
        self.assertEqual(self.type_chart.get_effectiveness("normal", "ghost"), 0.0)
        self.assertEqual(self.type_chart.get_effectiveness("ground", "flying"), 0.0)
        self.assertEqual(self.type_chart.get_effectiveness("dragon", "fairy"), 0.0)

    def test_neutral_types(self) -> None:
        self.assertEqual(self.type_chart.get_effectiveness("normal", "normal"), 1.0)

    def test_case_insensitive(self) -> None:
        self.assertEqual(self.type_chart.get_effectiveness("FIRE", "grass"), 2.0)
        self.assertEqual(self.type_chart.get_effectiveness("fire", "GRASS"), 2.0)
        self.assertEqual(self.type_chart.get_effectiveness("grasS", "FIre"), 0.5)

    def test_unknown_attacking_type(self) -> None:
        with self.assertRaises(ValueError) as context:
            self.type_chart.get_effectiveness("unknown", "fire")
        self.assertIn("Unknown attacking type", str(context.exception))

    def test_unknown_defending_type(self) -> None:
        with self.assertRaises(ValueError) as context:
            self.type_chart.get_effectiveness("fire", "unknown")
        self.assertIn("Unknown defending type", str(context.exception))


if __name__ == "__main__":
    unittest.main()
