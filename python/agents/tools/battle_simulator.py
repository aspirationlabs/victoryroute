"""Battle simulation tools for calculating Pokemon stats and simulating scenarios."""

from dataclasses import dataclass
from typing import Dict

from python.game.data.game_data import GameData
from python.game.schema.pokemon_state import PokemonState


@dataclass(frozen=True)
class IndividualValues:
    """Individual Values (IVs) for a Pokemon, ranging from 0-31."""

    hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    speed: int

    def __post_init__(self) -> None:
        for field_name in [
            "hp",
            "attack",
            "defense",
            "special_attack",
            "special_defense",
            "speed",
        ]:
            value = getattr(self, field_name)
            if not isinstance(value, int) or value < 0 or value > 31:
                raise ValueError(
                    f"{field_name} IV must be between 0 and 31, got {value}"
                )


@dataclass(frozen=True)
class EffortValues:
    """Effort Values (EVs) for a Pokemon, ranging from 0-252."""

    hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    speed: int

    def __post_init__(self) -> None:
        for field_name in [
            "hp",
            "attack",
            "defense",
            "special_attack",
            "special_defense",
            "speed",
        ]:
            value = getattr(self, field_name)
            if not isinstance(value, int) or value < 0 or value > 252:
                raise ValueError(
                    f"{field_name} EV must be between 0 and 252, got {value}"
                )


@dataclass(frozen=True)
class PokemonStats:
    """Calculated stats for a Pokemon."""

    hp: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    speed: int


class BattleSimulator:
    """Simulator for calculating Pokemon stats and battle scenarios."""

    def __init__(self, game_data: GameData) -> None:
        """Initialize the battle simulator.

        Args:
            game_data: GameData instance for looking up Pokemon, natures, etc.
        """
        self.game_data = game_data

    def get_nature_boosts(self, nature: str) -> Dict[str, float]:
        """Get nature stat multipliers.

        Args:
            nature: Name of the nature (e.g., "Jolly", "Bashful")

        Returns:
            Dictionary mapping stat names to their nature multipliers
            (1.1 for boosted stat, 0.9 for hindered stat, 1.0 otherwise)
        """
        nature_data = self.game_data.get_nature(nature)

        stat_name_map = {
            "atk": "attack",
            "def": "defense",
            "spa": "special_attack",
            "spd": "special_defense",
            "spe": "speed",
        }

        multipliers = {
            "hp": 1.0,
            "attack": 1.0,
            "defense": 1.0,
            "special_attack": 1.0,
            "special_defense": 1.0,
            "speed": 1.0,
        }

        if nature_data.plus_stat:
            full_stat_name = stat_name_map.get(
                nature_data.plus_stat, nature_data.plus_stat
            )
            multipliers[full_stat_name] = 1.1

        if nature_data.minus_stat:
            full_stat_name = stat_name_map.get(
                nature_data.minus_stat, nature_data.minus_stat
            )
            multipliers[full_stat_name] = 0.9

        return multipliers

    def get_pokemon_stats(
        self,
        pokemon: PokemonState,
        level: int = 100,
        ivs: IndividualValues = IndividualValues(31, 31, 31, 31, 31, 31),
        evs: EffortValues = EffortValues(252, 252, 252, 252, 252, 252),
        nature: str = "Bashful",
    ) -> PokemonStats:
        """Calculate the actual stats for a Pokemon given IVs, EVs, level, and nature.

        Uses the standard Pokemon stat calculation formula from Generation 3 onwards:
        - HP: floor(floor(2*base + IV + floor(EV/4) + 100) * level / 100 + 10)
        - Other: floor(floor(2*base + IV + floor(EV/4)) * level / 100 + 5) * nature_multiplier)

        Args:
            pokemon: The Pokemon state containing species information
            level: Pokemon level (default: 100)
            ivs: Individual Values (default: all 31s)
            evs: Effort Values (default: all 252s)
            nature: Nature name (default: "Bashful" - neutral nature)

        Returns:
            PokemonStats object with calculated HP, Attack, Defense, Sp. Atk, Sp. Def, Speed
        """
        pokemon_data = self.game_data.get_pokemon(pokemon.species)
        base_stats = pokemon_data.base_stats
        nature_multipliers = self.get_nature_boosts(nature)

        hp = int(
            int(2 * base_stats["hp"] + ivs.hp + int(evs.hp / 4) + 100) * level / 100
            + 10
        )

        attack = int(
            int(
                int(2 * base_stats["atk"] + ivs.attack + int(evs.attack / 4))
                * level
                / 100
                + 5
            )
            * nature_multipliers["attack"]
        )

        defense = int(
            int(
                int(2 * base_stats["def"] + ivs.defense + int(evs.defense / 4))
                * level
                / 100
                + 5
            )
            * nature_multipliers["defense"]
        )

        special_attack = int(
            int(
                int(
                    2 * base_stats["spa"]
                    + ivs.special_attack
                    + int(evs.special_attack / 4)
                )
                * level
                / 100
                + 5
            )
            * nature_multipliers["special_attack"]
        )

        special_defense = int(
            int(
                int(
                    2 * base_stats["spd"]
                    + ivs.special_defense
                    + int(evs.special_defense / 4)
                )
                * level
                / 100
                + 5
            )
            * nature_multipliers["special_defense"]
        )

        speed = int(
            int(
                int(2 * base_stats["spe"] + ivs.speed + int(evs.speed / 4))
                * level
                / 100
                + 5
            )
            * nature_multipliers["speed"]
        )

        return PokemonStats(
            hp=hp,
            attack=attack,
            defense=defense,
            special_attack=special_attack,
            special_defense=special_defense,
            speed=speed,
        )
