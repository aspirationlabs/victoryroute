"""Battle state representation for battle simulation."""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from python.game.schema.enums import Stat
from python.game.schema.field_state import FieldState
from python.game.schema.pokemon_state import PokemonState
from python.game.schema.team_state import TeamState


@dataclass(frozen=True)
class BattleState:
    """Immutable state of an entire battle.

    This is the complete snapshot of a battle, including both teams and field state.
    """

    # Teams
    p1_team: TeamState = field(default_factory=TeamState)
    p2_team: TeamState = field(default_factory=TeamState)

    # Field
    field_state: FieldState = field(default_factory=FieldState)

    # Battle format/rules
    battle_format: str = "singles"
    ruleset: Optional[str] = None

    # Available actions (set by request events)
    available_moves: List[str] = field(default_factory=list)
    available_switches: List[int] = field(default_factory=list)
    can_mega: bool = False
    can_tera: bool = False
    can_dynamax: bool = False
    force_switch: bool = False

    def get_team(self, player: str) -> TeamState:
        """Get team state for a player.

        Args:
            player: Player ID ("p1" or "p2")

        Returns:
            TeamState for the specified player
        """
        if player == "p1":
            return self.p1_team
        elif player == "p2":
            return self.p2_team
        else:
            raise ValueError(f"Invalid player ID: {player}")

    def get_active_pokemon(self, player: str) -> Optional[PokemonState]:
        """Get active Pokemon for a player.

        Args:
            player: Player ID ("p1" or "p2")

        Returns:
            Active Pokemon for the player, or None if no active Pokemon
        """
        team = self.get_team(player)
        return team.get_active_pokemon()

    def get_available_moves(self, player: str = "p1") -> List[str]:
        """Get available moves for a player.

        If request data is available (from RequestEvent), returns that.
        Otherwise, infers from battle state (replay mode).

        Args:
            player: Player ID (p1 or p2)

        Returns:
            List of available move names
        """
        # If we have request data, use it
        if player == "p1" and self.available_moves:
            return self.available_moves

        # Otherwise, infer from state
        from python.game.environment.state_transition import StateTransition

        return StateTransition._infer_available_moves(self, player)

    def get_available_switches(self, player: str = "p1") -> List[int]:
        """Get available switches for a player.

        If request data is available (from RequestEvent), returns that.
        Otherwise, infers from battle state (replay mode).

        Args:
            player: Player ID (p1 or p2)

        Returns:
            List of indices of Pokemon that can be switched in
        """
        # If we have request data, use it
        if player == "p1" and self.available_switches:
            return self.available_switches

        # Otherwise, infer from state
        from python.game.environment.state_transition import StateTransition

        return StateTransition._infer_available_switches(self, player)

    def get_pokemon_battle_state(
        self, pokemon: PokemonState, base_stats: Optional[Dict[Stat, int]] = None
    ) -> Dict[str, Any]:
        """Get complete battle state for a specific Pokemon.

        This wraps the Pokemon's get_all_stats method to provide a complete
        view of the Pokemon's effective stats with all modifiers applied.

        Args:
            pokemon: The Pokemon to get state for
            base_stats: Optional base stats dictionary. If not provided,
                       uses default 100 for all stats.

        Returns:
            Dictionary containing:
            - hp: Current/max HP
            - atk, def, spa, spd, spe: Effective stats with boosts
            - status: Current status condition
            - accuracy_stage, evasion_stage: Stat boost stages
            - Any volatile conditions (substitute_hp, protect_count, etc.)
            - Any active effects (protosynthesis, quark_drive, etc.)

        Example:
            >>> state = battle.get_pokemon_battle_state(landorus, base_stats)
            >>> state["atk"]  # With -1 Intimidate
            96
            >>> state["status"]
            "none"
            >>> state.get("supreme_overlord_fallen")
            4
        """
        if base_stats is None:
            base_stats = {
                Stat.HP: 100,
                Stat.ATK: 100,
                Stat.DEF: 100,
                Stat.SPA: 100,
                Stat.SPD: 100,
                Stat.SPE: 100,
            }
        return pokemon.get_all_stats(base_stats)

    def get_field_info(self) -> Dict[str, Any]:
        """Get complete field information including both sides.

        Returns:
            Dictionary containing:
            - weather: Current weather condition
            - terrain: Current terrain condition
            - field_effects: List of active field effects
            - turn_number: Current turn
            - p1_side_conditions: Player 1's side conditions
            - p2_side_conditions: Player 2's side conditions
            - p1_team: List of all Player 1's Pokemon
            - p2_team: List of all Player 2's Pokemon

        Example:
            >>> info = battle.get_field_info()
            >>> info["weather"]
            "snow"
            >>> info["p1_side_conditions"]["stealth_rock"]
            1
            >>> len(info["p1_team"])
            6
        """
        return {
            "turn_number": self.field_state.turn_number,
            "weather": (
                self.field_state.weather.value if self.field_state.weather else None
            ),
            "weather_turns_remaining": self.field_state.weather_turns_remaining,
            "terrain": (
                self.field_state.terrain.value if self.field_state.terrain else None
            ),
            "terrain_turns_remaining": self.field_state.terrain_turns_remaining,
            "field_effects": [
                effect.value for effect in self.field_state.field_effects
            ],
            "p1_side_conditions": {
                cond.value: value
                for cond, value in self.p1_team.side_conditions.items()
            },
            "p2_side_conditions": {
                cond.value: value
                for cond, value in self.p2_team.side_conditions.items()
            },
            "p1_team": [p.to_dict() for p in self.p1_team.get_pokemon_team()],
            "p2_team": [p.to_dict() for p in self.p2_team.get_pokemon_team()],
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert Battle state to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the entire battle state
        """
        return {
            "battle_format": self.battle_format,
            "ruleset": self.ruleset,
            "p1_team": self.p1_team.to_dict(),
            "p2_team": self.p2_team.to_dict(),
            "field_state": self.field_state.to_dict(),
            "available_actions": {
                "moves": self.available_moves,
                "switches": self.available_switches,
                "can_mega": self.can_mega,
                "can_tera": self.can_tera,
                "can_dynamax": self.can_dynamax,
                "force_switch": self.force_switch,
            },
        }

    def __str__(self) -> str:
        """Return JSON representation of Battle state.

        Returns:
            JSON string of battle state, useful for testing and LLM integration
        """
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)
