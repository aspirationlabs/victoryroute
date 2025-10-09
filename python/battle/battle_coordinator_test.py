"""Tests for BattleCoordinator."""

import unittest
from queue import Queue
from unittest.mock import MagicMock

from absl.testing import absltest

from python.battle.battle_coordinator import BattleCoordinator
from python.battle.battle_state_tracker import BattleStateTracker, BattleStatus


class BattleCoordinatorTest(unittest.IsolatedAsyncioTestCase, absltest.TestCase):
    """Tests for BattleCoordinator class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_router = MagicMock()
        self.coordinator = BattleCoordinator(
            message_router=self.mock_router,
            max_threads=2,
            battles_per_opponent=2,
        )

    def test_can_start_battle(self) -> None:
        """Test checking if we can start a battle with an opponent."""
        opponent = "testopponent"

        # Should be able to start first battle
        self.assertTrue(self.coordinator.can_start_battle(opponent))

        # Add mock trackers to reach limit
        mock_tracker1 = self._create_mock_tracker("battle-1")
        mock_tracker2 = self._create_mock_tracker("battle-2")

        self.coordinator.start_battle("battle-1", opponent, mock_tracker1)
        self.assertTrue(self.coordinator.can_start_battle(opponent))

        self.coordinator.start_battle("battle-2", opponent, mock_tracker2)
        # Should be at limit now
        self.assertFalse(self.coordinator.can_start_battle(opponent))

    def test_get_active_battle_count(self) -> None:
        """Test getting count of active battles."""
        opponent1 = "opponent1"
        opponent2 = "opponent2"

        # Initially zero
        self.assertEqual(self.coordinator.get_active_battle_count(), 0)
        self.assertEqual(self.coordinator.get_active_battle_count(opponent1), 0)

        # Add battles
        tracker1 = self._create_mock_tracker("battle-1")
        tracker2 = self._create_mock_tracker("battle-2")
        tracker3 = self._create_mock_tracker("battle-3")

        self.coordinator.start_battle("battle-1", opponent1, tracker1)
        self.coordinator.start_battle("battle-2", opponent1, tracker2)
        self.coordinator.start_battle("battle-3", opponent2, tracker3)

        # Check counts
        self.assertEqual(self.coordinator.get_active_battle_count(), 3)
        self.assertEqual(self.coordinator.get_active_battle_count(opponent1), 2)
        self.assertEqual(self.coordinator.get_active_battle_count(opponent2), 1)

    def test_start_battle(self) -> None:
        """Test starting a battle."""
        battle_room = "battle-gen9ou-12345"
        opponent = "testopponent"
        tracker = self._create_mock_tracker(battle_room)

        self.coordinator.start_battle(battle_room, opponent, tracker)

        # Check tracking
        self.assertEqual(self.coordinator.get_active_battle_count(opponent), 1)
        self.assertIsNotNone(self.coordinator.get_battle_tracker(battle_room))

        # Check router registration
        self.mock_router.register_battle.assert_called_once()

    def test_complete_battle(self) -> None:
        """Test completing a battle."""
        battle_room = "battle-gen9ou-12345"
        opponent = "testopponent"
        tracker = self._create_mock_tracker(battle_room)

        # Start battle
        self.coordinator.start_battle(battle_room, opponent, tracker)
        self.assertEqual(self.coordinator.get_active_battle_count(opponent), 1)

        # Complete battle
        result = self.coordinator.complete_battle(battle_room)

        # Check result
        self.assertIsNotNone(result)
        self.assertEqual(result.battle_room, battle_room)

        # Check tracking
        self.assertEqual(self.coordinator.get_active_battle_count(opponent), 0)
        self.assertIsNone(self.coordinator.get_battle_tracker(battle_room))

        # Check router unregistration
        self.mock_router.unregister_battle.assert_called_once_with(battle_room)

    def test_complete_nonexistent_battle(self) -> None:
        """Test completing a battle that doesn't exist."""
        result = self.coordinator.complete_battle("nonexistent-battle")
        self.assertIsNone(result)

    def test_get_all_active_battles(self) -> None:
        """Test getting all active battle room IDs."""
        tracker1 = self._create_mock_tracker("battle-1")
        tracker2 = self._create_mock_tracker("battle-2")

        self.coordinator.start_battle("battle-1", "opponent1", tracker1)
        self.coordinator.start_battle("battle-2", "opponent2", tracker2)

        active_battles = self.coordinator.get_all_active_battles()
        self.assertEqual(len(active_battles), 2)
        self.assertIn("battle-1", active_battles)
        self.assertIn("battle-2", active_battles)

    def test_multiple_battles_same_opponent(self) -> None:
        """Test tracking multiple battles with the same opponent."""
        opponent = "testopponent"
        tracker1 = self._create_mock_tracker("battle-1")
        tracker2 = self._create_mock_tracker("battle-2")

        self.coordinator.start_battle("battle-1", opponent, tracker1)
        self.coordinator.start_battle("battle-2", opponent, tracker2)

        self.assertEqual(self.coordinator.get_active_battle_count(opponent), 2)

        # Complete one battle
        self.coordinator.complete_battle("battle-1")
        self.assertEqual(self.coordinator.get_active_battle_count(opponent), 1)

        # Complete second battle
        self.coordinator.complete_battle("battle-2")
        self.assertEqual(self.coordinator.get_active_battle_count(opponent), 0)

    def _create_mock_tracker(self, battle_room: str) -> BattleStateTracker:
        """Create a mock BattleStateTracker.

        Args:
            battle_room: Battle room ID

        Returns:
            Mock BattleStateTracker
        """
        mock_tracker = MagicMock(spec=BattleStateTracker)
        mock_tracker.battle_room = battle_room
        mock_tracker.status = BattleStatus.IN_PROGRESS
        mock_tracker.turn_count = 0
        mock_tracker._message_queue = Queue()  # noqa: SLF001
        mock_tracker.is_complete.return_value = False
        mock_tracker.get_result.return_value = MagicMock(
            battle_room=battle_room,
            winner=None,
            turn_count=0,
            duration=0.0,
            status=BattleStatus.COMPLETED,
        )
        return mock_tracker


if __name__ == "__main__":
    absltest.main()
