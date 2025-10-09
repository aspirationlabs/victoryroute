"""Battle coordinator for managing multiple concurrent battles."""

import asyncio
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from absl import logging

from python.battle.battle_state_tracker import BattleResult, BattleStateTracker


class BattleCoordinator:
    """Coordinates multiple concurrent battles with thread pool for agent decisions.

    The BattleCoordinator manages:
    - Active battle trackers (one per battle)
    - Thread pool for executing agent decisions
    - Per-opponent battle limits
    - Battle completion and cleanup

    Architecture:
    - Main async loop manages battle state
    - Thread pool processes individual agent decisions (CPU-intensive)
    - When a state needs a decision, submit to thread pool
    - When decision completes, send action and wait for next state
    """

    def __init__(
        self,
        message_router: Any,
        max_threads: int = 8,
        battles_per_opponent: int = 4,
    ) -> None:
        """Initialize battle coordinator.

        Args:
            message_router: MessageRouter for registering battles
            max_threads: Maximum worker threads for agent decisions
            battles_per_opponent: Maximum concurrent battles per opponent
        """
        self._message_router = message_router
        self._executor = ThreadPoolExecutor(max_workers=max_threads)
        self._battles_per_opponent = battles_per_opponent

        # Track active battles
        self._active_battles: Dict[str, BattleStateTracker] = {}  # room_id -> tracker
        self._opponent_battles: Dict[str, List[str]] = {}  # opponent -> [room_ids]
        self._lock = threading.Lock()

    def can_start_battle(self, opponent: str) -> bool:
        """Check if we can start a new battle with this opponent.

        Args:
            opponent: Opponent username (normalized)

        Returns:
            True if under the per-opponent limit
        """
        with self._lock:
            current_count = len(self._opponent_battles.get(opponent, []))
            return current_count < self._battles_per_opponent

    def get_active_battle_count(self, opponent: Optional[str] = None) -> int:
        """Get count of active battles.

        Args:
            opponent: If specified, count only battles with this opponent.
                     If None, count all battles.

        Returns:
            Number of active battles
        """
        with self._lock:
            if opponent:
                return len(self._opponent_battles.get(opponent, []))
            return len(self._active_battles)

    def start_battle(
        self,
        battle_room: str,
        opponent: str,
        tracker: BattleStateTracker,
    ) -> None:
        """Register a new battle.

        Args:
            battle_room: Battle room ID
            opponent: Opponent username (normalized)
            tracker: Initialized BattleStateTracker
        """
        with self._lock:
            self._active_battles[battle_room] = tracker

            if opponent not in self._opponent_battles:
                self._opponent_battles[opponent] = []
            self._opponent_battles[opponent].append(battle_room)

        # Register with message router
        self._message_router.register_battle(
            battle_room,
            tracker._message_queue,  # noqa: SLF001
        )

        logging.info(
            f"[BattleCoordinator] Started battle {battle_room} vs {opponent} "
            f"(total: {len(self._active_battles)})"
        )

    def get_battle_tracker(self, battle_room: str) -> Optional[BattleStateTracker]:
        """Get tracker for a specific battle.

        Args:
            battle_room: Battle room ID

        Returns:
            BattleStateTracker if found, None otherwise
        """
        with self._lock:
            return self._active_battles.get(battle_room)

    def complete_battle(self, battle_room: str) -> Optional[BattleResult]:
        """Mark a battle as complete and clean up.

        Args:
            battle_room: Battle room ID

        Returns:
            BattleResult if battle existed, None otherwise
        """
        with self._lock:
            tracker = self._active_battles.get(battle_room)
            if not tracker:
                return None

            result = tracker.get_result()

            # Remove from tracking
            del self._active_battles[battle_room]

            # Remove from opponent list
            for opponent, rooms in self._opponent_battles.items():
                if battle_room in rooms:
                    rooms.remove(battle_room)
                    if not rooms:
                        del self._opponent_battles[opponent]
                    break

        # Unregister from message router
        self._message_router.unregister_battle(battle_room)

        logging.info(
            f"[BattleCoordinator] Completed battle {battle_room}: "
            f"winner={result.winner}, turns={result.turn_count}, "
            f"duration={result.duration:.1f}s "
            f"(remaining: {len(self._active_battles)})"
        )

        return result

    async def process_battle_moves(self) -> None:
        """Process one round of moves for all active battles.

        This should be called repeatedly from the main loop.
        For each battle that needs a decision, submits it to the thread pool.
        """
        # Get list of battles that need decisions (in a thread-safe manner)
        battles_to_process: List[BattleStateTracker] = []
        with self._lock:
            for tracker in self._active_battles.values():
                if not tracker.is_complete():
                    battles_to_process.append(tracker)

        if not battles_to_process:
            return

        # Submit decision tasks to thread pool
        futures: List[Future[None]] = []
        for tracker in battles_to_process:
            future = self._executor.submit(self._make_decision_sync, tracker)
            futures.append(future)

        # Wait for all decisions to complete (with timeout)
        if futures:
            # Use asyncio to wait for thread pool futures
            await asyncio.get_event_loop().run_in_executor(
                None, self._wait_for_decisions, futures
            )

    def _wait_for_decisions(self, futures: List[Future[None]]) -> None:
        """Wait for decision futures to complete (runs in thread pool).

        Args:
            futures: List of futures from decision submissions
        """
        for future in futures:
            try:
                future.result(timeout=30.0)  # 30 second timeout per decision
            except Exception as e:
                logging.error(f"Decision failed: {e}")

    def _make_decision_sync(self, tracker: BattleStateTracker) -> None:
        """Synchronous wrapper for make_decision (runs in thread pool).

        Args:
            tracker: Battle tracker to make decision for
        """
        # Run async code in the thread pool
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(tracker.make_decision())
        finally:
            loop.close()

    def shutdown(self, timeout: float = 30.0) -> None:
        """Shutdown the coordinator and wait for pending decisions.

        Args:
            timeout: Maximum time to wait for pending work
        """
        logging.info("[BattleCoordinator] Shutting down...")
        self._executor.shutdown(wait=True, cancel_futures=False)
        logging.info("[BattleCoordinator] Shutdown complete")

    def get_all_active_battles(self) -> List[str]:
        """Get list of all active battle room IDs.

        Returns:
            List of battle room IDs
        """
        with self._lock:
            return list(self._active_battles.keys())
