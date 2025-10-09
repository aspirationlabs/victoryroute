"""Tests for BattleStateTracker."""

import time
import unittest
from queue import Queue
from unittest.mock import AsyncMock, MagicMock

from absl.testing import absltest

from python.battle.battle_state_tracker import (
    BattleResult,
    BattleStateTracker,
    BattleStatus,
)


class BattleStateTrackerTest(unittest.IsolatedAsyncioTestCase, absltest.TestCase):
    """Tests for BattleStateTracker class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.mock_agent = MagicMock()
        self.mock_game_data = MagicMock()
        self.message_queue: Queue[str] = Queue()

        self.tracker = BattleStateTracker(
            client=self.mock_client,
            battle_room="battle-test-123",
            agent=self.mock_agent,
            game_data=self.mock_game_data,
            username="testuser",
            message_queue=self.message_queue,
            logger=None,
        )

    def test_initialization(self) -> None:
        """Test tracker initialization."""
        self.assertEqual(self.tracker.battle_room, "battle-test-123")
        self.assertEqual(self.tracker.status, BattleStatus.INITIALIZING)
        self.assertEqual(self.tracker.turn_count, 0)

    def test_timeout_max_turns(self) -> None:
        """Test timeout detection for max turns."""
        # Set turn count to exceed limit
        self.tracker._turn_count = BattleStateTracker.MAX_TURNS + 1  # noqa: SLF001

        # Check timeout
        is_timeout = self.tracker._check_timeout()  # noqa: SLF001
        self.assertTrue(is_timeout)
        self.assertEqual(self.tracker.status, BattleStatus.ERROR)
        self.assertIsNotNone(self.tracker._error_message)  # noqa: SLF001
        self.assertIn("max turns", self.tracker._error_message or "")  # noqa: SLF001

    def test_timeout_wall_time(self) -> None:
        """Test timeout detection for wall time."""
        # Set start time to exceed wall time limit
        self.tracker._start_time = (  # noqa: SLF001
            time.time() - BattleStateTracker.MAX_WALL_TIME - 1
        )

        # Check timeout
        is_timeout = self.tracker._check_timeout()  # noqa: SLF001
        self.assertTrue(is_timeout)
        self.assertEqual(self.tracker.status, BattleStatus.ERROR)
        self.assertIsNotNone(self.tracker._error_message)  # noqa: SLF001
        self.assertIn("max time", self.tracker._error_message or "")  # noqa: SLF001

    def test_no_timeout(self) -> None:
        """Test that timeout is not triggered for normal battles."""
        self.tracker._turn_count = 10  # noqa: SLF001
        self.tracker._start_time = time.time()  # noqa: SLF001

        is_timeout = self.tracker._check_timeout()  # noqa: SLF001
        self.assertFalse(is_timeout)
        self.assertEqual(self.tracker.status, BattleStatus.INITIALIZING)

    def test_is_complete_on_timeout(self) -> None:
        """Test is_complete returns True when timeout occurs."""
        self.tracker._turn_count = BattleStateTracker.MAX_TURNS + 1  # noqa: SLF001

        self.assertTrue(self.tracker.is_complete())
        self.assertEqual(self.tracker.status, BattleStatus.ERROR)

    def test_get_result(self) -> None:
        """Test getting battle result."""
        self.tracker._status = BattleStatus.COMPLETED  # noqa: SLF001
        self.tracker._turn_count = 42  # noqa: SLF001

        result = self.tracker.get_result()

        self.assertIsInstance(result, BattleResult)
        self.assertEqual(result.battle_room, "battle-test-123")
        self.assertEqual(result.turn_count, 42)
        self.assertEqual(result.status, BattleStatus.COMPLETED)
        self.assertGreaterEqual(result.duration, 0)

    async def test_make_decision_error_handling(self) -> None:
        """Test error handling in make_decision."""
        # Set up mock state
        mock_state = MagicMock()
        mock_state.team_preview = False
        mock_state.winner = None
        self.tracker._state = mock_state  # noqa: SLF001

        # Mock agent to raise exception
        self.mock_agent.choose_action = AsyncMock(
            side_effect=RuntimeError("Test error")
        )

        # Make decision should catch the error
        await self.tracker.make_decision()

        # Check that status is ERROR
        self.assertEqual(self.tracker.status, BattleStatus.ERROR)
        self.assertIsNotNone(self.tracker._error_message)  # noqa: SLF001
        self.assertIn("RuntimeError", self.tracker._error_message or "")  # noqa: SLF001

    async def test_make_decision_keyboard_interrupt(self) -> None:
        """Test that KeyboardInterrupt is re-raised."""
        mock_state = MagicMock()
        self.tracker._state = mock_state  # noqa: SLF001

        # Mock agent to raise KeyboardInterrupt
        self.mock_agent.choose_action = AsyncMock(side_effect=KeyboardInterrupt())

        # Should re-raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            await self.tracker.make_decision()

    async def test_make_decision_when_complete(self) -> None:
        """Test that make_decision returns early when battle is complete."""
        mock_state = MagicMock()
        self.tracker._state = mock_state  # noqa: SLF001
        self.tracker._status = BattleStatus.COMPLETED  # noqa: SLF001

        # Should return without calling agent
        await self.tracker.make_decision()

        # Agent should not be called
        self.mock_agent.choose_action.assert_not_called()

    async def test_make_decision_uninitialized(self) -> None:
        """Test that make_decision raises when battle not initialized."""
        # State is None by default in setUp
        self.tracker._state = None  # noqa: SLF001

        with self.assertRaises(RuntimeError):
            await self.tracker.make_decision()


class BattleResultTest(absltest.TestCase):
    """Tests for BattleResult dataclass."""

    def test_battle_result_creation(self) -> None:
        """Test creating a BattleResult."""
        result = BattleResult(
            battle_room="battle-test-123",
            winner="player1",
            turn_count=50,
            duration=123.45,
            status=BattleStatus.COMPLETED,
        )

        self.assertEqual(result.battle_room, "battle-test-123")
        self.assertEqual(result.winner, "player1")
        self.assertEqual(result.turn_count, 50)
        self.assertEqual(result.duration, 123.45)
        self.assertEqual(result.status, BattleStatus.COMPLETED)


if __name__ == "__main__":
    absltest.main()
