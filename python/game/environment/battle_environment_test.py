"""Tests for BattleEnvironment."""

import unittest
from typing import List

from python.game.environment.battle_environment import BattleEnvironment
from python.game.interface.battle_action import ActionType, BattleAction
from python.game.schema.battle_state import BattleState


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
        self.sent_messages: List[str] = []

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

    async def send_message(self, message: str) -> None:
        """Record sent message.

        Args:
            message: Message to send
        """
        self.sent_messages.append(message)


class BattleEnvironmentTest(unittest.IsolatedAsyncioTestCase):
    """Tests for BattleEnvironment class."""

    def test_initialization(self) -> None:
        """Test environment initialization."""
        client = FakeShowdownClient([])
        env = BattleEnvironment(client, track_history=False)

        self.assertIsNotNone(env)
        # Uninitialized state has battle_over=False by default
        self.assertFalse(env.is_battle_over())

    def test_initialization_with_history_tracking(self) -> None:
        """Test environment initialization with history tracking."""
        client = FakeShowdownClient([])
        env = BattleEnvironment(client, track_history=True)

        self.assertIsNotNone(env)
        # History should be empty before reset
        self.assertEqual([], env.get_history())

    async def test_reset_initializes_state(self) -> None:
        """Test that reset() initializes battle state from events."""
        messages = [
            # Battle start with team preview
            "|player|p1|Player1|",
            "|player|p2|Player2|",
            "|teamsize|p1|6",
            "|teamsize|p2|6",
            # Switch events for initial Pokemon
            "|switch|p1a: Pikachu|Pikachu, L50, M|100/100",
            "|switch|p2a: Charizard|Charizard, L50, M|100/100",
            # First request event
            '|request|{"active":[{"moves":[{"move":"Thunder Shock"}]}],"side":{"pokemon":[{"active":true,"condition":"100/100"}]}}',
        ]

        client = FakeShowdownClient(messages)
        env = BattleEnvironment(client)

        state = await env.reset()

        # Verify state was initialized
        self.assertIsNotNone(state)
        self.assertEqual(state, env.get_state())

        # Verify available actions were parsed from request
        self.assertEqual(["Thunder Shock"], state.available_moves)

    async def test_reset_with_history_tracking(self) -> None:
        """Test that reset() adds initial state to history."""
        messages = [
            "|switch|p1a: Pikachu|Pikachu, L50, M|100/100",
            '|request|{"active":[{"moves":[{"move":"Thunder Shock"}]}],"side":{"pokemon":[{"active":true,"condition":"100/100"}]}}',
        ]

        client = FakeShowdownClient(messages)
        env = BattleEnvironment(client, track_history=True)

        state = await env.reset()

        # History should contain initial state
        history = env.get_history()
        self.assertEqual(1, len(history))
        self.assertEqual(state, history[0])

    async def test_reset_raises_on_empty_stream(self) -> None:
        """Test that reset() raises error if stream ends before first request."""
        client = FakeShowdownClient([])
        env = BattleEnvironment(client)

        with self.assertRaises(RuntimeError):
            await env.reset()

    async def test_get_state_returns_current_state(self) -> None:
        """Test that get_state() returns current immutable state."""
        messages = [
            "|switch|p1a: Pikachu|Pikachu, L50, M|100/100",
            '|request|{"active":[{"moves":[{"move":"Thunder Shock"}]}],"side":{"pokemon":[{"active":true,"condition":"100/100"}]}}',
        ]

        client = FakeShowdownClient(messages)
        env = BattleEnvironment(client)

        state1 = await env.reset()
        state2 = env.get_state()

        # Should return same state
        self.assertEqual(state1, state2)

    def test_is_battle_over_false_when_not_ended(self) -> None:
        """Test that is_battle_over() returns False when battle_over is False."""
        client = FakeShowdownClient([])
        env = BattleEnvironment(client)

        # Create state with battle not over
        env._state = BattleState(battle_over=False)

        self.assertFalse(env.is_battle_over())

    def test_is_battle_over_true_when_ended(self) -> None:
        """Test that is_battle_over() returns True when battle_over is True."""
        client = FakeShowdownClient([])
        env = BattleEnvironment(client)

        # Create state with battle over
        env._state = BattleState(battle_over=True, winner="Player1")

        self.assertTrue(env.is_battle_over())

    def test_is_battle_over_true_for_tie(self) -> None:
        """Test that is_battle_over() returns True for a tie."""
        client = FakeShowdownClient([])
        env = BattleEnvironment(client)

        # Create state with tie (battle over, no winner)
        env._state = BattleState(battle_over=True, winner="")

        self.assertTrue(env.is_battle_over())

    def test_get_history_raises_when_not_tracking(self) -> None:
        """Test that get_history() raises error when tracking is disabled."""
        client = FakeShowdownClient([])
        env = BattleEnvironment(client, track_history=False)

        with self.assertRaises(ValueError):
            env.get_history()

    async def test_step_sends_action_and_updates_state(self) -> None:
        """Test that step() sends action and updates state with new events."""
        # Setup initial state
        reset_messages = [
            "|switch|p1a: Pikachu|Pikachu, L50, M|100/100",
            "|switch|p2a: Charizard|Charizard, L50, M|100/100",
            '|request|{"active":[{"moves":[{"move":"Thunder Shock"}]}],"side":{"pokemon":[{"active":true,"condition":"100/100"}]}}',
        ]

        # Events after action
        action_response = [
            "|move|p1a: Pikachu|Thunder Shock|p2a: Charizard",
            "|-damage|p2a: Charizard|80/100",
            "|move|p2a: Charizard|Flamethrower|p1a: Pikachu",
            "|-damage|p1a: Pikachu|70/100",
            '|request|{"active":[{"moves":[{"move":"Thunder Shock"}]}],"side":{"pokemon":[{"active":true,"condition":"70/100"}]}}',
        ]

        all_messages = reset_messages + action_response
        client = FakeShowdownClient(all_messages)
        env = BattleEnvironment(client)

        # Initialize battle
        initial_state = await env.reset()
        self.assertEqual(["Thunder Shock"], initial_state.available_moves)

        # Execute action
        action = BattleAction(action_type=ActionType.MOVE, move_index=0)
        new_state = await env.step(action)

        # Verify action was sent (with battle room prefix)
        self.assertEqual(1, len(client.sent_messages))
        self.assertEqual("test|/choose move 1", client.sent_messages[0])

        # Verify state was updated
        self.assertEqual(new_state, env.get_state())
        self.assertNotEqual(initial_state, new_state)

    async def test_step_with_history_tracking(self) -> None:
        """Test that step() appends states to history."""
        reset_messages = [
            "|switch|p1a: Pikachu|Pikachu, L50, M|100/100",
            '|request|{"active":[{"moves":[{"move":"Thunder Shock"}]}],"side":{"pokemon":[{"active":true,"condition":"100/100"}]}}',
        ]

        action_response = [
            "|move|p1a: Pikachu|Thunder Shock|p2a: Charizard",
            '|request|{"active":[{"moves":[{"move":"Thunder Shock"}]}],"side":{"pokemon":[{"active":true,"condition":"100/100"}]}}',
        ]

        all_messages = reset_messages + action_response
        client = FakeShowdownClient(all_messages)
        env = BattleEnvironment(client, track_history=True)

        # Initialize and take action
        await env.reset()
        action = BattleAction(action_type=ActionType.MOVE, move_index=0)
        await env.step(action)

        # Verify history contains both states
        history = env.get_history()
        self.assertEqual(2, len(history))

    async def test_step_with_switch_action(self) -> None:
        """Test that step() handles switch actions correctly."""
        reset_messages = [
            "|switch|p1a: Pikachu|Pikachu, L50, M|100/100",
            '|request|{"active":[{"moves":[{"move":"Thunder Shock"}]}],"side":{"pokemon":[{"active":true,"condition":"100/100"},{"condition":"100/100"}]}}',
        ]

        action_response = [
            "|switch|p1a: Raichu|Raichu, L50, M|100/100",
            '|request|{"active":[{"moves":[{"move":"Thunder"}]}],"side":{"pokemon":[{"active":true,"condition":"100/100"}]}}',
        ]

        all_messages = reset_messages + action_response
        client = FakeShowdownClient(all_messages)
        env = BattleEnvironment(client)

        await env.reset()

        # Switch to second Pokemon
        action = BattleAction(action_type=ActionType.SWITCH, switch_index=1)
        await env.step(action)

        # Verify switch command was sent (1-indexed, with battle room prefix)
        self.assertEqual("test|/choose switch 2", client.sent_messages[0])

    async def test_step_raises_on_stream_end(self) -> None:
        """Test that step() raises error if stream ends unexpectedly."""
        reset_messages = [
            "|switch|p1a: Pikachu|Pikachu, L50, M|100/100",
            '|request|{"active":[{"moves":[{"move":"Thunder Shock"}]}],"side":{"pokemon":[{"active":true,"condition":"100/100"}]}}',
        ]

        # No action response - stream will end
        client = FakeShowdownClient(reset_messages)
        env = BattleEnvironment(client)

        await env.reset()

        action = BattleAction(action_type=ActionType.MOVE, move_index=0)

        with self.assertRaises(RuntimeError):
            await env.step(action)

    async def test_step_raises_on_send_failure(self) -> None:
        """Test that step() raises error if sending action fails."""

        class FailingSendClient(FakeShowdownClient):
            async def send_message(self, message: str) -> None:
                raise ConnectionError("Send failed")

        reset_messages = [
            "|switch|p1a: Pikachu|Pikachu, L50, M|100/100",
            '|request|{"active":[{"moves":[{"move":"Thunder Shock"}]}],"side":{"pokemon":[{"active":true,"condition":"100/100"}]}}',
        ]

        client = FailingSendClient(reset_messages)
        env = BattleEnvironment(client)

        await env.reset()

        action = BattleAction(action_type=ActionType.MOVE, move_index=0)

        with self.assertRaises(RuntimeError):
            await env.step(action)

    async def test_multiple_turns(self) -> None:
        """Test that multiple step() calls work correctly."""
        reset_messages = [
            "|switch|p1a: Pikachu|Pikachu, L50, M|100/100",
            '|request|{"active":[{"moves":[{"move":"Thunder Shock"}]}],"side":{"pokemon":[{"active":true,"condition":"100/100"}]}}',
        ]

        turn1_response = [
            "|move|p1a: Pikachu|Thunder Shock|p2a: Charizard",
            '|request|{"active":[{"moves":[{"move":"Thunder Shock"}]}],"side":{"pokemon":[{"active":true,"condition":"100/100"}]}}',
        ]

        turn2_response = [
            "|move|p1a: Pikachu|Thunder Shock|p2a: Charizard",
            '|request|{"active":[{"moves":[{"move":"Thunder Shock"}]}],"side":{"pokemon":[{"active":true,"condition":"100/100"}]}}',
        ]

        all_messages = reset_messages + turn1_response + turn2_response
        client = FakeShowdownClient(all_messages)
        env = BattleEnvironment(client, track_history=True)

        # Initialize and take two actions
        await env.reset()
        action = BattleAction(action_type=ActionType.MOVE, move_index=0)
        await env.step(action)
        await env.step(action)

        # Verify both actions were sent
        self.assertEqual(2, len(client.sent_messages))

        # Verify history has 3 states (initial + 2 turns)
        history = env.get_history()
        self.assertEqual(3, len(history))


if __name__ == "__main__":
    unittest.main()
