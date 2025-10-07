"""WebSocket client for connecting to Pokemon Showdown servers."""

import json
from typing import Any, Optional

import httpx
import websockets
from absl import logging


class ShowdownClient:
    """Client for connecting to and communicating with Pokemon Showdown servers."""

    def __init__(self) -> None:
        self._ws: Optional[Any] = None
        self._server_url: str = ""
        self._username: str = ""
        self._authenticated: bool = False

    async def connect(self, server_url: str, username: str, password: str = "") -> None:
        """Connect to the Showdown server and authenticate.

        Args:
            server_url: WebSocket URL (e.g., ws://localhost:8000/showdown/websocket)
            username: Username to log in with
            password: Password for the account (empty string for guests)
        """
        self._server_url = server_url
        self._username = username

        logging.info("Connecting to %s as %s", server_url, username)
        self._ws = await websockets.connect(server_url)
        logging.info("WebSocket connection established")

        await self._authenticate(username, password)

    async def _authenticate(self, username: str, password: str) -> None:
        """Handle authentication flow with the server."""
        challstr = await self._wait_for_challstr()
        logging.info("Received challstr: %s", challstr)

        if not password:
            logging.info("No password provided, logging in as guest")
            await self.send_message(f"|/trn {username},0")
        else:
            assertion = await self._get_assertion(username, password, challstr)
            logging.info("Received assertion token")
            await self.send_message(f"|/trn {username},0,{assertion}")

        logging.info("Sent authentication command")

        while True:
            login_response = await self.receive_message()
            if "|updateuser|" in login_response:
                self._authenticated = True
                logging.info("Successfully authenticated as %s", username)
                break

        await self.send_message("|/join lobby")
        logging.info("Joined lobby")

    async def _wait_for_challstr(self) -> str:
        """Wait for and extract the challstr from the server."""
        while True:
            message = await self.receive_message()
            if "|challstr|" in message:
                parts = message.split("|challstr|")
                return parts[1].strip()
        raise RuntimeError("Failed to receive challstr from server")

    async def _get_assertion(self, username: str, password: str, challstr: str) -> str:
        """Get assertion token from the login server."""
        login_url = "https://play.pokemonshowdown.com/action.php"

        form_data = {
            "act": "login",
            "name": username,
            "pass": password,
            "challstr": challstr,
        }

        logging.info("Sending login request with name=%s to %s", username, login_url)
        async with httpx.AsyncClient() as client:
            response = await client.post(login_url, data=form_data)
            response_text = response.text
            if response_text.startswith("]"):
                response_text = response_text[1:]
            response_json = json.loads(response_text)
            if "assertion" not in response_json:
                error_msg = response_json.get("actionsuccess") or response_json
                raise ValueError(f"Login failed: {error_msg}")
            return response_json["assertion"]

    async def send_message(self, message: str) -> None:
        """Send a message to the server."""
        if self._ws is None:
            raise RuntimeError("Not connected to server")
        assert self._ws is not None
        await self._ws.send(message)

    async def receive_message(self) -> str:
        """Receive a message from the server."""
        if self._ws is None:
            raise RuntimeError("Not connected to server")
        assert self._ws is not None
        message = await self._ws.recv()
        return str(message)

    async def disconnect(self) -> None:
        """Close the WebSocket connection."""
        if self._ws is not None:
            assert self._ws is not None
            await self._ws.close()
            logging.info("Disconnected from server")
            self._ws = None
            self._authenticated = False

    @property
    def is_connected(self) -> bool:
        """Check if the client is connected."""
        return self._ws is not None

    @property
    def is_authenticated(self) -> bool:
        """Check if the client is authenticated."""
        return self._authenticated
