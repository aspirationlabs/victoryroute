"""Unit tests for RandomAgent."""

import unittest
from typing import List
from unittest.mock import patch

from python.agents.random_agent import RandomAgent
from python.game.data.game_data import GameData
from python.game.interface.battle_action import ActionType, BattleAction
from python.game.schema.battle_state import BattleState
from python.game.schema.pokemon_state import PokemonMove, PokemonState
from python.game.schema.team_state import TeamState


class RandomAgentTest(unittest.IsolatedAsyncioTestCase):
    """Test RandomAgent functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.agent = RandomAgent()
        self.game_data = GameData()

    def _create_test_state(
        self, available_moves: List[str], available_switches: List[int] = []
    ) -> BattleState:
        """Create a test battle state with Pokemon that have the specified moves.

        Args:
            available_moves: List of move names that should be available
            available_switches: List of switch indices

        Returns:
            BattleState with proper Pokemon setup
        """
        # Create moves for the active Pokemon (all moves, not just available)
        pokemon_moves = [
            PokemonMove(name=move, current_pp=10, max_pp=10) for move in available_moves
        ]

        # Create active Pokemon with those moves
        active_pokemon = PokemonState(
            species="TestMon",
            moves=pokemon_moves,
            is_active=True,
            current_hp=100,
            max_hp=100,
        )

        # Create team with active Pokemon at index 0
        team = TeamState(pokemon=[active_pokemon], active_pokemon_index=0)

        return BattleState(
            p1_team=team,
            available_moves=available_moves,
            available_switches=available_switches,
        )

    async def test_random_agent_returns_move_action(self) -> None:
        """Test that agent returns move action when moves are available."""
        state = self._create_test_state(["move1", "move2", "move3", "move4"])

        # Mock random to always choose move (not switch)
        with patch(
            "python.agents.random_agent.random.random", return_value=0.5
        ):  # > switch_probability
            with patch(
                "python.agents.random_agent.random.choice", return_value="move3"
            ):
                action = await self.agent.choose_action(state, self.game_data)

        self.assertIsInstance(action, BattleAction)
        self.assertEqual(action.action_type, ActionType.MOVE)
        self.assertEqual(action.move_index, 2)

    async def test_random_agent_returns_switch_action_when_no_moves(self) -> None:
        """Test that agent returns switch action when only switches available."""
        state = BattleState(available_moves=[], available_switches=[1, 2, 3, 4, 5])

        with patch("python.agents.random_agent.random.choice", return_value=3):
            action = await self.agent.choose_action(state, self.game_data)

        self.assertIsInstance(action, BattleAction)
        self.assertEqual(action.action_type, ActionType.SWITCH)
        self.assertEqual(action.switch_index, 3)

    async def test_random_agent_sometimes_chooses_switch_over_move(self) -> None:
        """Test that agent can choose switch even when moves are available."""
        state = BattleState(
            available_moves=["move1", "move2"], available_switches=[1, 2, 3]
        )

        # Mock random to choose switch (< switch_probability)
        with patch(
            "python.agents.random_agent.random.random", return_value=0.05
        ):  # < 0.1
            with patch("python.agents.random_agent.random.choice", return_value=2):
                action = await self.agent.choose_action(state, self.game_data)

        self.assertEqual(action.action_type, ActionType.SWITCH)
        self.assertEqual(action.switch_index, 2)

    async def test_random_agent_with_force_switch(self) -> None:
        """Test agent behavior when force switch is required."""
        state = BattleState(
            available_moves=["move1", "move2"],
            available_switches=[0, 2, 4],
            force_switch=True,
        )

        with patch("python.agents.random_agent.random.choice", return_value=2):
            action = await self.agent.choose_action(state, self.game_data)

        self.assertEqual(action.action_type, ActionType.SWITCH)
        self.assertEqual(action.switch_index, 2)

    async def test_random_agent_raises_error_when_no_actions_available(self) -> None:
        """Test that agent raises error when no actions are available."""
        state = BattleState(available_moves=[], available_switches=[])

        with self.assertRaises(ValueError) as context:
            await self.agent.choose_action(state, self.game_data)

        self.assertIn("switch", str(context.exception).lower())

    async def test_random_agent_raises_error_on_force_switch_with_no_switches(
        self,
    ) -> None:
        """Test error when force switch is true but no switches available."""
        state = BattleState(
            available_moves=["move1"], available_switches=[], force_switch=True
        )

        with self.assertRaises(ValueError):
            await self.agent.choose_action(state, self.game_data)

    async def test_random_agent_produces_varied_results(self) -> None:
        """Test that agent produces different results across multiple calls."""
        state = self._create_test_state(
            available_moves=["move1", "move2", "move3", "move4"],
            available_switches=[0, 1, 2, 3, 4, 5],
        )

        # Collect results from multiple calls
        results = []
        for _ in range(100):
            action = await self.agent.choose_action(state, self.game_data)
            results.append((action.action_type, action.move_index, action.switch_index))

        # Check that we got at least some variety (not all the same)
        unique_results = set(results)
        self.assertGreater(
            len(unique_results), 1, "Agent should produce varied results"
        )

        # Check that we got at least some moves
        move_count = sum(1 for r in results if r[0] == ActionType.MOVE)
        self.assertGreater(move_count, 0, "Agent should choose moves sometimes")

    async def test_random_agent_custom_probabilities(self) -> None:
        """Test RandomAgent with custom switch probability."""
        # Agent that switches 50% of the time
        agent = RandomAgent(switch_probability=0.5)
        state = BattleState(
            available_moves=["move1", "move2"], available_switches=[1, 2, 3]
        )

        # Mock random to be just below switch probability
        with patch("python.agents.random_agent.random.random", return_value=0.49):
            with patch("python.agents.random_agent.random.choice", return_value=2):
                action = await agent.choose_action(state, self.game_data)

        self.assertEqual(action.action_type, ActionType.SWITCH)
        self.assertEqual(action.switch_index, 2)

    async def test_random_agent_all_move_indices_can_be_selected(self) -> None:
        """Test that all move indices can potentially be selected."""
        state = self._create_test_state(["move1", "move2", "move3", "move4"])

        # Test each possible move index by mocking the move name choice
        move_names = ["move1", "move2", "move3", "move4"]
        for expected_index, move_name in enumerate(move_names):
            with patch(
                "python.agents.random_agent.random.random", return_value=0.5
            ):  # choose move
                with patch(
                    "python.agents.random_agent.random.choice",
                    return_value=move_name,
                ):
                    action = await self.agent.choose_action(state, self.game_data)

            self.assertEqual(action.move_index, expected_index)

    async def test_random_agent_all_switch_indices_can_be_selected(self) -> None:
        """Test that all switch indices can potentially be selected."""
        state = BattleState(available_moves=[], available_switches=[0, 1, 2, 3, 4, 5])

        # Test each possible switch index
        for expected_index in [0, 1, 2, 3, 4, 5]:
            with patch(
                "python.agents.random_agent.random.choice", return_value=expected_index
            ):
                action = await self.agent.choose_action(state, self.game_data)

            self.assertEqual(action.switch_index, expected_index)


if __name__ == "__main__":
    unittest.main()
