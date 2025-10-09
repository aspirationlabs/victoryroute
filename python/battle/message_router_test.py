"""Tests for MessageRouter."""

import asyncio
import unittest
from queue import Queue
from unittest.mock import AsyncMock, MagicMock

from absl.testing import absltest

from python.battle.message_router import MessageRouter


class MessageRouterTest(unittest.IsolatedAsyncioTestCase, absltest.TestCase):
    """Tests for MessageRouter class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.mock_client.is_connected = True
        self.router = MessageRouter(self.mock_client)

    def test_register_and_unregister_battle(self) -> None:
        """Test registering and unregistering battle rooms."""
        battle_queue: Queue[str] = Queue()
        room_id = "battle-gen9ou-12345"

        # Register
        self.router.register_battle(room_id, battle_queue)
        self.assertIn(room_id, self.router._battle_queues)  # noqa: SLF001

        # Unregister
        self.router.unregister_battle(room_id)
        self.assertNotIn(room_id, self.router._battle_queues)  # noqa: SLF001

    def test_parse_room_id(self) -> None:
        """Test parsing room ID from messages."""
        # Battle message with room ID
        message_with_room = ">battle-gen9ou-12345\n|turn|1\n|move|..."
        room_id = self.router._parse_room_id(message_with_room)  # noqa: SLF001
        self.assertEqual(room_id, "battle-gen9ou-12345")

        # Lobby message (no room ID)
        lobby_message = "|pm|User1|User2|Hello"
        room_id = self.router._parse_room_id(lobby_message)  # noqa: SLF001
        self.assertIsNone(room_id)

    async def test_route_to_battle(self) -> None:
        """Test routing messages to battle queues."""
        battle_queue: Queue[str] = Queue()
        room_id = "battle-gen9ou-12345"
        self.router.register_battle(room_id, battle_queue)

        message = ">battle-gen9ou-12345\n|turn|1"
        self.router._route_to_battle(room_id, message)  # noqa: SLF001

        # Check message was queued
        self.assertFalse(battle_queue.empty())
        queued_message = battle_queue.get_nowait()
        self.assertEqual(queued_message, message)

    async def test_route_to_lobby(self) -> None:
        """Test routing messages to lobby queue."""
        lobby_queue = self.router.get_lobby_queue()

        message = "|pm|User1|User2|/challenge gen9ou"
        self.router._route_to_lobby(message)  # noqa: SLF001

        # Check message was queued
        self.assertFalse(lobby_queue.empty())
        queued_message = lobby_queue.get_nowait()
        self.assertEqual(queued_message, message)

    async def test_route_messages_integration(self) -> None:
        """Test full routing flow."""
        # Set up mock client to return messages
        messages = [
            ">battle-gen9ou-12345\n|turn|1",
            "|pm|User1|User2|Hello",
            ">battle-gen9ou-67890\n|turn|2",
        ]
        self.mock_client.receive_message = AsyncMock(side_effect=messages + [asyncio.CancelledError()])
        self.mock_client.is_connected = True

        # Register battle queues
        battle_queue_1: Queue[str] = Queue()
        battle_queue_2: Queue[str] = Queue()
        self.router.register_battle("battle-gen9ou-12345", battle_queue_1)
        self.router.register_battle("battle-gen9ou-67890", battle_queue_2)

        # Run routing
        try:
            await self.router.route_messages()
        except asyncio.CancelledError:
            pass

        # Verify routing
        self.assertFalse(battle_queue_1.empty())
        self.assertFalse(battle_queue_2.empty())
        self.assertFalse(self.router.get_lobby_queue().empty())

        msg1 = battle_queue_1.get_nowait()
        self.assertIn("battle-gen9ou-12345", msg1)

        msg2 = battle_queue_2.get_nowait()
        self.assertIn("battle-gen9ou-67890", msg2)

        lobby_msg = self.router.get_lobby_queue().get_nowait()
        self.assertIn("|pm|", lobby_msg)

    async def test_unregistered_room_drops_message(self) -> None:
        """Test that messages for unregistered rooms are dropped."""
        # Don't register any rooms
        message = ">battle-gen9ou-12345\n|turn|1"

        # This should not raise, just log a warning
        self.router._route_to_battle("battle-gen9ou-12345", message)  # noqa: SLF001

        # No queues should have received the message
        self.assertTrue(self.router.get_lobby_queue().empty())

    def test_stop(self) -> None:
        """Test stopping the router."""
        self.router.stop()
        self.assertFalse(self.router._running)  # noqa: SLF001


if __name__ == "__main__":
    absltest.main()
