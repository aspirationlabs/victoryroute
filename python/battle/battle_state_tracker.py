"""Battle state tracker for managing individual battle lifecycle."""

import time
from dataclasses import dataclass
from enum import Enum
from queue import Queue
from typing import Any, Optional

from absl import logging

from python.game.environment.battle_environment import BattleEnvironment
from python.game.protocol.battle_event_logger import BattleEventLogger
from python.game.schema.battle_state import BattleState


class BattleStatus(Enum):
    """Status of a battle."""

    INITIALIZING = "initializing"
    TEAM_PREVIEW = "team_preview"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class BattleResult:
    """Result of a completed battle."""

    battle_room: str
    winner: Optional[str]
    turn_count: int
    duration: float  # seconds
    status: BattleStatus


class BattleStateTracker:
    """Tracks state for a single battle and coordinates agent decisions.

    This class maintains the battle environment, current state, and manages
    the transition between turns. It does not block - it processes messages
    and makes decisions when called.
    """

    # Timeout constants
    MAX_TURNS = 1000  # Maximum turns before considering battle stuck
    MAX_WALL_TIME = 1800.0  # Maximum 30 minutes per battle

    def __init__(
        self,
        client: Any,
        battle_room: str,
        agent: Any,
        game_data: Any,
        username: str,
        message_queue: Queue[str],
        logger: Optional[BattleEventLogger] = None,
    ) -> None:
        """Initialize battle state tracker.

        Args:
            client: Shared ShowdownClient
            battle_room: Battle room ID
            agent: Agent to make decisions
            game_data: GameData for agent
            username: Our username (to determine win/loss)
            message_queue: Queue to receive messages for this battle
            logger: Optional event logger
        """
        self._client = client
        self._battle_room = battle_room
        self._agent = agent
        self._game_data = game_data
        self._username = username
        self._message_queue = message_queue
        self._logger = logger

        self._env = BattleEnvironment(
            client, battle_room=battle_room, track_history=False, logger=logger
        )
        self._state: Optional[BattleState] = None
        self._status = BattleStatus.INITIALIZING
        self._turn_count = 0
        self._start_time = time.time()
        self._last_decision_time = time.time()
        self._error_message: Optional[str] = None

    @property
    def battle_room(self) -> str:
        """Get battle room ID."""
        return self._battle_room

    @property
    def status(self) -> BattleStatus:
        """Get current battle status."""
        return self._status

    @property
    def turn_count(self) -> int:
        """Get current turn count."""
        return self._turn_count

    async def initialize(self) -> None:
        """Initialize the battle environment and wait for first state.

        This should be called once after the battle room is joined.
        """
        logging.info(f"[{self._battle_room}] Initializing battle")
        try:
            self._state = await self._env.reset()
            if self._state.team_preview:
                self._status = BattleStatus.TEAM_PREVIEW
            else:
                self._status = BattleStatus.IN_PROGRESS
            logging.info(f"[{self._battle_room}] Battle initialized")
        except Exception as e:
            logging.error(f"[{self._battle_room}] Failed to initialize: {e}")
            self._status = BattleStatus.ERROR
            raise

    def is_complete(self) -> bool:
        """Check if battle is complete."""
        if self._env.is_battle_over() or self._status in (
            BattleStatus.COMPLETED,
            BattleStatus.ERROR,
        ):
            return True

        # Check for timeouts
        if self._check_timeout():
            return True

        return False

    def _check_timeout(self) -> bool:
        """Check if battle has timed out.

        Returns:
            True if battle should be terminated due to timeout
        """
        # Check turn limit
        if self._turn_count >= self.MAX_TURNS:
            logging.warning(
                f"[{self._battle_room}] Battle exceeded max turns ({self.MAX_TURNS})"
            )
            self._status = BattleStatus.ERROR
            self._error_message = f"Exceeded max turns: {self._turn_count}"
            return True

        # Check wall time
        elapsed = time.time() - self._start_time
        if elapsed >= self.MAX_WALL_TIME:
            logging.warning(
                f"[{self._battle_room}] Battle exceeded max time "
                f"({elapsed:.1f}s / {self.MAX_WALL_TIME}s)"
            )
            self._status = BattleStatus.ERROR
            self._error_message = f"Exceeded max time: {elapsed:.1f}s"
            return True

        return False

    def get_result(self) -> BattleResult:
        """Get battle result (only valid if is_complete() is True).

        Returns:
            BattleResult with outcome details
        """
        duration = time.time() - self._start_time
        winner = None
        if self._state:
            winner = self._state.winner

        return BattleResult(
            battle_room=self._battle_room,
            winner=winner,
            turn_count=self._turn_count,
            duration=duration,
            status=self._status,
        )

    async def make_decision(self) -> None:
        """Make a single decision (choose and send action).

        This is the function that will be called from the thread pool.
        It blocks on agent.choose_action() then sends the action to the server.

        Error handling:
        - Catches exceptions and marks battle as ERROR
        - Logs detailed error information
        - Does not raise - allows other battles to continue
        """
        if self._state is None:
            raise RuntimeError("Battle not initialized")

        if self.is_complete():
            logging.debug(f"[{self._battle_room}] Decision called on complete battle")
            return

        try:
            # Agent decides (this is the CPU-intensive part that runs in thread pool)
            self._last_decision_time = time.time()
            action = await self._agent.choose_action(self._state, self._game_data)
            logging.info(f"[{self._battle_room}] Action selected: {action}")

            # Send action and wait for next state
            self._state = await self._env.step(action)

            # Update counters
            if not self._state.team_preview:
                self._turn_count += 1

            # Check if battle ended
            if self._env.is_battle_over():
                self._status = BattleStatus.COMPLETED
                result = self.get_result()
                if result.winner == self._username:
                    logging.info(f"[{self._battle_room}] Victory!")
                elif result.winner is None:
                    logging.info(f"[{self._battle_room}] Tie")
                else:
                    logging.info(f"[{self._battle_room}] Defeat")

        except KeyboardInterrupt:
            # Allow graceful shutdown
            raise
        except Exception as e:
            # Log detailed error but don't raise - other battles should continue
            logging.error(
                f"[{self._battle_room}] Error making decision (turn {self._turn_count}): "
                f"{type(e).__name__}: {e}",
                exc_info=True,
            )
            self._status = BattleStatus.ERROR
            self._error_message = f"{type(e).__name__}: {str(e)}"
