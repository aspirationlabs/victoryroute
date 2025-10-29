"""Tests for JSON extraction logic inside JsonLlmAgent."""

from typing import Any, Dict, cast
import unittest

from python.agents.turn_predictor.json_llm_agent import JsonLlmAgent


class TestJsonExtraction(unittest.TestCase):
    def _extract_dict(self, text: str) -> Dict[str, Any]:
        result = JsonLlmAgent._extract_json_from_text(text)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        return cast(Dict[str, Any], result)

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
        result = self._extract_dict(json_text)
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
        result = self._extract_dict(markdown_text)
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
        result = self._extract_dict(markdown_text)
        self.assertEqual(result["species"], "Landorus-Therian")

    def test_extract_json_embedded_in_text(self):
        """Test extracting JSON embedded in explanatory text."""
        text_with_json = """
        The opponent's active Pokemon is Kingambit. Looking at the moves used,
        it seems to be a standard offensive set. Here's my prediction:
        {"species": "Kingambit", "moves": [{"name": "Sucker Punch", "confidence": 1.0}, {"name": "Kowtow Cleave", "confidence": 0.9}, {"name": "Iron Head", "confidence": 0.8}, {"name": "Swords Dance", "confidence": 0.7}], "item": "Leftovers", "ability": "Supreme Overlord", "tera_type": "Dark"}
        This is a very common set in the current meta.
        """
        result = self._extract_dict(text_with_json)
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
        result = self._extract_dict(json_text)
        self.assertEqual(len(result["moves"]), 4)
        self.assertEqual(result["moves"][0]["name"], "Dragon Darts")
        self.assertEqual(result["moves"][0]["confidence"], 0.95)

    def test_extract_none_for_invalid_json(self):
        """Test that invalid JSON returns None."""
        invalid_text = "This is just plain text without any JSON."
        result = JsonLlmAgent._extract_json_from_text(invalid_text)
        self.assertIsNone(result)

    def test_extract_none_for_incomplete_json(self):
        """Test that incomplete JSON returns None."""
        incomplete_json = """
        {
          "species": "Iron Crown",
          "moves": [
            {"name": "Tachyon Cutter", "confidence": 1.0}
        """
        result = JsonLlmAgent._extract_json_from_text(incomplete_json)
        self.assertIsNone(result)

    def test_extract_json_handles_empty_string(self):
        """Test that empty string returns None."""
        result = JsonLlmAgent._extract_json_from_text("")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
