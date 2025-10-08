"""Tests for BattleStream event batching."""

import unittest
from typing import List

from python.game.events.battle_event import (
    BattleEvent,
    DamageEvent,
    MoveEvent,
    RequestEvent,
    SwitchEvent,
    TurnEvent,
)
from python.game.protocol.battle_stream import BattleStream


class FakeShowdownClient:
    """Fake ShowdownClient for testing."""

    def __init__(self, messages: List[str]) -> None:
        """Initialize with a list of messages to return.

        Args:
            messages: List of raw protocol messages
        """
        self._messages = messages
        self._index = 0
        self.is_connected = True

    async def receive_message(self) -> str:
        """Return next message from the list.

        Returns:
            Next message in the list

        Raises:
            IndexError: If no more messages available
        """
        if self._index >= len(self._messages):
            self.is_connected = False
            raise IndexError("No more messages")

        message = self._messages[self._index]
        self._index += 1
        return message


class BattleStreamTest(unittest.IsolatedAsyncioTestCase):
    """Tests for BattleStream."""

    async def test_live_mode_batches_until_request(self) -> None:
        """Test that live mode batches events until RequestEvent."""
        messages = [
            "|turn|1",
            "|switch|p1a: pikachu|pikachu|100/100",
            "|move|p2a: charizard|flamethrower|p1a: pikachu",
            "|-damage|p1a: pikachu|80/100",
            '|request|{"active":[{"moves":[]}]}',
        ]

        client = FakeShowdownClient(messages)
        stream = BattleStream(client, mode="live")

        batch: List[BattleEvent] = []
        async for events in stream:
            batch = events
            break

        # Should batch all events until request
        self.assertEqual(len(batch), 5)
        self.assertIsInstance(batch[0], TurnEvent)
        self.assertIsInstance(batch[1], SwitchEvent)
        self.assertIsInstance(batch[2], MoveEvent)
        self.assertIsInstance(batch[3], DamageEvent)
        self.assertIsInstance(batch[4], RequestEvent)

    async def test_replay_mode_batches_until_turn(self) -> None:
        """Test that replay mode batches events until next TurnEvent."""
        messages = [
            "|turn|1",
            "|switch|p1a: pikachu|pikachu|100/100",
            "|move|p2a: charizard|flamethrower|p1a: pikachu",
            "|-damage|p1a: pikachu|80/100",
            "|turn|2",
        ]

        client = FakeShowdownClient(messages)
        stream = BattleStream(client, mode="replay")

        # First batch should be until first turn event
        batch1: List[BattleEvent] = []
        async for events in stream:
            batch1 = events
            break

        # In replay mode, turn events signal decision points
        # First batch should contain turn 1
        self.assertEqual(len(batch1), 1)
        self.assertIsInstance(batch1[0], TurnEvent)
        self.assertEqual(batch1[0].turn_number, 1)

    async def test_multiline_messages(self) -> None:
        """Test that BattleStream handles multiline messages correctly."""
        messages = [
            "|turn|1\n|switch|p1a: pikachu|pikachu|100/100\n|move|p2a: charizard|flamethrower|p1a: pikachu",
            "|-damage|p1a: pikachu|80/100\n|turn|2",
        ]

        client = FakeShowdownClient(messages)
        stream = BattleStream(client, mode="replay")

        batch1: List[BattleEvent] = []
        async for events in stream:
            batch1 = events
            break

        # First batch should contain turn 1 + following events until turn 2
        self.assertEqual(len(batch1), 1)
        self.assertIsInstance(batch1[0], TurnEvent)
        self.assertEqual(batch1[0].turn_number, 1)

    async def test_empty_messages_skipped(self) -> None:
        """Test that empty messages are skipped."""
        messages = [
            "",
            "|turn|1",
            "\n",
            "|switch|p1a: pikachu|pikachu|100/100",
            "  ",
            "|turn|2",
        ]

        client = FakeShowdownClient(messages)
        stream = BattleStream(client, mode="replay")

        batch1: List[BattleEvent] = []
        async for events in stream:
            batch1 = events
            break

        # Should skip empty messages
        self.assertEqual(len(batch1), 1)
        self.assertIsInstance(batch1[0], TurnEvent)

    async def test_stream_ends_when_client_disconnects(self) -> None:
        """Test that stream ends gracefully when client disconnects."""
        messages = [
            "|turn|1",
        ]

        client = FakeShowdownClient(messages)
        stream = BattleStream(client, mode="replay")

        batches: List[List[BattleEvent]] = []
        async for events in stream:
            batches.append(events)

        # Should get exactly one batch
        self.assertEqual(len(batches), 1)


if __name__ == "__main__":
    unittest.main()
