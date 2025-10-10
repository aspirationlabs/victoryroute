"""Logs LLM agent events to file for debugging and analysis."""

import json
import os
from typing import Any, Dict, Optional, TextIO


class LlmEventLogger:
    """Logs LLM agent events to a file."""

    def __init__(self, player_name: str, model_name: str, battle_room: str) -> None:
        """Initialize the LLM event logger.

        Args:
            player_name: Name of the player
            battle_room: Battle room ID
        """
        self._player_name = player_name
        self._model_name = model_name
        self._battle_room = battle_room
        self._file: Optional[TextIO] = None
        self._log_dir = "/tmp/logs"

        os.makedirs(self._log_dir, exist_ok=True)
        filename = f"{self._player_name}_{self._model_name.split('/')[-1]}_{self._battle_room}_llmevents.txt"
        filepath = os.path.join(self._log_dir, filename)
        self._file = open(filepath, "w")

    def log_event(self, turn_number: int, event_info: Dict[str, Any]) -> None:
        """Log an LLM event.

        Args:
            turn_number: Current turn number in the battle
            event_info: Dictionary containing event information (id, content, actions,
                       usage_metadata, etc.)
        """
        if self._file is None:
            return

        log_entry = {"turn_number": turn_number, "event": event_info}
        self._file.write(f"{json.dumps(log_entry)}\n")
        self._file.flush()

    def close(self) -> None:
        """Close the log file."""
        if self._file is not None:
            self._file.close()
            self._file = None
