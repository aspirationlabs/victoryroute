"""Parallel challenge handler for managing multiple concurrent battles."""

import asyncio
import time
from queue import Queue
from typing import Any, Dict, Optional, Set

from absl import logging

from python.game.events.battle_event import PopupEvent, PrivateMessageEvent
from python.game.protocol.message_parser import MessageParser


class ParallelChallengeHandler:
    """Handles challenges for multiple concurrent battles.

    Unlike the single-battle ChallengeHandler, this version:
    - Accepts multiple challenges simultaneously (up to per-opponent limit)
    - Tracks ongoing battles to enforce limits
    - Sends challenges to multiple opponents
    - Processes lobby messages from a queue
    """

    def __init__(
        self,
        client: Any,
        coordinator: Any,
        lobby_queue: Queue[str],
        format: str = "gen9ou",
        opponent: Optional[str] = None,
        challenge_timeout: int = 120,
        team_data: Optional[str] = None,
    ) -> None:
        """Initialize the parallel challenge handler.

        Args:
            client: ShowdownClient instance
            coordinator: BattleCoordinator to check capacity
            lobby_queue: Queue for receiving lobby messages
            format: Battle format (e.g., 'gen9ou')
            opponent: Optional opponent username filter (case insensitive)
            challenge_timeout: Timeout before sending proactive challenges
            team_data: Packed team data
        """
        self._client = client
        self._coordinator = coordinator
        self._lobby_queue = lobby_queue
        self._format = format
        self._opponent = opponent.lower() if opponent else None
        self._challenge_timeout = challenge_timeout
        self._team_data = team_data
        self._parser = MessageParser()

        # Track challenge state
        self._pending_battle_rooms: Set[str] = set()
        self._challenge_sent_times: Dict[str, float] = {}
        self._last_challenge_time: float = 0.0

    async def process_lobby_messages(self) -> Optional[str]:
        """Process lobby messages and return battle room if one starts.

        This should be called regularly from the main loop.

        Returns:
            Battle room ID if a battle started, None otherwise
        """
        # Check for timeout and send challenges if needed
        if self._should_send_challenges():
            await self._send_proactive_challenges()

        # Process any waiting lobby messages
        if not self._lobby_queue.empty():
            raw_message = self._lobby_queue.get_nowait()
            return await self._process_lobby_message(raw_message)

        return None

    async def _process_lobby_message(self, raw_message: str) -> Optional[str]:
        """Process a single lobby message.

        Args:
            raw_message: Raw protocol message

        Returns:
            Battle room ID if a battle started, None otherwise
        """
        for line in raw_message.split("\n"):
            if not line.strip():
                continue

            # Check for battle room join
            if line.startswith(">battle-"):
                battle_room = line[1:].strip()
                logging.info(f"[ParallelChallengeHandler] Joined battle: {battle_room}")
                self._pending_battle_rooms.add(battle_room)
                return battle_room

            # Parse event
            event = self._parser.parse(line)

            if isinstance(event, PrivateMessageEvent):
                await self._handle_pm(event)
            elif isinstance(event, PopupEvent):
                logging.warning("Server popup:\n%s", event.popup_text)

        return None

    async def _handle_pm(self, event: PrivateMessageEvent) -> None:
        """Handle a private message event.

        Args:
            event: PrivateMessageEvent containing the PM
        """
        if not self._is_challenge_message(event.message):
            return

        challenger = self._normalize_username(event.sender)
        challenge_format = self._parse_challenge_format(event.message)

        if challenge_format != self._format:
            logging.info(
                f"Ignoring challenge from {challenger} with format {challenge_format} "
                f"(expected {self._format})"
            )
            return

        if self._should_accept_challenge(challenger):
            logging.info(f"Accepting challenge from {challenger}")
            await self._accept_challenge(challenger)
        else:
            logging.info(
                f"Cannot accept challenge from {challenger} - at capacity "
                f"({self._coordinator.get_active_battle_count(challenger)}/"
                f"{self._coordinator._battles_per_opponent})"  # noqa: SLF001
            )

    def _should_accept_challenge(self, challenger: str) -> bool:
        """Check if we should accept a challenge from this user.

        Args:
            challenger: Normalized challenger username

        Returns:
            True if challenge should be accepted
        """
        # Check opponent filter
        if self._opponent and challenger != self._opponent:
            return False

        # Check capacity
        return self._coordinator.can_start_battle(challenger)

    async def _accept_challenge(self, username: str) -> None:
        """Accept a challenge from a specific user.

        Args:
            username: Username of the challenger
        """
        # Send team before accepting (as per Showdown protocol)
        if self._team_data:
            logging.info("Sending team before accepting challenge...")
            await self._client.send_message(f"|/utm {self._team_data}")
            await asyncio.sleep(0.1)

        await self._client.send_message(f"|/accept {username}")
        logging.info(f"Sent accept command for challenge from {username}")

    async def send_challenge(self, username: str) -> None:
        """Send a challenge to a specific user.

        Args:
            username: Username to challenge
        """
        # Check if we can challenge this opponent
        if not self._coordinator.can_start_battle(username):
            logging.info(f"Cannot challenge {username} - at capacity")
            return

        # Send team before challenging (as per Showdown protocol)
        if self._team_data:
            logging.info(f"Sending team before challenging {username}...")
            await self._client.send_message(f"|/utm {self._team_data}")
            await asyncio.sleep(0.1)

        await self._client.send_message(f"|/challenge {username}, {self._format}")
        self._challenge_sent_times[username] = time.time()
        logging.info(f"Sent challenge to {username} with format {self._format}")

    def _should_send_challenges(self) -> bool:
        """Check if we should send proactive challenges.

        Returns:
            True if timeout reached and opponent specified
        """
        if not self._opponent:
            return False

        # Only send if we have capacity
        if not self._coordinator.can_start_battle(self._opponent):
            return False

        # Check timeout
        elapsed = time.time() - self._last_challenge_time
        return elapsed >= self._challenge_timeout

    async def _send_proactive_challenges(self) -> None:
        """Send proactive challenges to opponent after timeout."""
        if self._opponent:
            await self.send_challenge(self._opponent)
            self._last_challenge_time = time.time()

    def _is_challenge_message(self, message: str) -> bool:
        """Check if a message is a challenge.

        Args:
            message: Message content

        Returns:
            True if message starts with '/challenge'
        """
        return message.strip().startswith("/challenge")

    def _parse_challenge_format(self, message: str) -> str:
        """Parse the battle format from a challenge message.

        Args:
            message: Challenge message (e.g., '/challenge gen9ou')

        Returns:
            Format string (e.g., 'gen9ou')
        """
        parts = message.strip().split()
        if len(parts) >= 2:
            return parts[1].lower()
        return ""

    def _normalize_username(self, username: str) -> str:
        """Normalize a username by removing rank prefix and lowercasing.

        Args:
            username: Username possibly with rank prefix (~, +, @, etc.)

        Returns:
            Normalized lowercase username without rank prefix
        """
        username = username.strip()
        if username and username[0] in "~+@#&":
            username = username[1:]
        return username.lower()

    def remove_pending_battle(self, battle_room: str) -> None:
        """Remove a battle room from pending set.

        Args:
            battle_room: Battle room ID to remove
        """
        self._pending_battle_rooms.discard(battle_room)
