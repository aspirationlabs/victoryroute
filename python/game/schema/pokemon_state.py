"""Pokemon state representation for battle simulation."""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from python.game.schema.enums import Stat, Status


# Stat stage multipliers for stages -6 to +6
STAT_STAGE_MULTIPLIERS = {
    -6: 2 / 8,
    -5: 2 / 7,
    -4: 2 / 6,
    -3: 2 / 5,
    -2: 2 / 4,
    -1: 2 / 3,
    0: 1.0,
    1: 3 / 2,
    2: 4 / 2,
    3: 5 / 2,
    4: 6 / 2,
    5: 7 / 2,
    6: 8 / 2,
}


@dataclass(frozen=True)
class PokemonMove:
    """Represents a move with its current PP."""

    name: str
    current_pp: int
    max_pp: int


@dataclass(frozen=True)
class PokemonState:
    """Immutable state of a single Pokemon during battle.

    This represents a complete snapshot of a Pokemon's state at a specific point
    in battle, including HP, stats, status conditions, and active effects.
    """

    species: str
    level: int = 100
    gender: Optional[str] = None
    shiny: bool = False
    nickname: Optional[str] = None

    current_hp: int = 100
    max_hp: int = 100
    status: Status = Status.NONE

    stat_boosts: Dict[Stat, int] = field(default_factory=dict)

    moves: List[PokemonMove] = field(default_factory=list)

    item: Optional[str] = None
    ability: str = ""
    tera_type: Optional[str] = None
    has_terastallized: bool = False

    volatile_conditions: Dict[str, Any] = field(default_factory=dict)

    is_active: bool = False

    active_effects: Dict[str, Any] = field(default_factory=dict)

    def is_alive(self) -> bool:
        """Check if Pokemon is not fainted.

        Returns:
            True if HP > 0, False otherwise
        """
        return self.current_hp > 0

    def can_switch(self) -> bool:
        """Check if Pokemon can switch out.

        Returns:
            True if alive and not trapped, False otherwise
        """
        if not self.is_alive():
            return False
        # Check for trapping conditions
        if self.volatile_conditions.get("trapped", False):
            return False
        return True

    def get_stat_boost(self, stat: Stat) -> int:
        """Get the current stat boost stage for a stat.

        Args:
            stat: The stat to check

        Returns:
            Integer from -6 to +6 representing the boost stage
        """
        return self.stat_boosts.get(stat, 0)

    def get_stat_multiplier(self, stat: Stat) -> float:
        """Get the multiplier for a stat based on its boost stage.

        Args:
            stat: The stat to check

        Returns:
            Float multiplier (0.25 to 4.0)

        Example:
            >>> pokemon.get_stat_multiplier(Stat.ATK)  # With +2 Atk
            2.0
        """
        stage = self.get_stat_boost(stat)
        return STAT_STAGE_MULTIPLIERS[stage]

    def get_effective_stat(
        self, stat: Stat, base_stat: int, nature_modifier: float = 1.0
    ) -> int:
        """Calculate the effective value of a stat with boosts applied.

        This applies stat stage multipliers to the base stat value.
        Does NOT include status effects like burn (handled elsewhere).

        Args:
            stat: The stat to calculate
            base_stat: The base stat value (from Pokemon data)
            nature_modifier: Nature modifier (0.9, 1.0, or 1.1)

        Returns:
            Effective stat value as integer

        Example:
            >>> # Landorus with base 145 Atk, -1 from Intimidate
            >>> pokemon.get_effective_stat(Stat.ATK, 145)
            96  # 145 * (2/3) = 96.67 -> 96
        """
        multiplier = self.get_stat_multiplier(stat)
        return int(base_stat * nature_modifier * multiplier)

    def get_all_stats(self, base_stats: Dict[Stat, int]) -> Dict[str, Any]:
        """Get all effective stats with modifiers applied.

        Args:
            base_stats: Dictionary of base stat values

        Returns:
            Dictionary containing:
            - hp: Current HP / Max HP
            - atk, def, spa, spd, spe: Effective stats with boosts
            - status: Current status condition
            - accuracy, evasion: Boost stages
            - Custom modifiers from active effects

        Example:
            >>> stats = pokemon.get_all_stats({Stat.ATK: 145, ...})
            >>> stats["atk"]
            96  # With -1 boost from Intimidate
            >>> stats["status"]
            "none"
        """
        result: Dict[str, Any] = {
            "hp": {"current": self.current_hp, "max": self.max_hp},
            "atk": self.get_effective_stat(Stat.ATK, base_stats.get(Stat.ATK, 100)),
            "def": self.get_effective_stat(Stat.DEF, base_stats.get(Stat.DEF, 100)),
            "spa": self.get_effective_stat(Stat.SPA, base_stats.get(Stat.SPA, 100)),
            "spd": self.get_effective_stat(Stat.SPD, base_stats.get(Stat.SPD, 100)),
            "spe": self.get_effective_stat(Stat.SPE, base_stats.get(Stat.SPE, 100)),
            "status": self.status.value,
            "accuracy_stage": self.get_stat_boost(Stat.ACCURACY),
            "evasion_stage": self.get_stat_boost(Stat.EVASION),
        }

        if "substitute_hp" in self.volatile_conditions:
            result["substitute_hp"] = self.volatile_conditions["substitute_hp"]
        if "protect_count" in self.volatile_conditions:
            result["protect_count"] = self.volatile_conditions["protect_count"]

        # Add active effects
        for effect_name, effect_value in self.active_effects.items():
            result[effect_name] = effect_value

        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert Pokemon state to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the Pokemon state
        """
        return {
            "species": self.species,
            "level": self.level,
            "gender": self.gender,
            "shiny": self.shiny,
            "nickname": self.nickname,
            "hp": {"current": self.current_hp, "max": self.max_hp},
            "status": self.status.value,
            "stat_boosts": {
                stat.value: boost for stat, boost in self.stat_boosts.items()
            },
            "moves": [
                {
                    "name": move.name,
                    "current_pp": move.current_pp,
                    "max_pp": move.max_pp,
                }
                for move in self.moves
            ],
            "item": self.item,
            "ability": self.ability,
            "tera_type": self.tera_type,
            "has_terastallized": self.has_terastallized,
            "volatile_conditions": self.volatile_conditions,
            "is_active": self.is_active,
            "active_effects": self.active_effects,
        }

    def __str__(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)
