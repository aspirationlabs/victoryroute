"""Logs battle events to file for debugging and analysis."""

import os
from typing import Optional, TextIO

from python.game.events.battle_event import BattleEvent


class BattleEventLogger:
    """Logs battle stream events to a file."""

    def __init__(
        self, player_name: str, epoch_secs: int, battle_room: str, opponent_name: str
    ) -> None:
        """Initialize the event logger.

        Args:
            player_name: Name of the player being used
            epoch_secs: Timestamp in epoch seconds for the log filename
            battle_room: Battle room ID
        """
        self._player_name = player_name
        self._epoch_secs = epoch_secs
        self._opponent_name = opponent_name
        self._file: Optional[TextIO] = None
        self._log_dir = "/tmp/logs"
        self._battle_room = battle_room

        os.makedirs(self._log_dir, exist_ok=True)
        filename = f"{self._player_name}_{self._opponent_name}_{self._battle_room}_{self._epoch_secs}.txt"
        filepath = os.path.join(self._log_dir, filename)
        self._file = open(filepath, "w")

    def log_event(self, event: BattleEvent) -> None:
        """Log a battle event.

        Args:
            event: BattleEvent to log
        """
        if self._file is None:
            return

        raw_message = getattr(event, "raw_message", str(event))
        self._file.write(f"{raw_message}\n")
        self._file.flush()

    def close(self) -> None:
        """Close the log file."""
        if self._file is not None:
            self._file.close()
            self._file = None
