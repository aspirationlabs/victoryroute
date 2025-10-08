"""Tests for ChallengeHandler."""

import unittest
from typing import List

from absl.testing import absltest, parameterized

from python.game.interface.challenge_handler import ChallengeHandler


class FakeShowdownClient:
    """Fake ShowdownClient for testing ChallengeHandler."""

    def __init__(self, messages: List[str], message_delay: float = 0.0) -> None:
        """Initialize with a list of messages to return.

        Args:
            messages: List of raw protocol messages
            message_delay: Optional delay in seconds before returning each message
        """
        self._messages = messages
        self._index = 0
        self._sent_messages: List[str] = []
        self._message_delay = message_delay
        self.is_connected = True

    async def receive_message(self) -> str:
        """Return next message from the list.

        Returns:
            Next message in the list

        Raises:
            IndexError: If no more messages available
        """
        import asyncio

        if self._message_delay > 0:
            await asyncio.sleep(self._message_delay)

        if self._index >= len(self._messages):
            self.is_connected = False
            raise IndexError("No more messages")

        message = self._messages[self._index]
        self._index += 1
        return message

    async def send_message(self, message: str) -> None:
        """Record sent message.

        Args:
            message: Message to send
        """
        self._sent_messages.append(message)

    def get_sent_messages(self) -> List[str]:
        """Get list of sent messages.

        Returns:
            List of messages sent via send_message
        """
        return self._sent_messages


