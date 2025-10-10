"""Battle environment orchestrator for managing battle lifecycle."""

from typing import Any, List, Optional

from absl import logging

from python.game.environment.battle_stream_store import BattleStreamStore
from python.game.environment.state_transition import StateTransition
from python.game.interface.battle_action import BattleAction
from python.game.protocol.battle_event_logger import BattleEventLogger
from python.game.protocol.battle_stream import BattleStream
from python.game.schema.battle_state import BattleState


class BattleEnvironment:
    """Main orchestrator that manages battle lifecycle and state updates.

    The BattleEnvironment is responsible for:
    - Managing the current immutable BattleState
    - Receiving event batches from BattleStream
    - Applying events via StateTransition to create new states
    - Sending actions to ShowdownClient
    - Optionally tracking state history for replay/debugging

    Example usage:
        ```python
        # Initialize environment
        client = ShowdownClient()
        await client.connect(server_url, username, password)
        env = BattleEnvironment(client)

        # Battle loop
        state = await env.reset()
        while not env.is_battle_over():
            action = await agent.choose_action(state, game_data)
            state = await env.step(action)
        ```

    Attributes:
        _client: Client for sending actions (any object with send_message method)
        _stream: BattleStream for receiving event batches
        _state: Current immutable BattleState
        _track_history: Whether to maintain state history
        _history: List of all historical states (if tracking enabled)
    """

    def __init__(
        self,
        client: Any,
        battle_room: Optional[str] = None,
        track_history: bool = False,
        logger: Optional["BattleEventLogger"] = None,
    ) -> None:
        """Initialize the battle environment.

        Args:
            client: Connected client instance (e.g., ShowdownClient) with
                   is_connected, receive_message(), and send_message() methods
            battle_room: Battle room ID (e.g., "battle-gen9ou-12345").
                        Optional for testing; required for production use.
            track_history: Whether to maintain history of all states (default: False)
            logger: Optional BattleEventLogger to log events to file
        """
        self._client = client
        self._battle_room = battle_room or "test"
        self._stream = BattleStream(
            client, mode="live", battle_id=battle_room, logger=logger
        )
        self._state = BattleState()
        self._track_history = track_history
        self._history: List[BattleState] = []
        self._battle_stream_store = BattleStreamStore()

    async def reset(self) -> BattleState:
        """Initialize battle state by waiting for battle start events.

        Collects events until the first RequestEvent (agent's turn to act),
        applies all events to build the initial battle state.

        Returns:
            Initial BattleState with team info and available actions

        Raises:
            StopAsyncIteration: If stream ends before first request
            RuntimeError: If battle initialization fails
        """
        logging.info("[%s] Waiting for battle to start...", self._battle_room)

        # Get first batch of events (until first RequestEvent)
        try:
            event_batch = await self._stream.__anext__()
        except StopAsyncIteration:
            raise RuntimeError("Battle stream ended before initialization")

        logging.info(
            "[%s] Received %d initialization events",
            self._battle_room,
            len(event_batch),
        )

        # Add events to battle stream store
        self._battle_stream_store.add_events(event_batch)

        # Apply all events to build initial state
        current_state = BattleState()
        for event in event_batch:
            current_state = StateTransition.apply(current_state, event)

        self._state = current_state

        # Add initial state to history if tracking
        if self._track_history:
            self._history = [current_state]

        logging.info(
            "[%s] Battle initialized, ready for first action", self._battle_room
        )
        return current_state

    def get_state(self) -> BattleState:
        """Get current immutable battle state.

        Returns:
            Current BattleState snapshot
        """
        return self._state

    def is_battle_over(self) -> bool:
        """Check if the battle has concluded.

        A battle is over when the server sends a |win| or |tie| message.

        Returns:
            True if battle is complete, False otherwise
        """
        return self._state.battle_over

    def get_history(self) -> List[BattleState]:
        """Get history of all battle states.

        Returns:
            List of all BattleState snapshots in chronological order

        Raises:
            ValueError: If history tracking is not enabled
        """
        if not self._track_history:
            raise ValueError(
                "History tracking is not enabled. "
                "Initialize BattleEnvironment with track_history=True"
            )
        return list(self._history)

    async def step(self, action: BattleAction) -> BattleState:
        """Execute an action and advance the battle to the next decision point.

        This method:
        1. Converts action to Showdown protocol command
        2. Sends command to server via ShowdownClient
        3. Collects all events until next RequestEvent
        4. Applies all events via StateTransition
        5. Updates internal state
        6. Optionally appends to history
        7. Returns new state

        Args:
            action: BattleAction to execute (from agent)

        Returns:
            New BattleState after action and all resulting events

        Raises:
            RuntimeError: If client disconnected or stream ended
            ValueError: If action conversion or state transition fails
        """
        try:
            command = action.to_showdown_command()
        except Exception as e:
            raise ValueError(f"Failed to convert action to command: {e}") from e

        message = f"{self._battle_room}|{command}"
        logging.debug("[%s] Sending action: %s", self._battle_room, command)
        try:
            await self._client.send_message(message)
        except Exception as e:
            raise RuntimeError(f"Failed to send action to server: {e}") from e

        try:
            event_batch = await self._stream.__anext__()
        except StopAsyncIteration:
            raise RuntimeError(
                "Battle stream ended unexpectedly. "
                "Check if battle concluded or connection lost."
            )

        logging.debug(
            "[%s] Received %d events from action", self._battle_room, len(event_batch)
        )

        # Add events to battle stream store
        self._battle_stream_store.add_events(event_batch)

        current_state = self._state
        for event in event_batch:
            try:
                current_state = StateTransition.apply(current_state, event)
            except Exception as e:
                logging.error(
                    "[%s] Failed to apply event %s: %s", self._battle_room, event, e
                )
                raise ValueError(f"State transition failed: {e}") from e

        self._state = current_state

        if self._track_history:
            self._history.append(current_state)

        return current_state

    async def wait_for_next_state(self) -> BattleState:
        """Wait for the next state update without sending an action.

        Used when we receive a "wait" request and need to wait for opponent's action.

        Returns:
            New BattleState after opponent's action completes

        Raises:
            RuntimeError: If stream ends unexpectedly
        """
        logging.debug("[%s] Waiting for opponent's action...", self._battle_room)

        try:
            event_batch = await self._stream.__anext__()
        except StopAsyncIteration:
            raise RuntimeError(
                "Battle stream ended while waiting for opponent. "
                "Check if battle concluded or connection lost."
            )

        logging.info(
            "[%s] Received %d events from opponent's action",
            self._battle_room,
            len(event_batch),
        )

        # Add events to battle stream store
        self._battle_stream_store.add_events(event_batch)

        current_state = self._state
        for event in event_batch:
            try:
                current_state = StateTransition.apply(current_state, event)
            except Exception as e:
                logging.error(
                    "[%s] Failed to apply event %s: %s", self._battle_room, event, e
                )
                raise ValueError(f"State transition failed: {e}") from e

        self._state = current_state

        if self._track_history:
            self._history.append(current_state)

        return current_state

    def get_battle_stream_store(self) -> BattleStreamStore:
        """Get the battle stream store containing all events seen so far.

        Returns:
            BattleStreamStore with all battle events processed up to this point
        """
        return self._battle_stream_store
