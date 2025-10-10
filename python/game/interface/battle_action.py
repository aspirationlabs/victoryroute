"""Battle action representation for agent decisions."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from python.game.schema.utils import normalize_move_name


class ActionType(Enum):
    """Type of action an agent can take."""

    MOVE = "move"
    SWITCH = "switch"
    TEAM_ORDER = "team_order"
    UNKNOWN_MOVE = "unknown_move"
    UNKNOWN_SWITCH = "unknown_switch"


@dataclass(frozen=True)
class BattleAction:
    """Immutable representation of an agent's battle decision.

    This class represents a single action that an agent can take during a battle.
    Actions are created by agents based on the available options in the BattleState,
    and are then converted to Showdown protocol commands for execution.

    Agents should pick from state.available_moves and state.available_switches,
    so no validation is performed here - the agent is responsible for choosing
    valid actions.

    Special action types UNKNOWN_MOVE and UNKNOWN_SWITCH are used as placeholders
    when inferring opponent potential actions but the full moveset or team is not
    yet revealed. These cannot be converted to Showdown commands.

    Attributes:
        action_type: Type of action (MOVE, SWITCH, TEAM_ORDER, UNKNOWN_MOVE, UNKNOWN_SWITCH)
        move_name: Name of the move to use, required for MOVE actions
        switch_pokemon_name: Name of Pokemon to switch to, required for SWITCH actions
        target_index: Target position for doubles battles (0-3), optional
        mega: Whether to Mega Evolve with this move (MOVE only)
        tera: Whether to Terastallize with this move (MOVE only)

    Examples:
        Basic move action:
        >>> action = BattleAction(action_type=ActionType.MOVE, move_name="earthquake")
        >>> action.to_showdown_command()
        '/choose move earthquake'

        Move with Mega Evolution:
        >>> action = BattleAction(action_type=ActionType.MOVE, move_name="thunderbolt", mega=True)
        >>> action.to_showdown_command()
        '/choose move thunderbolt mega'

        Switch action:
        >>> action = BattleAction(action_type=ActionType.SWITCH, switch_pokemon_name="pikachu")
        >>> action.to_showdown_command()
        '/choose switch pikachu'

        Targeted move in doubles (opponent):
        >>> action = BattleAction(action_type=ActionType.MOVE, move_name="surf", target_index=0)
        >>> action.to_showdown_command()
        '/choose move surf +1'

        Targeted move in doubles (ally support):
        >>> action = BattleAction(action_type=ActionType.MOVE, move_name="helpinghand", target_index=2)
        >>> action.to_showdown_command()
        '/choose move helpinghand -1'
    """

    action_type: ActionType
    move_name: Optional[str] = None
    switch_pokemon_name: Optional[str] = None
    target_index: Optional[int] = (
        None  # For doubles: 0-1 = opponents (+1,+2), 2-3 = allies (-1,-2)
    )
    mega: bool = False
    tera: bool = False
    team_order: Optional[str] = None  # For team preview: "123456" format

    def to_showdown_command(self) -> str:
        """Convert this action to a Showdown protocol command.

        Uses explicit move and Pokemon names in the Showdown protocol commands.
        Handles move actions (with optional mega/tera/target) and switch actions.

        Returns:
            A string command ready to send to the Showdown server.

        Raises:
            ValueError: If the action is invalid (e.g., MOVE without move_name,
                       SWITCH without switch_pokemon_name)

        Examples:
            >>> BattleAction(ActionType.MOVE, move_name="earthquake").to_showdown_command()
            '/choose move earthquake'
            >>> BattleAction(ActionType.MOVE, move_name="flamethrower", mega=True).to_showdown_command()
            '/choose move flamethrower mega'
            >>> BattleAction(ActionType.SWITCH, switch_pokemon_name="pikachu").to_showdown_command()
            '/choose switch pikachu'
        """
        if self.action_type == ActionType.MOVE:
            if self.move_name is None:
                raise ValueError("MOVE action requires move_name")

            # Normalize move name for Showdown protocol (lowercase, no spaces/hyphens)
            normalized_move = normalize_move_name(self.move_name)
            command = f"/choose move {normalized_move}"

            # Add target index if specified (doubles)
            # Protocol uses +/- prefix: +1,+2 for opponents, -1,-2 for allies
            # target_index mapping: 0->+1, 1->+2, 2->-1, 3->-2
            if self.target_index is not None:
                if self.target_index <= 1:
                    # Opponent targeting (most common)
                    target_spec = f"+{self.target_index + 1}"
                else:
                    # Ally targeting (for support moves)
                    target_spec = f"-{self.target_index - 1}"
                command = f"{command} {target_spec}"

            # Add mega/tera flags
            # Protocol: "mega" for Mega Evolution, "max" for Dynamax, "terastallize" for Terastallization
            if self.mega:
                command = f"{command} mega"
            if self.tera:
                command = f"{command} terastallize"

            return command

        elif self.action_type == ActionType.SWITCH:
            if self.switch_pokemon_name is None:
                raise ValueError("SWITCH action requires switch_pokemon_name")

            # Normalize Pokemon name for Showdown protocol (lowercase, no spaces/hyphens)
            normalized_pokemon = normalize_move_name(self.switch_pokemon_name)
            return f"/choose switch {normalized_pokemon}"

        elif self.action_type == ActionType.TEAM_ORDER:
            if self.team_order is None:
                raise ValueError("TEAM_ORDER action requires team_order")

            return f"/choose team {self.team_order}"

        elif self.action_type in (ActionType.UNKNOWN_MOVE, ActionType.UNKNOWN_SWITCH):
            raise ValueError(
                f"Cannot convert {self.action_type.value} to Showdown command. "
                "Unknown actions are placeholders for opponent move inference only."
            )

        else:
            raise ValueError(f"Unknown action type: {self.action_type}")
