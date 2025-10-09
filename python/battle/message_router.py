"""Message router for distributing WebSocket messages to battle-specific queues."""

import threading
from queue import Queue
from typing import Any, Dict, Optional

from absl import logging


class MessageRouter:
    """Routes messages from a shared ShowdownClient to battle-specific queues.

    The MessageRouter runs in the main async loop and continuously reads messages
    from the ShowdownClient. It parses the room ID from messages (format: >ROOMID)
    and dispatches them to the appropriate battle queue. Messages without a room ID
    (lobby messages) are sent to a special lobby queue.
    """

    def __init__(self, client: Any) -> None:
        """Initialize the message router.

        Args:
            client: ShowdownClient instance to read messages from
        """
        self._client = client
        self._battle_queues: Dict[str, Queue[str]] = {}
        self._lobby_queue: Queue[str] = Queue()
        self._lock: threading.Lock = threading.Lock()
        self._running: bool = False

    def register_battle(self, room_id: str, message_queue: Queue[str]) -> None:
        """Register a battle room to receive messages.

        Args:
            room_id: Battle room ID (e.g., "battle-gen9ou-12345")
            message_queue: Queue to send messages to
        """
        with self._lock:
            self._battle_queues[room_id] = message_queue
            logging.info(f"[MessageRouter] Registered battle: {room_id}")

    def unregister_battle(self, room_id: str) -> None:
        """Unregister a battle room when it completes.

        Args:
            room_id: Battle room ID to remove
        """
        with self._lock:
            if room_id in self._battle_queues:
                del self._battle_queues[room_id]
                logging.info(f"[MessageRouter] Unregistered battle: {room_id}")

    def get_lobby_queue(self) -> Queue[str]:
        """Get the queue for lobby messages (challenges, PMs, etc.).

        Returns:
            Queue that receives all non-battle messages
        """
        return self._lobby_queue

    async def route_messages(self) -> None:
        """Main routing loop - continuously reads and routes messages.

        This should be run as an asyncio task. It will run until the client
        disconnects or stop() is called.
        """
        self._running = True
        logging.info("[MessageRouter] Starting message routing loop")

        try:
            while self._running and self._client.is_connected:
                try:
                    raw_message = await self._client.receive_message()
                except Exception as e:
                    logging.error(f"[MessageRouter] Error receiving message: {e}")
                    break

                if not raw_message.strip():
                    continue

                # Parse room ID from message
                room_id = self._parse_room_id(raw_message)

                # Route to appropriate queue
                if room_id:
                    self._route_to_battle(room_id, raw_message)
                else:
                    self._route_to_lobby(raw_message)

        except Exception as e:
            logging.error(f"[MessageRouter] Fatal error in routing loop: {e}")
        finally:
            logging.info("[MessageRouter] Message routing loop ended")

    def stop(self) -> None:
        """Stop the routing loop."""
        self._running = False
        logging.info("[MessageRouter] Stopping message router")

    def _parse_room_id(self, raw_message: str) -> Optional[str]:
        """Parse room ID from the message.

        Messages are formatted as:
            >ROOMID
            |message1
            |message2
            ...

        Args:
            raw_message: Raw message from server

        Returns:
            Room ID if present, None for lobby messages
        """
        lines = raw_message.split("\n")
        if lines and lines[0].startswith(">"):
            return lines[0][1:].strip()
        return None

    def _route_to_battle(self, room_id: str, raw_message: str) -> None:
        """Route message to a specific battle queue.

        Args:
            room_id: Battle room ID
            raw_message: Raw message to route
        """
        with self._lock:
            queue = self._battle_queues.get(room_id)

        if queue:
            queue.put(raw_message)
            logging.debug(f"[MessageRouter] Routed message to {room_id}")
        else:
            logging.warning(
                f"[MessageRouter] No queue registered for room {room_id}, "
                "message dropped"
            )

    def _route_to_lobby(self, raw_message: str) -> None:
        """Route message to the lobby queue.

        Args:
            raw_message: Raw message to route
        """
        self._lobby_queue.put(raw_message)
        logging.debug("[MessageRouter] Routed message to lobby")
