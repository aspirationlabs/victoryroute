"""Tests for agent registry."""

import unittest

from python.agents.agent_interface import Agent
from python.agents.agent_registry import AgentRegistry
from python.agents.first_available_agent import FirstAvailableAgent
from python.agents.random_agent import RandomAgent
from python.game.environment.battle_stream_store import BattleStreamStore
from python.game.interface.battle_action import ActionType, BattleAction
from python.game.schema.battle_state import BattleState


class AgentRegistryTest(unittest.TestCase):
    """Test cases for AgentRegistry class."""

    def test_get_available_agents_returns_sorted_list(self) -> None:
        """Test that get_available_agents returns sorted agent names."""
        agents = AgentRegistry.get_available_agents()

        self.assertIsInstance(agents, list)
        self.assertEqual(agents, sorted(agents))
        self.assertIn("random", agents)
        self.assertIn("first_move", agents)

    def test_has_agent_returns_true_for_registered_agents(self) -> None:
        """Test that has_agent returns True for registered agents."""
        self.assertTrue(AgentRegistry.has_agent("random"))
        self.assertTrue(AgentRegistry.has_agent("first_move"))

    def test_has_agent_returns_false_for_unregistered_agents(self) -> None:
        """Test that has_agent returns False for unregistered agents."""
        self.assertFalse(AgentRegistry.has_agent("nonexistent"))
        self.assertFalse(AgentRegistry.has_agent("unknown_agent"))

    def test_has_agent_is_case_insensitive(self) -> None:
        """Test that has_agent is case insensitive."""
        self.assertTrue(AgentRegistry.has_agent("Random"))
        self.assertTrue(AgentRegistry.has_agent("RANDOM"))
        self.assertTrue(AgentRegistry.has_agent("First_Move"))
        self.assertTrue(AgentRegistry.has_agent("FIRST_MOVE"))

    def test_create_agent_returns_random_agent(self) -> None:
        """Test that create_agent returns RandomAgent for 'random'."""
        agent = AgentRegistry.create_agent("random", "test-battle", BattleStreamStore())

        self.assertIsInstance(agent, RandomAgent)
        self.assertIsInstance(agent, Agent)

    def test_create_agent_returns_first_available_agent(self) -> None:
        """Test that create_agent returns FirstAvailableAgent for 'first_move'."""
        agent = AgentRegistry.create_agent(
            "first_move", "test-battle", BattleStreamStore()
        )

        self.assertIsInstance(agent, FirstAvailableAgent)
        self.assertIsInstance(agent, Agent)

    def test_create_agent_is_case_insensitive(self) -> None:
        """Test that create_agent is case insensitive."""
        agent1 = AgentRegistry.create_agent(
            "Random", "test-battle", BattleStreamStore()
        )
        agent2 = AgentRegistry.create_agent(
            "RANDOM", "test-battle", BattleStreamStore()
        )
        agent3 = AgentRegistry.create_agent(
            "First_Move", "test-battle", BattleStreamStore()
        )

        self.assertIsInstance(agent1, RandomAgent)
        self.assertIsInstance(agent2, RandomAgent)
        self.assertIsInstance(agent3, FirstAvailableAgent)

    def test_create_agent_raises_value_error_for_unknown_agent(self) -> None:
        """Test that create_agent raises ValueError for unknown agents."""
        with self.assertRaises(ValueError) as context:
            AgentRegistry.create_agent(
                "unknown_agent", "test-battle", BattleStreamStore()
            )

        self.assertIn("Unknown agent", str(context.exception))
        self.assertIn("unknown_agent", str(context.exception))
        self.assertIn("Available agents", str(context.exception))

    def test_create_agent_returns_new_instances(self) -> None:
        """Test that create_agent returns new instances each time."""
        agent1 = AgentRegistry.create_agent(
            "random", "test-battle", BattleStreamStore()
        )
        agent2 = AgentRegistry.create_agent(
            "random", "test-battle", BattleStreamStore()
        )

        self.assertIsNot(agent1, agent2)

    def test_register_agent_adds_new_agent(self) -> None:
        """Test that register_agent adds a new agent to the registry."""

        class TestAgent(Agent):
            async def choose_action(self, state: BattleState) -> BattleAction:
                return BattleAction(action_type=ActionType.MOVE, move_name="testmove")

        original_agents = set(AgentRegistry.get_available_agents())

        try:
            AgentRegistry.register_agent(
                "test_agent",
                lambda battle_room, battle_stream_store: TestAgent(
                    battle_room, battle_stream_store
                ),
            )

            self.assertTrue(AgentRegistry.has_agent("test_agent"))
            self.assertIn("test_agent", AgentRegistry.get_available_agents())

            agent = AgentRegistry.create_agent(
                "test_agent", "test-battle", BattleStreamStore()
            )
            self.assertIsInstance(agent, TestAgent)
        finally:
            if "test_agent" in AgentRegistry._AGENT_MAP:
                del AgentRegistry._AGENT_MAP["test_agent"]

            current_agents = set(AgentRegistry.get_available_agents())
            self.assertEqual(original_agents, current_agents)

    def test_register_agent_raises_error_for_duplicate(self) -> None:
        """Test that register_agent raises error for duplicate names."""
        with self.assertRaises(ValueError) as context:
            AgentRegistry.register_agent(
                "random",
                lambda battle_room, battle_stream_store: RandomAgent(
                    battle_room, battle_stream_store
                ),
            )

        self.assertIn("already registered", str(context.exception))


if __name__ == "__main__":
    unittest.main()
