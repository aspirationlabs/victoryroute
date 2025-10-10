"""Unit tests for BattleEventLogger."""

import json
import os
import tempfile
import unittest

from python.game.events.battle_event import BattleEvent
from python.game.protocol.battle_event_logger import BattleEventLogger


class MockBattleEvent(BattleEvent):
    """Mock BattleEvent for testing."""

    def __init__(self, raw_message: str) -> None:
        """Initialize mock battle event."""
        self.raw_message = raw_message

    @classmethod
    def parse_raw_message(cls, raw_message: str) -> "MockBattleEvent":
        """Parse raw message into MockBattleEvent."""
        return cls(raw_message)


class BattleEventLoggerTest(unittest.TestCase):
    """Test cases for BattleEventLogger."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        import shutil

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_init_creates_directory(self) -> None:
        """Test that __init__ creates the log directory."""
        logger = BattleEventLogger(
            player_name="test_player",
            epoch_secs=1234567890,
            battle_room="battle-test-123",
            opponent_name="opponent1",
            log_dir=self.test_dir,
        )

        self.assertTrue(os.path.exists(self.test_dir))
        logger.close()

    def test_log_event_writes_to_file(self) -> None:
        """Test that log_event writes events to the correct file."""
        epoch_secs = 1234567890
        logger = BattleEventLogger(
            player_name="test_player",
            epoch_secs=epoch_secs,
            battle_room="battle-test-456",
            opponent_name="opponent2",
            log_dir=self.test_dir,
        )

        event = MockBattleEvent(raw_message="|switch|p1a: Pikachu|Pikachu, L50|100/100")
        logger.log_event(turn_number=3, event=event)
        logger.close()

        expected_path = os.path.join(
            self.test_dir, f"test_player_opponent2_battle-test-456_{epoch_secs}.txt"
        )
        self.assertTrue(os.path.exists(expected_path))

        with open(expected_path, "r") as f:
            content = f.read()
            lines = content.strip().split("\n")
            self.assertEqual(len(lines), 1)

            log_entry = json.loads(lines[0])
            self.assertEqual(log_entry["turn_number"], 3)
            self.assertEqual(
                log_entry["event"], "|switch|p1a: Pikachu|Pikachu, L50|100/100"
            )

    def test_multiple_events(self) -> None:
        """Test logging multiple events."""
        epoch_secs = 9876543210
        logger = BattleEventLogger(
            player_name="test_player",
            epoch_secs=epoch_secs,
            battle_room="battle-test-multi",
            opponent_name="opponent3",
            log_dir=self.test_dir,
        )

        events = [
            MockBattleEvent(raw_message="|turn|1"),
            MockBattleEvent(raw_message="|move|p1a: Pikachu|Thunder Shock|p2a: Eevee"),
            MockBattleEvent(raw_message="|switch|p2a: Vaporeon|Vaporeon, L50|100/100"),
        ]

        for i, event in enumerate(events):
            logger.log_event(turn_number=i + 1, event=event)

        logger.close()

        expected_path = os.path.join(
            self.test_dir, f"test_player_opponent3_battle-test-multi_{epoch_secs}.txt"
        )
        with open(expected_path, "r") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 3)

            for i, line in enumerate(lines):
                log_entry = json.loads(line)
                self.assertEqual(log_entry["turn_number"], i + 1)
                self.assertIn("event", log_entry)

    def test_context_manager(self) -> None:
        """Test that BattleEventLogger works as a context manager."""
        epoch_secs = 1111111111
        with BattleEventLogger(
            player_name="test_player",
            epoch_secs=epoch_secs,
            battle_room="battle-test-context",
            opponent_name="opponent4",
            log_dir=self.test_dir,
        ) as logger:
            event = MockBattleEvent(raw_message="|start")
            logger.log_event(turn_number=1, event=event)

        expected_path = os.path.join(
            self.test_dir, f"test_player_opponent4_battle-test-context_{epoch_secs}.txt"
        )
        self.assertTrue(os.path.exists(expected_path))

        with open(expected_path, "r") as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 1)

    def test_close_is_idempotent(self) -> None:
        """Test that calling close() multiple times is safe."""
        logger = BattleEventLogger(
            player_name="test_player",
            epoch_secs=2222222222,
            battle_room="battle-test-close",
            opponent_name="opponent5",
            log_dir=self.test_dir,
        )

        logger.close()
        logger.close()
        logger.close()

    def test_log_after_close_does_nothing(self) -> None:
        """Test that logging after close does not raise an error."""
        logger = BattleEventLogger(
            player_name="test_player",
            epoch_secs=3333333333,
            battle_room="battle-test-after-close",
            opponent_name="opponent6",
            log_dir=self.test_dir,
        )

        logger.close()

        event = MockBattleEvent(raw_message="|end")
        logger.log_event(turn_number=1, event=event)

    def test_event_without_raw_message(self) -> None:
        """Test handling events without raw_message attribute."""

        class EventWithoutRawMessage(BattleEvent):
            """Event without raw_message attribute."""

            @classmethod
            def parse_raw_message(cls, raw_message: str) -> "EventWithoutRawMessage":
                """Parse raw message."""
                return cls()

        epoch_secs = 4444444444
        logger = BattleEventLogger(
            player_name="test_player",
            epoch_secs=epoch_secs,
            battle_room="battle-test-no-raw",
            opponent_name="opponent7",
            log_dir=self.test_dir,
        )

        event = EventWithoutRawMessage()
        logger.log_event(turn_number=1, event=event)
        logger.close()

        expected_path = os.path.join(
            self.test_dir, f"test_player_opponent7_battle-test-no-raw_{epoch_secs}.txt"
        )
        self.assertTrue(os.path.exists(expected_path))

        with open(expected_path, "r") as f:
            content = f.read()
            lines = content.strip().split("\n")
            self.assertEqual(len(lines), 1)

            log_entry = json.loads(lines[0])
            self.assertEqual(log_entry["turn_number"], 1)
            self.assertIn("event", log_entry)


if __name__ == "__main__":
    unittest.main()
