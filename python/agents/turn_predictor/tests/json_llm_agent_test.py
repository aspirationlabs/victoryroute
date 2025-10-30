"""Tests for JsonLlmAgent utilities and prompt formatting."""

from typing import Any, Dict, cast
import unittest

from google.adk.agents import LlmAgent

from python.agents.battle_action_generator import BattleActionResponse
from python.agents.turn_predictor.json_llm_agent import JsonLlmAgent
from python.agents.turn_predictor.llm_model_factory import get_llm_model


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


class TestJsonLlmAgentPrompt(unittest.TestCase):
    def test_coercion_instruction_includes_placeholder_and_schema(self):
        base_agent = LlmAgent(
            model=get_llm_model("test-model"),
            name="base_agent",
            instruction="Base instruction.",
            output_key="battle_action_response_draft",
        )
        wrapper = JsonLlmAgent[BattleActionResponse](
            base_agent=base_agent,
            output_schema=BattleActionResponse,
            data_input_key="battle_action_response_draft",
            json_output_key="battle_action_response",
            model=get_llm_model("test-model"),
        )
        coercion_agent = cast(LlmAgent, wrapper.sub_agents[1])
        instruction = coercion_agent.instruction
        self.assertIsInstance(instruction, str)

        self.assertIn("# Draft", instruction)
        self.assertIn("{battle_action_response_draft}", instruction)
        self.assertIn("## Output Structure", instruction)
        self.assertIn("markdown sections with JSON keys in parentheses", instruction)
        self.assertIn("## Section Name (json_key)", instruction)
        expected_structure_lines = [
            "- action_type (str): Type of action: 'move', 'switch', or 'team_order'",
            "- move_name (Optional[str]): Name of the move to use (required for 'move' actions)",
            "- switch_pokemon_name (Optional[str]): Name of Pokemon to switch to (required for 'switch' actions)",
            "- team_order (Optional[str]): Team order as 6 digits, e.g. '123456' (required for 'team_order' actions)",
            "- mega (bool): Whether to Mega Evolve (only with 'move' actions)",
            "- tera (bool): Whether to Terastallize (only with 'move' actions)",
            "- reasoning (str): Explanation of why this action was chosen",
        ]
        for line in expected_structure_lines:
            self.assertIn(line, instruction)
        self.assertIn("## Example", instruction)

        formatted_instruction = instruction.format(
            battle_action_response_draft="test_output_value"
        )
        self.assertIn("test_output_value", formatted_instruction)
        expected_example = """```json
{
  "action_type": "",
  "move_name": null,
  "switch_pokemon_name": null,
  "team_order": null,
  "mega": false,
  "tera": false,
  "reasoning": ""
}
```"""
        self.assertIn(expected_example, formatted_instruction)


if __name__ == "__main__":
    unittest.main()
