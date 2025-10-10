"""Async event stream for batching battle events between decision points."""

from typing import Any, AsyncIterator, List, Literal, Optional

from absl import logging

from python.game.events.battle_event import (
    BattleEndEvent,
    BattleEvent,
    ErrorEvent,
    RequestEvent,
    TurnEvent,
)
from python.game.protocol.battle_event_logger import BattleEventLogger
from python.game.protocol.message_parser import MessageParser


class BattleStream:
    """Async iterator that batches battle events between decision points.

    Supports two modes:
    - 'live': Batches events until |request| (agent needs to choose action)
    - 'replay': Batches events until next |turn| (for replay analysis)
    """

    def __init__(
        self,
        client: Any,
        parser: Optional[MessageParser] = None,
        mode: Literal["live", "replay"] = "live",
        battle_id: Optional[str] = None,
        logger: Optional["BattleEventLogger"] = None,
    ) -> None:
        """Initialize the battle stream.

        Args:
            client: Client with is_connected and receive_message() (e.g., ShowdownClient)
            parser: MessageParser to parse messages (creates new one if None)
            mode: 'live' for real-time battles, 'replay' for replay analysis
            battle_id: Optional battle ID to filter messages (for multi-battle support)
            logger: Optional BattleEventLogger to log events to file
        """
        self._client = client
        self._parser = parser or MessageParser()
        self._mode = mode
        self._battle_id = battle_id
        self._logger = logger
        self._buffer: List[BattleEvent] = []
        self._done = False
        self._current_turn_number: int = 0

    def __aiter__(self) -> AsyncIterator[List[BattleEvent]]:
        """Return async iterator (self)."""
        return self

    async def __anext__(self) -> List[BattleEvent]:
        """Return next batch of events until decision point.

        In live mode: batches until RequestEvent
        In replay mode: batches until next TurnEvent

        Returns:
            List of BattleEvent objects

        Raises:
            StopAsyncIteration: When stream is complete
        """
        if self._done:
            raise StopAsyncIteration

        batch: List[BattleEvent] = []
        decision_event_found = False

        while not decision_event_found:
            if not self._client.is_connected:
                self._done = True
                if batch:
                    return batch
                raise StopAsyncIteration

            try:
                raw_message = await self._client.receive_message()
            except Exception as e:
                logging.error("Error receiving message: %s", e)
                self._done = True
                if batch:
                    return batch
                raise StopAsyncIteration

            if not raw_message.strip():
                continue

            # Check if entire message belongs to our battle (first line has >ROOMID)
            if self._battle_id and not self._matches_battle_id(raw_message):
                continue

            for line in raw_message.split("\n"):
                if not line.strip():
                    continue

                if line.startswith(">"):
                    continue

                event = self._parser.parse(line)
                batch.append(event)

                if isinstance(event, TurnEvent):
                    self._current_turn_number = event.turn_number

                if isinstance(event, ErrorEvent):
                    logging.error(
                        "[%s] Server error: %s", self._battle_id, event.error_text
                    )

                if self._logger:
                    self._logger.log_event(self._current_turn_number, event)

                if self._is_decision_point(event):
                    decision_event_found = True
                    break

            if decision_event_found:
                return batch

        return batch

    def _matches_battle_id(self, raw_message: str) -> bool:
        """Check if message belongs to the specified battle.

        Args:
            raw_message: Raw protocol message

        Returns:
            True if message matches battle ID or battle ID not set
        """
        if not self._battle_id:
            return True

        # Battle-specific messages start with ">battle-BATTLEID"
        # For simplicity, check if battle ID appears in message
        return self._battle_id in raw_message

    def _is_decision_point(self, event: BattleEvent) -> bool:
        """Check if event is a decision point.

        In live mode: RequestEvent or BattleEndEvent signals decision point
        In replay mode: TurnEvent signals decision point

        Args:
            event: BattleEvent to check

        Returns:
            True if this event signals a decision point
        """

        if self._mode == "live":
            return isinstance(event, (RequestEvent, BattleEndEvent))
        else:  # replay mode
            return isinstance(event, TurnEvent)

    async def close(self) -> None:
        """Mark stream as done."""
        self._done = True
