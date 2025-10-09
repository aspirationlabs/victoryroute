"""Tests for opponent stats tracker."""

import tempfile
import threading
from pathlib import Path

from absl.testing import absltest

from python.battle.opponent_stats_tracker import OpponentStats, OpponentStatsTracker


class OpponentStatsTest(absltest.TestCase):
    """Tests for OpponentStats dataclass."""

    def test_total_battles(self) -> None:
        """Test total_battles property."""
        stats = OpponentStats(wins=5, losses=3, ties=1)
        self.assertEqual(stats.total_battles, 9)

    def test_win_percentage_no_battles(self) -> None:
        """Test win_percentage with no battles."""
        stats = OpponentStats()
        self.assertEqual(stats.win_percentage, 0.0)

    def test_win_percentage_only_ties(self) -> None:
        """Test win_percentage with only ties."""
        stats = OpponentStats(ties=5)
        self.assertEqual(stats.win_percentage, 0.0)

    def test_win_percentage_with_wins_and_losses(self) -> None:
        """Test win_percentage calculation."""
        stats = OpponentStats(wins=7, losses=3)
        self.assertEqual(stats.win_percentage, 70.0)

    def test_win_percentage_excludes_ties(self) -> None:
        """Test that win_percentage excludes ties from calculation."""
        stats = OpponentStats(wins=5, losses=5, ties=10)
        self.assertEqual(stats.win_percentage, 50.0)

    def test_win_loss_ratio_no_losses(self) -> None:
        """Test win_loss_ratio with no losses returns None."""
        stats = OpponentStats(wins=5)
        self.assertIsNone(stats.win_loss_ratio)

    def test_win_loss_ratio_calculation(self) -> None:
        """Test win_loss_ratio calculation."""
        stats = OpponentStats(wins=6, losses=2)
        self.assertEqual(stats.win_loss_ratio, 3.0)

    def test_to_dict(self) -> None:
        """Test to_dict serialization."""
        stats = OpponentStats(wins=5, losses=3, ties=1)
        result = stats.to_dict()
        self.assertEqual(result["wins"], 5)
        self.assertEqual(result["losses"], 3)
        self.assertEqual(result["ties"], 1)
        self.assertEqual(result["total_battles"], 9)
        self.assertEqual(result["win_percentage"], 62.5)
        self.assertEqual(result["win_loss_ratio"], 1.67)

    def test_to_dict_no_losses(self) -> None:
        """Test to_dict with no losses."""
        stats = OpponentStats(wins=3)
        result = stats.to_dict()
        self.assertIsNone(result["win_loss_ratio"])


class OpponentStatsTrackerTest(absltest.TestCase):
    """Tests for OpponentStatsTracker."""

    def setUp(self) -> None:
        """Create a temporary file for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.stats_file = Path(self.temp_dir) / "test_stats.json"

    def test_init_creates_empty_stats(self) -> None:
        """Test initialization with no existing file."""
        tracker = OpponentStatsTracker(self.stats_file)
        self.assertEqual(len(tracker.get_all_stats()), 0)

    def test_record_win(self) -> None:
        """Test recording a win."""
        tracker = OpponentStatsTracker(self.stats_file)
        stats = tracker.record_battle("TestOpponent", won=True)
        self.assertEqual(stats.wins, 1)
        self.assertEqual(stats.losses, 0)
        self.assertEqual(stats.ties, 0)

    def test_record_loss(self) -> None:
        """Test recording a loss."""
        tracker = OpponentStatsTracker(self.stats_file)
        stats = tracker.record_battle("TestOpponent", won=False)
        self.assertEqual(stats.wins, 0)
        self.assertEqual(stats.losses, 1)
        self.assertEqual(stats.ties, 0)

    def test_record_tie(self) -> None:
        """Test recording a tie."""
        tracker = OpponentStatsTracker(self.stats_file)
        stats = tracker.record_battle("TestOpponent", won=False, tied=True)
        self.assertEqual(stats.wins, 0)
        self.assertEqual(stats.losses, 0)
        self.assertEqual(stats.ties, 1)

    def test_record_multiple_battles(self) -> None:
        """Test recording multiple battles against same opponent."""
        tracker = OpponentStatsTracker(self.stats_file)
        tracker.record_battle("TestOpponent", won=True)
        tracker.record_battle("TestOpponent", won=True)
        tracker.record_battle("TestOpponent", won=False)
        tracker.record_battle("TestOpponent", won=False, tied=True)

        stats = tracker.get_stats("TestOpponent")
        self.assertIsNotNone(stats)
        self.assertEqual(stats.wins, 2)
        self.assertEqual(stats.losses, 1)
        self.assertEqual(stats.ties, 1)

    def test_multiple_opponents(self) -> None:
        """Test tracking stats for multiple opponents."""
        tracker = OpponentStatsTracker(self.stats_file)
        tracker.record_battle("Opponent1", won=True)
        tracker.record_battle("Opponent2", won=False)

        stats1 = tracker.get_stats("Opponent1")
        stats2 = tracker.get_stats("Opponent2")

        self.assertIsNotNone(stats1)
        self.assertIsNotNone(stats2)
        self.assertEqual(stats1.wins, 1)
        self.assertEqual(stats2.losses, 1)

    def test_get_stats_nonexistent_opponent(self) -> None:
        """Test getting stats for opponent with no battles."""
        tracker = OpponentStatsTracker(self.stats_file)
        stats = tracker.get_stats("NonexistentOpponent")
        self.assertIsNone(stats)

    def test_persistence(self) -> None:
        """Test that stats are persisted to file and loaded correctly."""
        tracker1 = OpponentStatsTracker(self.stats_file)
        tracker1.record_battle("Opponent1", won=True)
        tracker1.record_battle("Opponent1", won=False)

        # Create new tracker with same file
        tracker2 = OpponentStatsTracker(self.stats_file)
        stats = tracker2.get_stats("Opponent1")

        self.assertIsNotNone(stats)
        self.assertEqual(stats.wins, 1)
        self.assertEqual(stats.losses, 1)

    def test_thread_safety(self) -> None:
        """Test thread-safe concurrent access."""
        tracker = OpponentStatsTracker(self.stats_file)
        threads = []

        def record_wins() -> None:
            for _ in range(100):
                tracker.record_battle("ThreadTest", won=True)

        def record_losses() -> None:
            for _ in range(100):
                tracker.record_battle("ThreadTest", won=False)

        # Start multiple threads
        for _ in range(5):
            t1 = threading.Thread(target=record_wins)
            t2 = threading.Thread(target=record_losses)
            threads.extend([t1, t2])
            t1.start()
            t2.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Verify total is correct
        stats = tracker.get_stats("ThreadTest")
        self.assertIsNotNone(stats)
        self.assertEqual(stats.wins, 500)  # 5 threads * 100 wins
        self.assertEqual(stats.losses, 500)  # 5 threads * 100 losses


if __name__ == "__main__":
    absltest.main()
