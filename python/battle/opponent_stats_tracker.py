"""Track win/loss statistics against opponents."""

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class OpponentStats:
    """Statistics for battles against a specific opponent."""

    wins: int = 0
    losses: int = 0
    ties: int = 0

    @property
    def total_battles(self) -> int:
        """Total number of battles against this opponent."""
        return self.wins + self.losses + self.ties

    @property
    def win_percentage(self) -> float:
        """Win percentage against this opponent (excluding ties)."""
        decisive_battles = self.wins + self.losses
        if decisive_battles == 0:
            return 0.0
        return (self.wins / decisive_battles) * 100

    @property
    def win_loss_ratio(self) -> Optional[float]:
        """Win/loss ratio against this opponent.

        Returns None if there are no losses yet.
        """
        if self.losses == 0:
            return None
        return self.wins / self.losses

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "wins": self.wins,
            "losses": self.losses,
            "ties": self.ties,
            "total_battles": self.total_battles,
            "win_percentage": round(self.win_percentage, 2),
            "win_loss_ratio": (
                round(self.win_loss_ratio, 2)
                if self.win_loss_ratio is not None
                else None
            ),
        }


class OpponentStatsTracker:
    """Tracks battle statistics against opponents.

    This class is thread-safe for concurrent access.
    """

    def __init__(self, stats_file: Optional[Path] = None) -> None:
        """Initialize the stats tracker.

        Args:
            stats_file: Path to save/load stats. Defaults to ~/.victoryroute/opponent_stats.json
        """
        if stats_file is None:
            stats_file = Path.home() / ".victoryroute" / "opponent_stats.json"

        self.stats_file = stats_file
        self.stats: Dict[str, OpponentStats] = {}
        self._lock = threading.Lock()
        self._load_stats()

    def _load_stats(self) -> None:
        """Load stats from file if it exists.

        Note: This is called from __init__, so no lock is needed.
        """
        if self.stats_file.exists():
            try:
                with open(self.stats_file, "r") as f:
                    data = json.load(f)
                    for opponent, stats_dict in data.items():
                        self.stats[opponent] = OpponentStats(
                            wins=stats_dict.get("wins", 0),
                            losses=stats_dict.get("losses", 0),
                            ties=stats_dict.get("ties", 0),
                        )
            except (json.JSONDecodeError, IOError):
                self.stats = {}

    def _save_stats(self) -> None:
        """Save stats to file.

        Note: Caller must hold the lock.
        """
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.stats_file, "w") as f:
            data = {opponent: stats.to_dict() for opponent, stats in self.stats.items()}
            json.dump(data, f, indent=2)

    def record_battle(
        self, opponent: str, won: bool, tied: bool = False
    ) -> OpponentStats:
        """Record the result of a battle against an opponent.

        Args:
            opponent: Username of the opponent
            won: True if we won, False if we lost (ignored if tied=True)
            tied: True if the battle was a tie

        Returns:
            Updated stats for this opponent
        """
        with self._lock:
            if opponent not in self.stats:
                self.stats[opponent] = OpponentStats()

            stats = self.stats[opponent]

            if tied:
                stats.ties += 1
            elif won:
                stats.wins += 1
            else:
                stats.losses += 1

            self._save_stats()
            return stats

    def get_stats(self, opponent: str) -> Optional[OpponentStats]:
        """Get stats for a specific opponent.

        Args:
            opponent: Username of the opponent

        Returns:
            Stats for this opponent, or None if no battles recorded
        """
        with self._lock:
            return self.stats.get(opponent)

    def get_all_stats(self) -> Dict[str, OpponentStats]:
        """Get stats for all opponents.

        Returns:
            Dictionary mapping opponent usernames to their stats
        """
        with self._lock:
            return self.stats.copy()
