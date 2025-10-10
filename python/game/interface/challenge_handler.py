"""Challenge handler for accepting and sending Pokemon Showdown challenges."""

import asyncio
from typing import Any, Dict, Optional

from absl import logging

from python.game.events.battle_event import PopupEvent, PrivateMessageEvent
from python.game.protocol.message_parser import MessageParser


class ChallengeHandler:
    """Handles challenge workflow for Pokemon Showdown battles."""

    def __init__(
        self,
        client: Any,
        format: str = "gen9ou",
        opponent: Optional[str] = None,
        challenge_timeout: int = 120,
        team_data: Optional[str] = None,
    ) -> None:
        """Initialize the challenge handler.

        Args:
            client: ShowdownClient instance with send_message and receive_message
            format: Battle format (e.g., 'gen9ou', 'gen9vgc2024regh')
            opponent: Optional opponent username filter (case insensitive)
            challenge_timeout: Timeout in seconds before sending proactive challenge
            team_data: Packed team data to send before accepting/sending challenges
        """
        self._client = client
        self._format = format
        self._opponent = opponent.lower() if opponent else None
        self._challenge_timeout = challenge_timeout
        self._team_data = team_data
        self._parser = MessageParser()
        self._pending_challenges: Dict[str, str] = {}
        self._accepted_battle: Optional[str] = None
        self._timeout_task: Optional[asyncio.Task[None]] = None

    async def listen_for_challenges(self) -> str:
        """Listen for challenges and handle them according to configuration.

        Returns:
            Battle room ID when a challenge is accepted

        Raises:
            RuntimeError: If client is not connected
        """
        # Reset battle state for each new challenge round
        self._accepted_battle = None

        if self._opponent and self._challenge_timeout > 0:
            self._timeout_task = asyncio.create_task(self._handle_challenge_timeout())

        try:
            while self._client.is_connected:
                raw_message = await self._client.receive_message()
                logging.debug("Received raw message: %s", raw_message[:200])

                if not raw_message.strip():
                    continue

                for line in raw_message.split("\n"):
                    if not line.strip():
                        continue

                    logging.debug("Processing line: %s", line[:100])

                    # Check for battle room join
                    if line.startswith(">battle-"):
                        battle_room = line[1:].strip()
                        logging.info("Joined battle room: %s", battle_room)
                        self._accepted_battle = battle_room
                        if self._timeout_task:
                            self._timeout_task.cancel()
                        return self._accepted_battle

                    event = self._parser.parse(line)

                    if isinstance(event, PrivateMessageEvent):
                        logging.debug(
                            "Received PM from %s: %s", event.sender, event.message
                        )
                        await self._handle_pm(event)
                    elif isinstance(event, PopupEvent):
                        logging.warning("Server popup:\n%s", event.popup_text)
                        logging.debug("Raw popup message: %s", event.raw_message)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error("Error while listening for challenges: %s", e)
            raise

        raise RuntimeError("Client disconnected before challenge accepted")

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
                "Ignoring challenge from %s with format %s (expected %s)",
                challenger,
                challenge_format,
                self._format,
            )
            return

        if self._should_accept_challenge(challenger):
            logging.info("Accepting challenge from %s", challenger)

            # Send team before accepting (as per Showdown protocol)
            if self._team_data:
                logging.info("Sending team before accepting challenge...")
                await self._client.send_message(f"|/utm {self._team_data}")

                # Give server a moment to process the team
                await asyncio.sleep(0.1)

            await self.accept_challenge(challenger)

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

    def _should_accept_challenge(self, challenger: str) -> bool:
        """Check if we should accept a challenge from this user.

        Args:
            challenger: Normalized challenger username

        Returns:
            True if challenge should be accepted
        """
        if not self._opponent:
            return True

        return challenger == self._opponent

    async def accept_challenge(self, username: str) -> None:
        """Accept a challenge from a specific user.

        Args:
            username: Username of the challenger
        """
        await self._client.send_message(f"|/accept {username}")
        self._pending_challenges[username] = username
        logging.info("Sent accept command for challenge from %s", username)

    async def send_challenge(self, username: str) -> None:
        """Send a challenge to a specific user.

        Args:
            username: Username to challenge
        """
        # Send team before challenging (as per Showdown protocol)
        if self._team_data:
            logging.info("Sending team before challenging...")
            await self._client.send_message(f"|/utm {self._team_data}")

            # Give server a moment to process the team
            await asyncio.sleep(0.1)

        await self._client.send_message(f"|/challenge {username}, {self._format}")
        logging.info("Sent challenge to %s with format %s", username, self._format)

    async def _handle_challenge_timeout(self) -> None:
        """Handle challenge timeout by sending proactive challenge."""
        try:
            logging.debug(
                "Challenge timeout task started, waiting %s seconds",
                self._challenge_timeout,
            )
            await asyncio.sleep(self._challenge_timeout)

            if self._opponent and not self._accepted_battle:
                logging.info(
                    "Challenge timeout reached, sending challenge to %s",
                    self._opponent,
                )
                await self.send_challenge(self._opponent)
            else:
                logging.debug(
                    "Timeout reached but not sending challenge (opponent=%s, accepted=%s)",
                    self._opponent,
                    self._accepted_battle,
                )
        except asyncio.CancelledError:
            logging.debug("Challenge timeout task cancelled")

    def get_battle_room(self) -> Optional[str]:
        """Get the accepted battle room ID.

        Returns:
            Battle room ID if a battle was accepted, None otherwise
        """
        return self._accepted_battle
