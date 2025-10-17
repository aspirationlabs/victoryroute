"""Tests for JSON extraction utilities."""

import unittest
from python.agents.turn_predictor.json_extraction_utils import (
    extract_json_from_text,
    validate_opponent_pokemon_prediction,
)


class TestJsonExtractionUtils(unittest.TestCase):
    def test_extract_pure_json(self):
        """Test extracting pure JSON string."""
        json_text = """
        {
          "species": "Iron Crown",
          "moves": [
            {"name": "Tachyon Cutter", "confidence": 1.0},
            {"name": "Future Sight", "confidence": 1.0},
            {"name": "Focus Blast", "confidence": 0.85},
            {"name": "Volt Switch", "confidence": 0.8}
          ],
          "item": "Assault Vest",
          "ability": "Quark Drive",
          "tera_type": "Fighting"
        }
        """
        result = extract_json_from_text(json_text)
        self.assertIsNotNone(result)
        self.assertEqual(result["species"], "Iron Crown")
        self.assertEqual(len(result["moves"]), 4)

    def test_extract_json_from_markdown(self):
        """Test extracting JSON from markdown code block."""
        markdown_text = """
        The opponent's active Pokemon is Iron Crown. Based on the analysis:

        ```json
        {
          "species": "Iron Crown",
          "moves": [
            {"name": "Tachyon Cutter", "confidence": 1.0},
            {"name": "Future Sight", "confidence": 1.0},
            {"name": "Focus Blast", "confidence": 0.85},
            {"name": "Volt Switch", "confidence": 0.8}
          ],
          "item": "Assault Vest",
          "ability": "Quark Drive",
          "tera_type": "Fighting"
        }
        ```

        This is based on usage stats.
        """
        result = extract_json_from_text(markdown_text)
        self.assertIsNotNone(result)
        self.assertEqual(result["species"], "Iron Crown")

    def test_extract_json_from_markdown_no_language_tag(self):
        """Test extracting JSON from markdown code block without language tag."""
        markdown_text = """
        Here's the prediction:

        ```
        {
          "species": "Landorus-Therian",
          "moves": [
            {"name": "Earthquake", "confidence": 0.95},
            {"name": "U-turn", "confidence": 0.9},
            {"name": "Stone Edge", "confidence": 0.7},
            {"name": "Stealth Rock", "confidence": 0.6}
          ],
          "item": "Rocky Helmet",
          "ability": "Intimidate",
          "tera_type": "Water"
        }
        ```
        """
        result = extract_json_from_text(markdown_text)
        self.assertIsNotNone(result)
        self.assertEqual(result["species"], "Landorus-Therian")

    def test_extract_json_embedded_in_text(self):
        """Test extracting JSON embedded in explanatory text."""
        text_with_json = """
        The opponent's active Pokemon is Kingambit. Looking at the moves used,
        it seems to be a standard offensive set. Here's my prediction:
        {"species": "Kingambit", "moves": [{"name": "Sucker Punch", "confidence": 1.0}, {"name": "Kowtow Cleave", "confidence": 0.9}, {"name": "Iron Head", "confidence": 0.8}, {"name": "Swords Dance", "confidence": 0.7}], "item": "Leftovers", "ability": "Supreme Overlord", "tera_type": "Dark"}
        This is a very common set in the current meta.
        """
        result = extract_json_from_text(text_with_json)
        self.assertIsNotNone(result)
        self.assertEqual(result["species"], "Kingambit")
        self.assertEqual(result["ability"], "Supreme Overlord")

    def test_extract_json_with_nested_objects(self):
        """Test extracting JSON with nested move objects."""
        json_text = """
        {
          "species": "Dragapult",
          "moves": [
            {"name": "Dragon Darts", "confidence": 0.95},
            {"name": "U-turn", "confidence": 0.85},
            {"name": "Will-O-Wisp", "confidence": 0.7},
            {"name": "Hex", "confidence": 0.6}
          ],
          "item": "Choice Band",
          "ability": "Infiltrator",
          "tera_type": "Ghost"
        }
        """
        result = extract_json_from_text(json_text)
        self.assertIsNotNone(result)
        self.assertEqual(len(result["moves"]), 4)
        self.assertEqual(result["moves"][0]["name"], "Dragon Darts")
        self.assertEqual(result["moves"][0]["confidence"], 0.95)

    def test_extract_none_for_invalid_json(self):
        """Test that invalid JSON returns None."""
        invalid_text = "This is just plain text without any JSON."
        result = extract_json_from_text(invalid_text)
        self.assertIsNone(result)

    def test_extract_none_for_incomplete_json(self):
        """Test that incomplete JSON returns None."""
        incomplete_json = """
        {
          "species": "Iron Crown",
          "moves": [
            {"name": "Tachyon Cutter", "confidence": 1.0}
        """
        result = extract_json_from_text(incomplete_json)
        self.assertIsNone(result)

    def test_validate_valid_prediction(self):
        """Test validation of a valid OpponentPokemonPrediction."""
        valid_data = {
            "species": "Iron Crown",
            "moves": [
                {"name": "Tachyon Cutter", "confidence": 1.0},
                {"name": "Future Sight", "confidence": 0.9},
                {"name": "Focus Blast", "confidence": 0.85},
                {"name": "Volt Switch", "confidence": 0.8},
            ],
            "item": "Assault Vest",
            "ability": "Quark Drive",
            "tera_type": "Fighting",
        }
        self.assertTrue(validate_opponent_pokemon_prediction(valid_data))

    def test_validate_missing_field(self):
        """Test validation fails when required field is missing."""
        missing_ability = {
            "species": "Iron Crown",
            "moves": [{"name": "Tachyon Cutter", "confidence": 1.0}],
            "item": "Assault Vest",
            # "ability": missing
            "tera_type": "Fighting",
        }
        self.assertFalse(validate_opponent_pokemon_prediction(missing_ability))

    def test_validate_invalid_move_structure(self):
        """Test validation fails with invalid move structure."""
        invalid_moves = {
            "species": "Iron Crown",
            "moves": [
                {"name": "Tachyon Cutter"},  # Missing confidence
                {"name": "Future Sight", "confidence": 0.9},
            ],
            "item": "Assault Vest",
            "ability": "Quark Drive",
            "tera_type": "Fighting",
        }
        self.assertFalse(validate_opponent_pokemon_prediction(invalid_moves))

    def test_validate_confidence_out_of_range(self):
        """Test validation fails when confidence is out of range."""
        invalid_confidence = {
            "species": "Iron Crown",
            "moves": [
                {"name": "Tachyon Cutter", "confidence": 1.5}  # > 1.0
            ],
            "item": "Assault Vest",
            "ability": "Quark Drive",
            "tera_type": "Fighting",
        }
        self.assertFalse(validate_opponent_pokemon_prediction(invalid_confidence))

    def test_validate_wrong_type_fields(self):
        """Test validation fails when fields have wrong types."""
        wrong_types = {
            "species": 123,  # Should be string
            "moves": [{"name": "Tachyon Cutter", "confidence": 1.0}],
            "item": "Assault Vest",
            "ability": "Quark Drive",
            "tera_type": "Fighting",
        }
        self.assertFalse(validate_opponent_pokemon_prediction(wrong_types))

    def test_extract_json_handles_empty_string(self):
        """Test that empty string returns None."""
        result = extract_json_from_text("")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