class ChallengeHandlerTest(unittest.IsolatedAsyncioTestCase, parameterized.TestCase):
    """Tests for ChallengeHandler."""

    async def test_accept_challenge_basic(self) -> None:
        """Test accepting a basic challenge."""
        messages = [
            "|pm|~Challenger| BotPlayer|/challenge gen9ou",
            ">battle-gen9ou-12345",
        ]

        client = FakeShowdownClient(messages)
        handler = ChallengeHandler(client, format="gen9ou")

        battle_room = await handler.listen_for_challenges()

        self.assertEqual(battle_room, "battle-gen9ou-12345")
        sent_messages = client.get_sent_messages()
        self.assertEqual(len(sent_messages), 1)
        self.assertEqual(sent_messages[0], "|/accept challenger")

    async def test_ignore_wrong_format(self) -> None:
        """Test that challenges with wrong format are ignored."""
        messages = [
            "|pm|~Challenger| BotPlayer|/challenge gen9vgc2024regh",
            "|pm|~CorrectChallenger| BotPlayer|/challenge gen9ou",
            ">battle-gen9ou-12345",
        ]

        client = FakeShowdownClient(messages)
        handler = ChallengeHandler(client, format="gen9ou")

        battle_room = await handler.listen_for_challenges()

        self.assertEqual(battle_room, "battle-gen9ou-12345")
        sent_messages = client.get_sent_messages()
        self.assertEqual(len(sent_messages), 1)
        self.assertEqual(sent_messages[0], "|/accept correctchallenger")

    async def test_ignore_non_challenge_pms(self) -> None:
        """Test that non-challenge PMs are ignored."""
        messages = [
            "|pm| FriendlyUser| BotPlayer|Hello!",
            "|pm| AnotherUser| BotPlayer|How are you?",
            "|pm|~Challenger| BotPlayer|/challenge gen9ou",
            ">battle-gen9ou-12345",
        ]

        client = FakeShowdownClient(messages)
        handler = ChallengeHandler(client, format="gen9ou")

        battle_room = await handler.listen_for_challenges()

        self.assertEqual(battle_room, "battle-gen9ou-12345")
        sent_messages = client.get_sent_messages()
        self.assertEqual(len(sent_messages), 1)
        self.assertEqual(sent_messages[0], "|/accept challenger")

    @parameterized.parameters(
        ("~Username", "username"),
        ("+VoiceUser", "voiceuser"),
        ("@Moderator", "moderator"),
        ("#RoomOwner", "roomowner"),
        ("&Administrator", "administrator"),
        (" RegularUser", "regularuser"),
        ("NoPrefixUser", "noprefixuser"),
    )
    def test_normalize_username(
        self, input_username: str, expected_normalized: str
    ) -> None:
        """Test username normalization."""
        client = FakeShowdownClient([])
        handler = ChallengeHandler(client, format="gen9ou")

        normalized = handler._normalize_username(input_username)
        self.assertEqual(normalized, expected_normalized)

    async def test_opponent_filter_accepts_matching(self) -> None:
        """Test that opponent filter accepts matching username."""
        messages = [
            "|pm|~TargetOpponent| BotPlayer|/challenge gen9ou",
            ">battle-gen9ou-12345",
        ]

        client = FakeShowdownClient(messages)
        handler = ChallengeHandler(client, format="gen9ou", opponent="TargetOpponent")

        battle_room = await handler.listen_for_challenges()

        self.assertEqual(battle_room, "battle-gen9ou-12345")
        sent_messages = client.get_sent_messages()
        self.assertEqual(len(sent_messages), 1)
        self.assertEqual(sent_messages[0], "|/accept targetopponent")

    async def test_opponent_filter_rejects_non_matching(self) -> None:
        """Test that opponent filter rejects non-matching username."""
        messages = [
            "|pm|~WrongUser| BotPlayer|/challenge gen9ou",
            "|pm|~AnotherWrongUser| BotPlayer|/challenge gen9ou",
            "|pm|~TargetOpponent| BotPlayer|/challenge gen9ou",
            ">battle-gen9ou-12345",
        ]

        client = FakeShowdownClient(messages)
        handler = ChallengeHandler(client, format="gen9ou", opponent="TargetOpponent")

        battle_room = await handler.listen_for_challenges()

        self.assertEqual(battle_room, "battle-gen9ou-12345")
        sent_messages = client.get_sent_messages()
        self.assertEqual(len(sent_messages), 1)
        self.assertEqual(sent_messages[0], "|/accept targetopponent")

    async def test_opponent_filter_case_insensitive(self) -> None:
        """Test that opponent filter is case insensitive."""
        messages = [
            "|pm|~TARGETOPPONENT| BotPlayer|/challenge gen9ou",
            ">battle-gen9ou-12345",
        ]

        client = FakeShowdownClient(messages)
        handler = ChallengeHandler(client, format="gen9ou", opponent="targetopponent")

        battle_room = await handler.listen_for_challenges()

        self.assertEqual(battle_room, "battle-gen9ou-12345")
        sent_messages = client.get_sent_messages()
        self.assertEqual(len(sent_messages), 1)
        self.assertEqual(sent_messages[0], "|/accept targetopponent")

    async def test_challenge_timeout_sends_proactive_challenge(self) -> None:
        """Test that timeout triggers proactive challenge."""
        messages = [
            ">battle-gen9ou-12345",
        ]

        # Delay message so timeout can trigger first
        client = FakeShowdownClient(messages, message_delay=0.02)
        handler = ChallengeHandler(
            client, format="gen9ou", opponent="TargetOpponent", challenge_timeout=0.01
        )

        battle_room = await handler.listen_for_challenges()

        self.assertEqual(battle_room, "battle-gen9ou-12345")
        sent_messages = client.get_sent_messages()
        self.assertEqual(len(sent_messages), 1)
        self.assertEqual(sent_messages[0], "|/challenge targetopponent, gen9ou")

    async def test_challenge_timeout_cancelled_if_challenge_received(self) -> None:
        """Test that timeout is cancelled if challenge is received."""
        messages = [
            "|pm|~TargetOpponent| BotPlayer|/challenge gen9ou",
            ">battle-gen9ou-12345",
        ]

        client = FakeShowdownClient(messages)
        handler = ChallengeHandler(
            client, format="gen9ou", opponent="TargetOpponent", challenge_timeout=10
        )

        battle_room = await handler.listen_for_challenges()

        self.assertEqual(battle_room, "battle-gen9ou-12345")
        sent_messages = client.get_sent_messages()
        self.assertEqual(len(sent_messages), 1)
        self.assertEqual(sent_messages[0], "|/accept targetopponent")

    async def test_no_proactive_challenge_without_opponent(self) -> None:
        """Test that no proactive challenge is sent without opponent specified."""
        messages = [
            "|pm|~SomeChallenger| BotPlayer|/challenge gen9ou",
            ">battle-gen9ou-12345",
        ]

        client = FakeShowdownClient(messages)
        handler = ChallengeHandler(client, format="gen9ou", challenge_timeout=1)

        battle_room = await handler.listen_for_challenges()

        self.assertEqual(battle_room, "battle-gen9ou-12345")
        sent_messages = client.get_sent_messages()
        self.assertEqual(len(sent_messages), 1)
        self.assertEqual(sent_messages[0], "|/accept somechallenger")

    @parameterized.parameters(
        ("/challenge gen9ou", "gen9ou"),
        ("/challenge gen9vgc2024regh", "gen9vgc2024regh"),
        ("/challenge gen8ou", "gen8ou"),
        ("/challenge gen1ou", "gen1ou"),
    )
    def test_parse_challenge_format(self, message: str, expected_format: str) -> None:
        """Test parsing challenge format from message."""
        client = FakeShowdownClient([])
        handler = ChallengeHandler(client, format="gen9ou")

        parsed_format = handler._parse_challenge_format(message)
        self.assertEqual(parsed_format, expected_format)

    def test_get_battle_room_before_acceptance(self) -> None:
        """Test get_battle_room returns None before acceptance."""
        client = FakeShowdownClient([])
        handler = ChallengeHandler(client, format="gen9ou")

        self.assertIsNone(handler.get_battle_room())

    async def test_multiline_messages(self) -> None:
        """Test handling multiline messages."""
        messages = [
            "|pm|~Challenger| BotPlayer|/challenge gen9ou\n>battle-gen9ou-12345",
        ]

        client = FakeShowdownClient(messages)
        handler = ChallengeHandler(client, format="gen9ou")

        battle_room = await handler.listen_for_challenges()

        self.assertEqual(battle_room, "battle-gen9ou-12345")

    async def test_empty_messages_skipped(self) -> None:
        """Test that empty messages are skipped."""
        messages = [
            "",
            "\n",
            "|pm|~Challenger| BotPlayer|/challenge gen9ou",
            "  ",
            ">battle-gen9ou-12345",
        ]

        client = FakeShowdownClient(messages)
        handler = ChallengeHandler(client, format="gen9ou")

        battle_room = await handler.listen_for_challenges()

        self.assertEqual(battle_room, "battle-gen9ou-12345")


if __name__ == "__main__":
    absltest.main()
