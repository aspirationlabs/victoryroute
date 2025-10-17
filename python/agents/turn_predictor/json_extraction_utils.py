"""Utility functions for extracting JSON from text outputs."""

import json
import re
from typing import Any, Dict, Optional


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extract and parse JSON from text that may contain additional content.

    This function handles various formats:
    - Pure JSON
    - JSON within markdown code blocks
    - JSON embedded in explanatory text

    Args:
        text: The text that may contain JSON

    Returns:
        Parsed JSON as a dictionary, or None if no valid JSON found
    """
    if not text:
        return None

    # First, try parsing as pure JSON
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code blocks
    markdown_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
    markdown_matches = re.findall(markdown_pattern, text, re.DOTALL)
    for match in markdown_matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue

    # Try to find JSON object in the text using braces
    # Look for the first { and find its matching }
    brace_stack = []
    start_idx: Optional[int] = None

    for i, char in enumerate(text):
        if char == "{":
            if start_idx is None:
                start_idx = i
            brace_stack.append(char)
        elif char == "}" and brace_stack:
            brace_stack.pop()
            if not brace_stack and start_idx is not None:
                # Found a complete JSON object
                json_str = text[start_idx : i + 1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # Reset and continue looking
                    start_idx = None

    # Try to find JSON array (less common but possible)
    bracket_stack = []
    start_idx: Optional[int] = None

    for i, char in enumerate(text):
        if char == "[":
            if start_idx is None:
                start_idx = i
            bracket_stack.append(char)
        elif char == "]" and bracket_stack:
            bracket_stack.pop()
            if not bracket_stack and start_idx is not None:
                # Found a complete JSON array
                json_str = text[start_idx : i + 1]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    # Reset and continue looking
                    start_idx = None

    return None


def validate_opponent_pokemon_prediction(data: Dict[str, Any]) -> bool:
    """Validate that the extracted JSON matches the OpponentPokemonPrediction schema.

    Args:
        data: Dictionary to validate

    Returns:
        True if valid, False otherwise
    """
    required_fields = {"species", "moves", "item", "ability", "tera_type"}

    # Check all required fields exist
    if not all(field in data for field in required_fields):
        return False

    # Validate moves structure
    if not isinstance(data["moves"], list):
        return False

    for move in data["moves"]:
        if not isinstance(move, dict):
            return False
        if "name" not in move or "confidence" not in move:
            return False
        if not isinstance(move["confidence"], (int, float)):
            return False
        if not 0 <= move["confidence"] <= 1:
            return False

    # Basic type checking for other fields
    string_fields = ["species", "item", "ability", "tera_type"]
    for field in string_fields:
        if not isinstance(data[field], str):
            return False

    return True
