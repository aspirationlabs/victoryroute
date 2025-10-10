"""Unit tests for LlmEventLogger."""

import json
import os
import tempfile
import shutil
import unittest
from typing import Any, Dict

from python.agents.tools.llm_event_logger import LlmEventLogger


class LlmEventLoggerTest(unittest.TestCase):
    """Test cases for LlmEventLogger."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.llm_events_dir = os.path.join(self.test_dir, "llm_events")
        self.battle_turns_dir = os.path.join(self.test_dir, "battle_turns")
        self.system_instructions_dir = os.path.join(
            self.test_dir, "system_instructions"
        )
        self.user_queries_dir = os.path.join(self.test_dir, "user_queries")

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_init_creates_directories(self) -> None:
        """Test that __init__ creates the required directories."""
        logger = LlmEventLogger(
            player_name="test_player",
            model_name="test/model-name",
            battle_room="battle-test-123",
            llm_events_dir=self.llm_events_dir,
            battle_turns_dir=self.battle_turns_dir,
            system_instructions_dir=self.system_instructions_dir,
            user_queries_dir=self.user_queries_dir,
        )

        self.assertTrue(os.path.exists(self.llm_events_dir))
        self.assertTrue(os.path.exists(self.battle_turns_dir))
        self.assertTrue(os.path.exists(self.system_instructions_dir))
        self.assertTrue(os.path.exists(self.user_queries_dir))

        logger.close()

    def test_log_event_writes_to_file(self) -> None:
        """Test that log_event writes events to the correct file."""
        logger = LlmEventLogger(
            player_name="test_player",
            model_name="test/model-name",
            battle_room="battle-test-456",
            llm_events_dir=self.llm_events_dir,
            battle_turns_dir=self.battle_turns_dir,
            system_instructions_dir=self.system_instructions_dir,
            user_queries_dir=self.user_queries_dir,
        )

        event_info: Dict[str, Any] = {
            "event_number": 1,
            "retry_attempt": 0,
            "id": "event_123",
            "event": "test event data",
            "latency_seconds": 0.123,
        }

        logger.log_event(turn_number=5, event_info=event_info)
        logger.close()

        expected_path = os.path.join(
            self.llm_events_dir, "test_player_model-name_battle-test-456_llmevents.txt"
        )
        self.assertTrue(os.path.exists(expected_path))

        with open(expected_path, "r") as f:
            content = f.read()
            lines = content.strip().split("\n")
            self.assertEqual(len(lines), 1)

            log_entry = json.loads(lines[0])
            self.assertEqual(log_entry["turn_number"], 5)
            self.assertEqual(log_entry["event"]["event_number"], 1)
            self.assertEqual(log_entry["event"]["id"], "event_123")

    def test_log_turn_summary_writes_to_file(self) -> None:
        """Test that log_turn_summary writes summaries to the correct file."""
        logger = LlmEventLogger(
            player_name="test_player",
            model_name="test/model-name",
            battle_room="battle-test-789",
            llm_events_dir=self.llm_events_dir,
            battle_turns_dir=self.battle_turns_dir,
            system_instructions_dir=self.system_instructions_dir,
            user_queries_dir=self.user_queries_dir,
        )

        summary_info: Dict[str, Any] = {
            "summary": "turn_complete",
            "turn": 3,
            "total_latency_seconds": 1.234,
            "total_prompt_tokens": 100,
            "total_completion_tokens": 50,
            "total_tokens": 150,
            "retry_attempts": 0,
            "success": True,
        }

        logger.log_turn_summary(turn_number=3, summary_info=summary_info)
        logger.close()

        expected_path = os.path.join(
            self.battle_turns_dir, "test_player_model-name_battle-test-789_turns.txt"
        )
        self.assertTrue(os.path.exists(expected_path))

        with open(expected_path, "r") as f:
            content = f.read()
            lines = content.strip().split("\n")
            self.assertEqual(len(lines), 1)

            log_entry = json.loads(lines[0])
            self.assertEqual(log_entry["turn"], 3)
            self.assertEqual(log_entry["total_tokens"], 150)
            self.assertEqual(log_entry["success"], True)

    def test_multiple_events_same_turn(self) -> None:
        """Test logging multiple events in the same turn."""
        logger = LlmEventLogger(
            player_name="test_player",
            model_name="test/model-name",
            battle_room="battle-test-multi",
            llm_events_dir=self.llm_events_dir,
            battle_turns_dir=self.battle_turns_dir,
            system_instructions_dir=self.system_instructions_dir,
            user_queries_dir=self.user_queries_dir,
        )

        for i in range(3):
            event_info: Dict[str, Any] = {
                "event_number": i + 1,
                "retry_attempt": 0,
                "id": f"event_{i}",
                "event": f"test event {i}",
            }
            logger.log_event(turn_number=1, event_info=event_info)

        logger.close()

        expected_path = os.path.join(
            self.llm_events_dir,
            "test_player_model-name_battle-test-multi_llmevents.txt",
        )
        with open(expected_path, "r") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 3)

            for i, line in enumerate(lines):
                log_entry = json.loads(line)
                self.assertEqual(log_entry["turn_number"], 1)
                self.assertEqual(log_entry["event"]["event_number"], i + 1)

    def test_context_manager(self) -> None:
        """Test that LlmEventLogger works as a context manager."""
        with LlmEventLogger(
            player_name="test_player",
            model_name="test/model-name",
            battle_room="battle-test-context",
            llm_events_dir=self.llm_events_dir,
            battle_turns_dir=self.battle_turns_dir,
            system_instructions_dir=self.system_instructions_dir,
            user_queries_dir=self.user_queries_dir,
        ) as logger:
            event_info: Dict[str, Any] = {"event_number": 1, "id": "test"}
            logger.log_event(turn_number=1, event_info=event_info)

        expected_path = os.path.join(
            self.llm_events_dir,
            "test_player_model-name_battle-test-context_llmevents.txt",
        )
        self.assertTrue(os.path.exists(expected_path))

        with open(expected_path, "r") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 1)

    def test_close_is_idempotent(self) -> None:
        """Test that calling close() multiple times is safe."""
        logger = LlmEventLogger(
            player_name="test_player",
            model_name="test/model-name",
            battle_room="battle-test-close",
            llm_events_dir=self.llm_events_dir,
            battle_turns_dir=self.battle_turns_dir,
            system_instructions_dir=self.system_instructions_dir,
            user_queries_dir=self.user_queries_dir,
        )

        logger.close()
        logger.close()
        logger.close()

    def test_log_after_close_does_nothing(self) -> None:
        """Test that logging after close does not raise an error."""
        logger = LlmEventLogger(
            player_name="test_player",
            model_name="test/model-name",
            battle_room="battle-test-after-close",
            llm_events_dir=self.llm_events_dir,
            battle_turns_dir=self.battle_turns_dir,
            system_instructions_dir=self.system_instructions_dir,
            user_queries_dir=self.user_queries_dir,
        )

        logger.close()

        event_info: Dict[str, Any] = {"event_number": 1}
        logger.log_event(turn_number=1, event_info=event_info)

        summary_info: Dict[str, Any] = {"summary": "test"}
        logger.log_turn_summary(turn_number=1, summary_info=summary_info)

        logger.log_system_instruction(turn_number=0, instruction="test instruction")
        logger.log_user_query(turn_number=1, query="test query", retry_attempt=0)

    def test_log_system_instruction_writes_to_file(self) -> None:
        """Test that log_system_instruction writes to the correct file."""
        logger = LlmEventLogger(
            player_name="test_player",
            model_name="test/model-name",
            battle_room="battle-test-sys-instr",
            llm_events_dir=self.llm_events_dir,
            battle_turns_dir=self.battle_turns_dir,
            system_instructions_dir=self.system_instructions_dir,
            user_queries_dir=self.user_queries_dir,
        )

        instruction = "You are a Pokemon battle agent. Use the tools available to you."
        logger.log_system_instruction(turn_number=0, instruction=instruction)
        logger.close()

        expected_path = os.path.join(
            self.system_instructions_dir,
            "test_player_model-name_battle-test-sys-instr_system_instructions.txt",
        )
        self.assertTrue(os.path.exists(expected_path))

        with open(expected_path, "r") as f:
            content = f.read()
            lines = content.strip().split("\n")
            self.assertEqual(len(lines), 1)

            log_entry = json.loads(lines[0])
            self.assertEqual(log_entry["turn_number"], 0)
            self.assertEqual(log_entry["instruction"], instruction)

    def test_log_user_query_writes_to_file(self) -> None:
        """Test that log_user_query writes to the correct file."""
        logger = LlmEventLogger(
            player_name="test_player",
            model_name="test/model-name",
            battle_room="battle-test-user-query",
            llm_events_dir=self.llm_events_dir,
            battle_turns_dir=self.battle_turns_dir,
            system_instructions_dir=self.system_instructions_dir,
            user_queries_dir=self.user_queries_dir,
        )

        query1 = "=== Turn 1 - Choose Your Action ==="
        query2 = "RETRY 1/3 - Previous action INVALID"
        logger.log_user_query(turn_number=1, query=query1, retry_attempt=0)
        logger.log_user_query(turn_number=1, query=query2, retry_attempt=1)
        logger.close()

        expected_path = os.path.join(
            self.user_queries_dir,
            "test_player_model-name_battle-test-user-query_user_queries.txt",
        )
        self.assertTrue(os.path.exists(expected_path))

        with open(expected_path, "r") as f:
            content = f.read()
            lines = content.strip().split("\n")
            self.assertEqual(len(lines), 2)

            log_entry1 = json.loads(lines[0])
            self.assertEqual(log_entry1["turn_number"], 1)
            self.assertEqual(log_entry1["retry_attempt"], 0)
            self.assertEqual(log_entry1["query"], query1)

            log_entry2 = json.loads(lines[1])
            self.assertEqual(log_entry2["turn_number"], 1)
            self.assertEqual(log_entry2["retry_attempt"], 1)
            self.assertEqual(log_entry2["query"], query2)


if __name__ == "__main__":
    unittest.main()
