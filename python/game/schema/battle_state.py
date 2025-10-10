"""Battle state representation for battle simulation."""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from python.game.schema.enums import Stat
from python.game.schema.field_state import FieldState
from python.game.schema.pokemon_state import PokemonState
from python.game.schema.team_state import TeamState
from python.game.schema.utils import normalize_move_name


@dataclass(frozen=True)
class BattleState:
    """Immutable state of an entire battle.

    This is the complete snapshot of a battle, including both teams and field state.
    """

    teams: Dict[str, TeamState] = field(
        default_factory=lambda: {"p1": TeamState(), "p2": TeamState()}
    )

    field_state: FieldState = field(default_factory=FieldState)

    battle_format: str = "singles"
    ruleset: Optional[str] = None

    available_moves: List[str] = field(default_factory=list)
    available_switches: List[int] = field(default_factory=list)
    can_mega: bool = False
    can_tera: bool = False
    can_dynamax: bool = False
    force_switch: bool = False
    team_preview: bool = False
    waiting: bool = (
        False  # True when we received a "wait" request (opponent is choosing)
    )

    battle_over: bool = False
    winner: Optional[str] = None
    player_usernames: Dict[str, str] = field(default_factory=dict)
    our_player_id: Optional[str] = (
        None  # "p1" or "p2" - learned from first RequestEvent
    )

    def get_team(self, player: str) -> TeamState:
        """Get team state for a player.

        Args:
            player: Player ID ("p1" or "p2")

        Returns:
            TeamState for the specified player
        """
        if player not in self.teams:
            raise ValueError(f"Invalid player ID: {player}")
        return self.teams[player]

    def get_active_pokemon(self, player: str) -> Optional[PokemonState]:
        """Get active Pokemon for a player.

        Args:
            player: Player ID ("p1" or "p2")

        Returns:
            Active Pokemon for the player, or None if no active Pokemon
        """
        team = self.get_team(player)
        return team.get_active_pokemon()

    def _infer_available_moves(self, player: str) -> List[str]:
        """Infer available moves from battle state (for replay mode).

        Args:
            player: Player ID (p1 or p2)

        Returns:
            List of move names with PP > 0, accounting for Encore and Disable
        """
        # Team preview: no moves available yet (choosing team order)
        if self.team_preview:
            return []

        # Force switch (from pivot moves or faints): no moves, only switches available
        if self.force_switch:
            return []

        active = self.get_active_pokemon(player)
        if not active or not active.is_alive():
            return []

        # For opponent Pokemon, if they have revealed moves (learned via MoveEvent),
        # return empty list to match server behavior. The server doesn't re-send
        # move lists once moves are revealed through battle actions.
        # Only apply this logic if we know our player ID and this is the opponent
        if self.our_player_id is not None and player != self.our_player_id and active.moves:
            return []

        # Check for Encore - only the encored move is available
        if "encore" in active.volatile_conditions:
            encore_data = active.volatile_conditions["encore"]
            # Handle both {'move': 'MoveName'} and 'MoveName' formats
            encored_move = (
                encore_data.get("move")
                if isinstance(encore_data, dict)
                else encore_data
            )
            for move in active.moves:
                if move.name == encored_move and move.current_pp > 0:
                    return [move.name]
            return []

        # Check for Choice item locking - if Pokemon has Choice item and used a move,
        # only that move is available (others will have 0 PP or be tracked as locked)
        choice_items = ["choicescarf", "choicespecs", "choiceband"]
        pokemon_item = active.item.lower() if active.item else ""
        has_choice_item = pokemon_item in choice_items

        if has_choice_item and "choice_locked_move" in active.volatile_conditions:
            locked_move = active.volatile_conditions["choice_locked_move"]
            for move in active.moves:
                if move.name == locked_move and move.current_pp > 0:
                    return [move.name]
            return []

        # Check for Disable - exclude the disabled move
        disabled_move = None
        if "disable" in active.volatile_conditions:
            disable_data = active.volatile_conditions["disable"]
            disabled_move = (
                disable_data.get("move")
                if isinstance(disable_data, dict)
                else disable_data
            )

        # Check for Gigaton Hammer restriction - cannot use twice in a row
        # Track the last move used to detect this restriction
        last_move_used = active.volatile_conditions.get("last_move_used")
        gigaton_hammer_disabled = (
            last_move_used and
            normalize_move_name(last_move_used) == "gigatonhammer"
        )

        available = []
        for move in active.moves:
            # Skip moves with no PP
            if move.current_pp <= 0:
                continue

            # Skip disabled move
            if disabled_move and move.name == disabled_move:
                continue

            # Skip Gigaton Hammer if it was just used
            if gigaton_hammer_disabled and normalize_move_name(move.name) == "gigatonhammer":
                continue

            available.append(move.name)

        return available

    def _infer_available_switches(self, player: str) -> List[int]:
        """Infer available switches from battle state (for replay mode).

        Args:
            player: Player ID (p1 or p2)

        Returns:
            List of indices of Pokemon that can be switched in
        """
        # Team preview: no switches available (choosing team order, not switching)
        if self.team_preview:
            return []

        team = self.get_team(player)
        active_index = team.active_pokemon_index

        available = []
        for i, pokemon in enumerate(team.get_pokemon_team()):
            # Can switch if: alive, not active, not trapped
            # Skip the active Pokemon (use index instead of species/nickname matching)
            # Note: active_index might be None if no Pokemon has switched in yet
            if active_index is not None and i == active_index:
                continue

            # Must be alive and not trapped
            if pokemon.is_alive() and pokemon.can_switch():
                available.append(i)

        return available

    def get_available_moves(self, player: Optional[str] = None) -> List[str]:
        """Get available moves for a player.

        If request data is available (from RequestEvent), returns that.
        Otherwise, infers from battle state (replay mode).

        Args:
            player: Player ID (p1 or p2). If None, uses our_player_id.

        Returns:
            List of available move names

        Raises:
            ValueError: If player is None and our_player_id is not set
        """
        if player is None:
            if self.our_player_id is None:
                raise ValueError(
                    "player parameter is required when our_player_id is not set"
                )
            player = self.our_player_id

        if player == self.our_player_id and self.available_moves:
            return self.available_moves

        return self._infer_available_moves(player)

    def get_available_switches(self, player: Optional[str] = None) -> List[int]:
        """Get available switches for a player.

        If request data is available (from RequestEvent), returns that.
        Otherwise, infers from battle state (replay mode).

        Args:
            player: Player ID (p1 or p2). If None, uses our_player_id.

        Returns:
            List of indices of Pokemon that can be switched in

        Raises:
            ValueError: If player is None and our_player_id is not set
        """
        if player is None:
            if self.our_player_id is None:
                raise ValueError(
                    "player parameter is required when our_player_id is not set"
                )
            player = self.our_player_id

        if player == self.our_player_id and self.available_switches:
            return self.available_switches

        return self._infer_available_switches(player)

    def get_move_index(self, move_name: str, player: Optional[str] = None) -> int:
        """Get the index of a move in the active Pokemon's moveset.

        Args:
            move_name: Name of the move to find
            player: Player ID ("p1" or "p2"). If None, uses our_player_id.

        Returns:
            Index of the move (0-3)

        Raises:
            ValueError: If the move is not found in the Pokemon's moveset
            ValueError: If player is None and our_player_id is not set
        """
        if player is None:
            if self.our_player_id is None:
                raise ValueError(
                    "player parameter is required when our_player_id is not set"
                )
            player = self.our_player_id

        active_pokemon = self.get_active_pokemon(player)
        if not active_pokemon:
            raise ValueError(f"No active Pokemon for player {player}")

        # Normalize move name for comparison
        normalized_search = normalize_move_name(move_name)

        for i, move in enumerate(active_pokemon.moves):
            normalized_move = normalize_move_name(move.name)
            if normalized_move == normalized_search:
                return i

        raise ValueError(
            f"Move '{move_name}' not found in {active_pokemon.species}'s moveset"
        )

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
        result: Dict[str, Any] = {
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
        }

        # Add side conditions and teams for each player
        for player_id, team in self.teams.items():
            result[f"{player_id}_side_conditions"] = {
                cond.value: value for cond, value in team.side_conditions.items()
            }
            result[f"{player_id}_team"] = [p.to_dict() for p in team.get_pokemon_team()]

        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert Battle state to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the entire battle state
        """
        result = {
            "battle_format": self.battle_format,
            "ruleset": self.ruleset,
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

        for player_id, team in self.teams.items():
            result[f"{player_id}_team"] = team.to_dict()

        return result

    def __str__(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)
