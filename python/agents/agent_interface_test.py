"""Unit tests for Agent interface."""

import unittest

from python.agents.agent_interface import Agent
from python.game.environment.battle_stream_store import BattleStreamStore
from python.game.interface.battle_action import ActionType, BattleAction
from python.game.schema.battle_state import BattleState


class FirstMoveAgent(Agent):
    """Test agent that picks the first move or first switch.

    This simple agent always picks the first available move if moves are available,
    otherwise picks the first available switch. This makes tests deterministic.
    """

    async def choose_action(self, state: BattleState) -> BattleAction:
        """Choose first move or first switch from available options."""
        if state.available_moves:
            return BattleAction(
                action_type=ActionType.MOVE, move_name=state.available_moves[0]
            )

        if state.available_switches:
            return BattleAction(
                action_type=ActionType.SWITCH, switch_pokemon_name="TestPokemon"
            )

        raise ValueError("No available moves or switches")


class AgentInterfaceTest(unittest.IsolatedAsyncioTestCase):
    """Test Agent interface functionality."""

    def test_cannot_instantiate_abstract_agent(self) -> None:
        """Test that Agent abstract class cannot be instantiated directly."""
        with self.assertRaises(TypeError) as context:
            Agent("test-room", BattleStreamStore())  # type: ignore
        self.assertIn("abstract", str(context.exception).lower())

    def test_concrete_agent_can_be_instantiated(self) -> None:
        """Test that concrete agent implementation can be instantiated."""
        agent = FirstMoveAgent("test-battle", BattleStreamStore())
        self.assertIsInstance(agent, Agent)
        self.assertIsInstance(agent, FirstMoveAgent)

    async def test_agent_returns_move_action(self) -> None:
        """Test that agent returns move action when moves are available."""
        agent = FirstMoveAgent("test-battle", BattleStreamStore())

        state = BattleState(available_moves=["move1", "move2", "move3", "move4"])

        action = await agent.choose_action(state)

        self.assertIsInstance(action, BattleAction)
        self.assertEqual(action.action_type, ActionType.MOVE)
        self.assertEqual(action.move_name, "move1")

    async def test_agent_returns_switch_action_when_no_moves(self) -> None:
        """Test that agent returns switch action when only switches available."""
        agent = FirstMoveAgent("test-battle", BattleStreamStore())

        state = BattleState(available_moves=[], available_switches=[1, 2, 3, 4, 5])

        action = await agent.choose_action(state)

        self.assertIsInstance(action, BattleAction)
        self.assertEqual(action.action_type, ActionType.SWITCH)
        self.assertEqual(action.switch_pokemon_name, "TestPokemon")

    async def test_agent_chooses_first_move_consistently(self) -> None:
        """Test that agent consistently chooses first move."""
        agent = FirstMoveAgent("test-battle", BattleStreamStore())
        state = BattleState(
            available_moves=["thunderbolt", "earthquake", "protect", "volt switch"]
        )

        action1 = await agent.choose_action(state)
        action2 = await agent.choose_action(state)
        action3 = await agent.choose_action(state)

        self.assertEqual(action1.move_name, "thunderbolt")
        self.assertEqual(action2.move_name, "thunderbolt")
        self.assertEqual(action3.move_name, "thunderbolt")

    async def test_agent_with_force_switch(self) -> None:
        """Test agent behavior when force switch is required."""
        agent = FirstMoveAgent("test-battle", BattleStreamStore())

        state = BattleState(
            available_moves=[],
            available_switches=[0, 2, 4],
            force_switch=True,
        )

        action = await agent.choose_action(state)

        self.assertEqual(action.action_type, ActionType.SWITCH)
        self.assertEqual(action.switch_pokemon_name, "TestPokemon")

    async def test_agent_raises_error_when_no_actions_available(self) -> None:
        """Test that agent raises error when no actions are available."""
        agent = FirstMoveAgent("test-battle", BattleStreamStore())

        state = BattleState(available_moves=[], available_switches=[])

        with self.assertRaises(ValueError):
            await agent.choose_action(state)


if __name__ == "__main__":
    unittest.main()
