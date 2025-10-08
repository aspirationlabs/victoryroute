"""Battle action representation for agent decisions."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ActionType(Enum):
    """Type of action an agent can take."""

    MOVE = "move"
    SWITCH = "switch"


@dataclass(frozen=True)
class BattleAction:
    """Immutable representation of an agent's battle decision.

    This class represents a single action that an agent can take during a battle.
    Actions are created by agents based on the available options in the BattleState,
    and are then converted to Showdown protocol commands for execution.

    Agents should pick from state.available_moves and state.available_switches,
    so no validation is performed here - the agent is responsible for choosing
    valid actions.

    Attributes:
        action_type: Type of action (MOVE or SWITCH)
        move_index: Which move to use (0-3), required for MOVE actions
        switch_index: Which Pokemon to switch to (0-5), required for SWITCH actions
        target_index: Target position for doubles battles (0-3), optional
        mega: Whether to Mega Evolve with this move (MOVE only)
        tera: Whether to Terastallize with this move (MOVE only)

    Examples:
        Basic move action:
        >>> action = BattleAction(action_type=ActionType.MOVE, move_index=0)
        >>> action.to_showdown_command()
        '/choose move 1'

        Move with Mega Evolution:
        >>> action = BattleAction(action_type=ActionType.MOVE, move_index=2, mega=True)
        >>> action.to_showdown_command()
        '/choose move 3 mega'

        Switch action:
        >>> action = BattleAction(action_type=ActionType.SWITCH, switch_index=3)
        >>> action.to_showdown_command()
        '/choose switch 4'

        Targeted move in doubles (opponent):
        >>> action = BattleAction(action_type=ActionType.MOVE, move_index=1, target_index=0)
        >>> action.to_showdown_command()
        '/choose move 2 +1'

        Targeted move in doubles (ally support):
        >>> action = BattleAction(action_type=ActionType.MOVE, move_index=1, target_index=2)
        >>> action.to_showdown_command()
        '/choose move 2 -1'
    """

    action_type: ActionType
    move_index: Optional[int] = None
    switch_index: Optional[int] = None
    target_index: Optional[int] = (
        None  # For doubles: 0-1 = opponents (+1,+2), 2-3 = allies (-1,-2)
    )
    mega: bool = False
    tera: bool = False

    def to_showdown_command(self) -> str:
        """Convert this action to a Showdown protocol command.

        Converts the 0-indexed internal representation to 1-indexed Showdown
        protocol commands. Handles move actions (with optional mega/tera/target)
        and switch actions.

        Returns:
            A string command ready to send to the Showdown server.

        Raises:
            ValueError: If the action is invalid (e.g., MOVE without move_index,
                       SWITCH without switch_index)

        Examples:
            >>> BattleAction(ActionType.MOVE, move_index=0).to_showdown_command()
            '/choose move 1'
            >>> BattleAction(ActionType.MOVE, move_index=2, mega=True).to_showdown_command()
            '/choose move 3 mega'
            >>> BattleAction(ActionType.SWITCH, switch_index=4).to_showdown_command()
            '/choose switch 5'
        """
        if self.action_type == ActionType.MOVE:
            if self.move_index is None:
                raise ValueError("MOVE action requires move_index")

            # Convert 0-indexed to 1-indexed
            move_num = self.move_index + 1
            command = f"/choose move {move_num}"

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
            # Protocol: "mega" for Mega Evolution, "max" for Dynamax
            # Using "tera" for Terastallize (follows same shortened pattern)
            if self.mega:
                command = f"{command} mega"
            if self.tera:
                command = f"{command} tera"

            return command

        elif self.action_type == ActionType.SWITCH:
            if self.switch_index is None:
                raise ValueError("SWITCH action requires switch_index")

            # Convert 0-indexed to 1-indexed
            switch_num = self.switch_index + 1
            return f"/choose switch {switch_num}"

        else:
            raise ValueError(f"Unknown action type: {self.action_type}")
