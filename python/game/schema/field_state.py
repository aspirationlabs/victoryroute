"""Field state representation for battle simulation."""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from python.game.schema.enums import FieldEffect, Terrain, Weather


@dataclass(frozen=True)
class FieldState:
    """Immutable state of global field conditions during battle.

    This includes weather, terrain, and field-wide effects like Trick Room.
    """

    # Weather
    weather: Optional[Weather] = None
    weather_turns_remaining: int = 0

    # Terrain
    terrain: Optional[Terrain] = None
    terrain_turns_remaining: int = 0

    # Field effects (Trick Room, Gravity, etc.)
    field_effects: List[FieldEffect] = field(default_factory=list)
    field_effect_turns_remaining: Dict[FieldEffect, int] = field(default_factory=dict)

    # Current turn number
    turn_number: int = 0

    def get_weather(self) -> Optional[Weather]:
        """Get the current weather condition.

        Returns:
            Current weather, or None if no weather is active
        """
        if self.weather == Weather.NONE:
            return None
        return self.weather

    def get_terrain(self) -> Optional[Terrain]:
        """Get the current terrain condition.

        Returns:
            Current terrain, or None if no terrain is active
        """
        if self.terrain == Terrain.NONE:
            return None
        return self.terrain

    def get_field_effects(self) -> List[FieldEffect]:
        """Get all active field effects.

        Returns:
            List of active field effects
        """
        return list(self.field_effects)

    def has_field_effect(self, effect: FieldEffect) -> bool:
        """Check if a specific field effect is active.

        Args:
            effect: The field effect to check

        Returns:
            True if the effect is active
        """
        return effect in self.field_effects

    def get_field_effect_turns_remaining(self, effect: FieldEffect) -> int:
        """Get turns remaining for a field effect.

        Args:
            effect: The field effect to check

        Returns:
            Turns remaining, or 0 if not active
        """
        return self.field_effect_turns_remaining.get(effect, 0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert Field state to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the field state
        """
        return {
            "turn_number": self.turn_number,
            "weather": self.weather.value if self.weather else None,
            "weather_turns_remaining": self.weather_turns_remaining,
            "terrain": self.terrain.value if self.terrain else None,
            "terrain_turns_remaining": self.terrain_turns_remaining,
            "field_effects": [effect.value for effect in self.field_effects],
            "field_effect_turns": {
                effect.value: turns
                for effect, turns in self.field_effect_turns_remaining.items()
            },
        }

    def __str__(self) -> str:
        """Return JSON representation of Field state.

        Returns:
            JSON string of field state, useful for testing and LLM integration
        """
        return json.dumps(self.to_dict(), sort_keys=True)
