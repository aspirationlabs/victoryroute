"""Unit tests for FieldState."""

import json
import unittest

from python.game.schema.enums import FieldEffect, Terrain, Weather
from python.game.schema.field_state import FieldState


class FieldStateTest(unittest.IsolatedAsyncioTestCase):
    """Test FieldState functionality."""

    def test_weather_tracking_snow(self) -> None:
        """Test Snow weather tracking with turn counter."""
        field = FieldState(
            weather=Weather.SNOW,
            weather_turns_remaining=5,
            turn_number=16,
        )

        self.assertEqual(field.get_weather(), Weather.SNOW)
        self.assertEqual(field.weather_turns_remaining, 5)

    def test_weather_none(self) -> None:
        """Test no weather active."""
        field = FieldState(
            weather=Weather.NONE,
            turn_number=5,
        )

        self.assertIsNone(field.get_weather())

    def test_terrain_tracking(self) -> None:
        """Test terrain tracking with turn counters."""
        field = FieldState(
            terrain=Terrain.ELECTRIC,
            terrain_turns_remaining=4,
            turn_number=10,
        )

        self.assertEqual(field.get_terrain(), Terrain.ELECTRIC)
        self.assertEqual(field.terrain_turns_remaining, 4)

    def test_trick_room_field_effect(self) -> None:
        """Test Trick Room field effect."""
        field = FieldState(
            field_effects=[FieldEffect.TRICK_ROOM],
            field_effect_turns_remaining={FieldEffect.TRICK_ROOM: 4},
            turn_number=23,
        )

        self.assertTrue(field.has_field_effect(FieldEffect.TRICK_ROOM))
        self.assertEqual(
            field.get_field_effect_turns_remaining(FieldEffect.TRICK_ROOM), 4
        )

    def test_field_effect_expiration(self) -> None:
        """Test field effect expiration (turns remaining = 0)."""
        # Trick Room active
        field_active = FieldState(
            field_effects=[FieldEffect.TRICK_ROOM],
            field_effect_turns_remaining={FieldEffect.TRICK_ROOM: 1},
            turn_number=27,
        )

        self.assertTrue(field_active.has_field_effect(FieldEffect.TRICK_ROOM))

        # Trick Room expired
        field_expired = FieldState(
            field_effects=[],
            field_effect_turns_remaining={},
            turn_number=28,
        )

        self.assertFalse(field_expired.has_field_effect(FieldEffect.TRICK_ROOM))

    def test_multiple_field_effects(self) -> None:
        """Test multiple field effects active simultaneously."""
        field = FieldState(
            field_effects=[FieldEffect.TRICK_ROOM, FieldEffect.GRAVITY],
            field_effect_turns_remaining={
                FieldEffect.TRICK_ROOM: 3,
                FieldEffect.GRAVITY: 5,
            },
            turn_number=10,
        )

        effects = field.get_field_effects()
        self.assertEqual(len(effects), 2)
        self.assertIn(FieldEffect.TRICK_ROOM, effects)
        self.assertIn(FieldEffect.GRAVITY, effects)

    def test_weather_and_terrain_together(self) -> None:
        """Test weather and terrain active together."""
        field = FieldState(
            weather=Weather.RAIN,
            weather_turns_remaining=3,
            terrain=Terrain.GRASSY,
            terrain_turns_remaining=4,
            turn_number=12,
        )

        self.assertEqual(field.get_weather(), Weather.RAIN)
        self.assertEqual(field.get_terrain(), Terrain.GRASSY)

    def test_json_serialization(self) -> None:
        """Test JSON serialization via __str__."""
        field = FieldState(
            weather=Weather.SNOW,
            weather_turns_remaining=5,
            terrain=Terrain.PSYCHIC,
            terrain_turns_remaining=3,
            field_effects=[FieldEffect.TRICK_ROOM],
            field_effect_turns_remaining={FieldEffect.TRICK_ROOM: 4},
            turn_number=20,
        )

        json_str = str(field)
        parsed = json.loads(json_str)

        self.assertEqual(parsed["turn_number"], 20)
        self.assertEqual(parsed["weather"], "snow")
        self.assertEqual(parsed["weather_turns_remaining"], 5)
        self.assertEqual(parsed["terrain"], "psychicterrain")
        self.assertIn("trickroom", parsed["field_effects"])


if __name__ == "__main__":
    unittest.main()
