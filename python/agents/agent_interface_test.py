"""Unit tests for Agent interface."""

import unittest

from python.agents.agent_interface import Agent
from python.game.data.game_data import GameData
from python.game.interface.battle_action import ActionType, BattleAction
from python.game.schema.battle_state import BattleState


class FirstMoveAgent(Agent):
    """Test agent that picks the first move or first switch.

    This simple agent always picks the first available move if moves are available,
    otherwise picks the first available switch. This makes tests deterministic.
    """

    async def choose_action(
        self, state: BattleState, game_data: GameData
    ) -> BattleAction:
        """Choose first move or first switch from available options."""
        if state.available_moves:
            return BattleAction(action_type=ActionType.MOVE, move_index=0)

        if state.available_switches:
            return BattleAction(
                action_type=ActionType.SWITCH, switch_index=state.available_switches[0]
            )

        raise ValueError("No available moves or switches")


class AgentInterfaceTest(unittest.IsolatedAsyncioTestCase):
    """Test Agent interface functionality."""

    def test_cannot_instantiate_abstract_agent(self) -> None:
        """Test that Agent abstract class cannot be instantiated directly."""
        with self.assertRaises(TypeError) as context:
            Agent()  # type: ignore
        self.assertIn("abstract", str(context.exception).lower())

    def test_concrete_agent_can_be_instantiated(self) -> None:
        """Test that concrete agent implementation can be instantiated."""
        agent = FirstMoveAgent()
        self.assertIsInstance(agent, Agent)
        self.assertIsInstance(agent, FirstMoveAgent)

    async def test_agent_returns_move_action(self) -> None:
        """Test that agent returns move action when moves are available."""
        agent = FirstMoveAgent()
        game_data = GameData()

        state = BattleState(available_moves=["move1", "move2", "move3", "move4"])

        action = await agent.choose_action(state, game_data)

        self.assertIsInstance(action, BattleAction)
        self.assertEqual(action.action_type, ActionType.MOVE)
        self.assertEqual(action.move_index, 0)

    async def test_agent_returns_switch_action_when_no_moves(self) -> None:
        """Test that agent returns switch action when only switches available."""
        agent = FirstMoveAgent()
        game_data = GameData()

        state = BattleState(available_moves=[], available_switches=[1, 2, 3, 4, 5])

        action = await agent.choose_action(state, game_data)

        self.assertIsInstance(action, BattleAction)
        self.assertEqual(action.action_type, ActionType.SWITCH)
        self.assertEqual(action.switch_index, 1)

    async def test_agent_chooses_first_move_consistently(self) -> None:
        """Test that agent consistently chooses first move."""
        agent = FirstMoveAgent()
        game_data = GameData()
        state = BattleState(
            available_moves=["thunderbolt", "earthquake", "protect", "volt switch"]
        )

        action1 = await agent.choose_action(state, game_data)
        action2 = await agent.choose_action(state, game_data)
        action3 = await agent.choose_action(state, game_data)

        self.assertEqual(action1.move_index, 0)
        self.assertEqual(action2.move_index, 0)
        self.assertEqual(action3.move_index, 0)

    async def test_agent_with_force_switch(self) -> None:
        """Test agent behavior when force switch is required."""
        agent = FirstMoveAgent()
        game_data = GameData()

        state = BattleState(
            available_moves=[],
            available_switches=[0, 2, 4],
            force_switch=True,
        )

        action = await agent.choose_action(state, game_data)

        self.assertEqual(action.action_type, ActionType.SWITCH)
        self.assertEqual(action.switch_index, 0)

    async def test_agent_raises_error_when_no_actions_available(self) -> None:
        """Test that agent raises error when no actions are available."""
        agent = FirstMoveAgent()
        game_data = GameData()

        state = BattleState(available_moves=[], available_switches=[])

        with self.assertRaises(ValueError):
            await agent.choose_action(state, game_data)


if __name__ == "__main__":
    unittest.main()
