"""Team state representation for battle simulation."""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from python.game.schema.enums import SideCondition
from python.game.schema.pokemon_state import PokemonState


@dataclass(frozen=True)
class TeamState:
    """Immutable state of a team (one player's side) during battle.

    This includes all 6 Pokemon, the active Pokemon, and side conditions
    like Reflect, Light Screen, Stealth Rock, etc.
    """

    pokemon: List[PokemonState] = field(default_factory=list)

    active_pokemon_index: Optional[int] = None

    side_conditions: Dict[SideCondition, int] = field(default_factory=dict)

    player_id: str = ""

    def get_pokemon_team(self) -> List[PokemonState]:
        """Get all Pokemon with their current statuses.

        Returns:
            List of all 6 Pokemon with complete state information
        """
        return list(self.pokemon)

    def get_active_pokemon(self) -> Optional[PokemonState]:
        """Get the currently active Pokemon.

        Returns:
            Active Pokemon if one is set, None otherwise
        """
        if self.active_pokemon_index is None:
            return None
        if 0 <= self.active_pokemon_index < len(self.pokemon):
            return self.pokemon[self.active_pokemon_index]
        raise ValueError(f"Active pokemon index {self.active_pokemon_index} is out of bounds")

    def get_side_conditions(self) -> Dict[SideCondition, int]:
        """Get all active side conditions.

        Returns:
            Dictionary mapping side conditions to their layer count or turns remaining
        """
        return dict(self.side_conditions)

    def get_alive_pokemon(self) -> List[PokemonState]:
        """Get all Pokemon that are not fainted.

        Returns:
            List of Pokemon with HP > 0
        """
        return [p for p in self.pokemon if p.is_alive()]

    def get_fainted_pokemon(self) -> List[PokemonState]:
        """Get all fainted Pokemon.

        Returns:
            List of Pokemon with HP = 0
        """
        return [p for p in self.pokemon if not p.is_alive()]

    def has_side_condition(self, condition: SideCondition) -> bool:
        """Check if a side condition is active.

        Args:
            condition: The side condition to check

        Returns:
            True if the condition is active
        """
        return condition in self.side_conditions

    def get_side_condition_value(self, condition: SideCondition) -> int:
        """Get the value for a side condition (layers or turns remaining).

        Args:
            condition: The side condition to check

        Returns:
            Number of layers or turns, or 0 if not active
        """
        return self.side_conditions.get(condition, 0)

    def to_dict(self) -> Dict[str, Any]:
        """Convert Team state to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the team state
        """
        return {
            "player_id": self.player_id,
            "active_pokemon_index": self.active_pokemon_index,
            "pokemon": [p.to_dict() for p in self.pokemon],
            "side_conditions": {
                cond.value: value for cond, value in self.side_conditions.items()
            },
            "fainted_count": len(self.get_fainted_pokemon()),
        }

    def __str__(self) -> str:
        """Return JSON representation of Team state.

        Returns:
            JSON string of team state, useful for testing and LLM integration
        """
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)
