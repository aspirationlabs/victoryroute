"""Logs LLM agent events to file for debugging and analysis."""

import json
import os
from typing import Any, Dict, Optional, TextIO


class LlmEventLogger:
    """Logs LLM agent events to a file."""

    def __init__(
        self,
        player_name: str,
        model_name: str,
        battle_room: str,
        llm_events_dir: str = "/tmp/logs/llm_events",
        battle_turns_dir: str = "/tmp/logs/battle_turns",
        system_instructions_dir: str = "/tmp/logs/system_instructions",
        user_queries_dir: str = "/tmp/logs/user_queries",
    ) -> None:
        """Initialize the LLM event logger.

        Args:
            player_name: Name of the player
            model_name: Model name used by the agent
            battle_room: Battle room ID
            llm_events_dir: Directory for LLM event logs (default: /tmp/logs/llm_events)
            battle_turns_dir: Directory for turn summaries (default: /tmp/logs/battle_turns)
            system_instructions_dir: Directory for system instructions (default: /tmp/logs/system_instructions)
            user_queries_dir: Directory for user queries (default: /tmp/logs/user_queries)
        """
        self._player_name = player_name
        self._model_name = model_name
        self._battle_room = battle_room

        os.makedirs(llm_events_dir, exist_ok=True)
        os.makedirs(battle_turns_dir, exist_ok=True)
        os.makedirs(system_instructions_dir, exist_ok=True)
        os.makedirs(user_queries_dir, exist_ok=True)

        base_filename = (
            f"{self._player_name}_{self._model_name.split('/')[-1]}_{self._battle_room}"
        )

        filename = f"{base_filename}_llmevents.txt"
        filepath = os.path.join(llm_events_dir, filename)
        self._file: Optional[TextIO] = open(filepath, "w")

        filename = f"{base_filename}_turns.txt"
        filepath = os.path.join(battle_turns_dir, filename)
        self._turn_summary_file: Optional[TextIO] = open(filepath, "w")

        filename = f"{base_filename}_system_instructions.txt"
        filepath = os.path.join(system_instructions_dir, filename)
        self._system_instruction_file: Optional[TextIO] = open(filepath, "w")

        filename = f"{base_filename}_user_queries.txt"
        filepath = os.path.join(user_queries_dir, filename)
        self._user_query_file: Optional[TextIO] = open(filepath, "w")

    def _serialize_event(self, event: Any) -> Dict[str, Any]:
        """Serialize event object preserving nested structures.

        Args:
            event: Event object from the LLM runner

        Returns:
            Dictionary with serialized event data
        """
        serialized: Dict[str, Any] = {
            "id": getattr(event, "id", None),
            "timestamp": getattr(event, "timestamp", None),
        }

        if hasattr(event, "content") and event.content:
            serialized["role"] = getattr(event.content, "role", None)
            if hasattr(event.content, "parts") and event.content.parts:
                serialized["parts"] = []
                for part in event.content.parts:
                    part_data: Dict[str, Any] = {}

                    if hasattr(part, "text") and part.text:
                        part_data["text"] = part.text

                    if hasattr(part, "function_call") and part.function_call:
                        part_data["function_call"] = {
                            "name": part.function_call.name,
                            "id": part.function_call.id,
                            "args": dict(part.function_call.args),
                        }

                    if hasattr(part, "function_response") and part.function_response:
                        part_data["function_response"] = {
                            "name": part.function_response.name,
                            "id": part.function_response.id,
                            "response": dict(part.function_response.response),
                        }

                    serialized["parts"].append(part_data)

        if hasattr(event, "usage_metadata") and event.usage_metadata:
            serialized["usage_metadata"] = {
                "prompt_token_count": event.usage_metadata.prompt_token_count,
                "candidates_token_count": event.usage_metadata.candidates_token_count,
                "total_token_count": event.usage_metadata.total_token_count,
            }

        serialized["_raw_event_str"] = str(event)

        return serialized

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

    def log_turn_summary(self, turn_number: int, summary_info: Dict[str, Any]) -> None:
        """Log a turn summary.

        Args:
            turn_number: Current turn number in the battle
            summary_info: Dictionary containing turn summary information
        """
        if self._turn_summary_file is None:
            return

        self._turn_summary_file.write(f"{json.dumps(summary_info)}\n")
        self._turn_summary_file.flush()

    def log_system_instruction(self, turn_number: int, instruction: str) -> None:
        """Log system instruction.

        Args:
            turn_number: Turn number (typically 0 for initial instruction)
            instruction: System instruction text
        """
        if self._system_instruction_file is None:
            return

        log_entry = {"turn_number": turn_number, "instruction": instruction}
        self._system_instruction_file.write(f"{json.dumps(log_entry)}\n")
        self._system_instruction_file.flush()

    def log_user_query(
        self, turn_number: int, query: str, retry_attempt: int = 0
    ) -> None:
        """Log user query sent to the LLM.

        Args:
            turn_number: Current turn number in the battle
            query: User query text sent to the LLM
            retry_attempt: Retry attempt number (0 for initial query)
        """
        if self._user_query_file is None:
            return

        log_entry = {
            "turn_number": turn_number,
            "retry_attempt": retry_attempt,
            "query": query,
        }
        self._user_query_file.write(f"{json.dumps(log_entry)}\n")
        self._user_query_file.flush()

    def close(self) -> None:
        """Close all log files."""
        if self._file is not None:
            self._file.close()
            self._file = None
        if self._turn_summary_file is not None:
            self._turn_summary_file.close()
            self._turn_summary_file = None
        if self._system_instruction_file is not None:
            self._system_instruction_file.close()
            self._system_instruction_file = None
        if self._user_query_file is not None:
            self._user_query_file.close()
            self._user_query_file = None

    def __enter__(self) -> "LlmEventLogger":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
