"""Store for retrieving past battle events and actions."""

from typing import Dict, List

from python.game.events.battle_event import (
    BattleEvent,
    FaintEvent,
    MoveEvent,
    SwitchEvent,
    TurnEvent,
)
from python.game.interface.battle_action import ActionType, BattleAction
from python.game.schema.utils import normalize_move_name


class BattleStreamStore:
    """Store for accessing past battle events and extracting player actions.

    This class parses a list of battle events and provides methods to:
    1. Retrieve events grouped by turn
    2. Extract player actions (moves, switches) for each turn
    """

    def __init__(self, events: List[BattleEvent]) -> None:
        """Initialize the store with a list of battle events.

        Args:
            events: List of BattleEvent objects to process
        """
        self._events = events
        self._events_by_turn: Dict[int, List[BattleEvent]] = {}
        self._current_turn = 0
        self._process_events()

    def _process_events(self) -> None:
        """Process events and group them by turn number."""
        for event in self._events:
            if isinstance(event, TurnEvent):
                self._current_turn = event.turn_number
                if self._current_turn not in self._events_by_turn:
                    self._events_by_turn[self._current_turn] = []
            elif self._current_turn > 0:
                if self._current_turn not in self._events_by_turn:
                    self._events_by_turn[self._current_turn] = []
                self._events_by_turn[self._current_turn].append(event)

    def get_past_events(self) -> Dict[int, List[BattleEvent]]:
        """Get all past events grouped by turn.

        Returns:
            Dictionary mapping turn_id to list of events that occurred in that turn
        """
        return self._events_by_turn.copy()

    def get_past_battle_actions(
        self, player_id: str, past_turns: int = 0
    ) -> Dict[int, List[BattleAction]]:
        """Get past battle actions for a specific player.

        Args:
            player_id: Player ID (e.g., 'p1' or 'p2')
            past_turns: Number of past turns to retrieve (0 = all turns)

        Returns:
            Dictionary mapping turn_id to list of BattleAction objects
        """
        actions_by_turn: Dict[int, List[BattleAction]] = {}

        if past_turns == 0:
            turn_ids = self._events_by_turn.keys()
        else:
            turn_ids = range(1, past_turns + 1)

        for turn_id in turn_ids:
            if turn_id not in self._events_by_turn:
                continue

            turn_events = self._events_by_turn[turn_id]
            actions = self._extract_player_actions(player_id, turn_events)
            actions_by_turn[turn_id] = actions

        return actions_by_turn

    def _extract_player_actions(
        self, player_id: str, events: List[BattleEvent]
    ) -> List[BattleAction]:
        """Extract all actions taken by a player during a turn.

        Args:
            player_id: Player ID (e.g., 'p1' or 'p2')
            events: List of events that occurred during the turn

        Returns:
            List of BattleAction objects representing player's actions
        """
        actions: List[BattleAction] = []
        fainted_positions: set[str] = set()
        last_move_name: str | None = None

        for i, event in enumerate(events):
            if isinstance(event, FaintEvent) and event.player_id == player_id:
                fainted_positions.add(event.position)

            elif isinstance(event, MoveEvent) and event.player_id == player_id:
                move_name = normalize_move_name(event.move_name)
                action = BattleAction(action_type=ActionType.MOVE, move_name=move_name)
                actions.append(action)
                last_move_name = move_name

            elif isinstance(event, SwitchEvent) and event.player_id == player_id:
                is_pivot_switch = self._is_switch_from_move(event, last_move_name)

                if self._is_forced_switch(
                    event, events, i, fainted_positions, is_pivot_switch
                ):
                    continue

                pokemon_name = normalize_move_name(event.species)
                action = BattleAction(
                    action_type=ActionType.SWITCH, switch_pokemon_name=pokemon_name
                )
                actions.append(action)

                if is_pivot_switch:
                    last_move_name = None

        return actions

    def _is_switch_from_move(
        self, switch_event: SwitchEvent, last_move_name: str | None
    ) -> bool:
        """Check if a switch is caused by a pivot move.

        Args:
            switch_event: The switch event to check
            last_move_name: The normalized name of the last move used by this player

        Returns:
            True if the switch was caused by a pivot move, False otherwise
        """
        if not last_move_name:
            return False

        if "[from]" not in switch_event.raw_message:
            return False

        parts = switch_event.raw_message.split("|")
        for part in parts:
            if part.startswith("[from]"):
                from_move = normalize_move_name(part[7:])
                return from_move == last_move_name

        return False

    def _is_forced_switch(
        self,
        switch_event: SwitchEvent,
        all_events: List[BattleEvent],
        current_index: int,
        fainted_positions: set[str],
        after_pivot: bool,
    ) -> bool:
        """Determine if a switch is forced (after faint) or voluntary.

        Args:
            switch_event: The switch event to check
            all_events: All events in the turn
            current_index: Index of the switch event in all_events
            fainted_positions: Set of positions that fainted this turn
            after_pivot: Whether this switch follows a pivot move

        Returns:
            True if the switch is forced, False if it's a player action
        """
        if switch_event.position in fainted_positions:
            return True

        if "[from]" in switch_event.raw_message:
            if after_pivot:
                return False
            return True

        for i in range(current_index - 1, -1, -1):
            event = all_events[i]
            if isinstance(event, FaintEvent):
                if event.player_id == switch_event.player_id:
                    return True
            elif isinstance(event, (MoveEvent, SwitchEvent)):
                if event.player_id == switch_event.player_id:
                    break

        return False
