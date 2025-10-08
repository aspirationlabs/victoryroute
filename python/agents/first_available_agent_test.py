"""Unit tests for FirstAvailableAgent."""

import unittest
from dataclasses import replace
from typing import List

from python.agents.first_available_agent import FirstAvailableAgent
from python.game.data.game_data import GameData
from python.game.interface.battle_action import ActionType, BattleAction
from python.game.schema.battle_state import BattleState
from python.game.schema.pokemon_state import PokemonMove, PokemonState
from python.game.schema.team_state import TeamState


class FirstAvailableAgentTest(unittest.IsolatedAsyncioTestCase):
    """Test FirstAvailableAgent functionality."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.agent = FirstAvailableAgent()
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
        pokemon_moves = [PokemonMove(name=move, current_pp=10, max_pp=10) for move in available_moves]

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

    async def test_agent_returns_first_move(self) -> None:
        """Test that agent returns first move when moves are available."""
        state = self._create_test_state(["move1", "move2", "move3", "move4"])

        action = await self.agent.choose_action(state, self.game_data)

        self.assertIsInstance(action, BattleAction)
        self.assertEqual(action.action_type, ActionType.MOVE)
        self.assertEqual(action.move_index, 0)

    async def test_agent_returns_first_switch_when_no_moves(self) -> None:
        """Test that agent returns first switch when only switches available."""
        state = BattleState(available_moves=[], available_switches=[1, 2, 3, 4, 5])

        action = await self.agent.choose_action(state, self.game_data)

        self.assertIsInstance(action, BattleAction)
        self.assertEqual(action.action_type, ActionType.SWITCH)
        self.assertEqual(action.switch_index, 1)

    async def test_agent_chooses_first_move_consistently(self) -> None:
        """Test that agent consistently chooses first move across multiple calls."""
        state = self._create_test_state(
            ["thunderbolt", "earthquake", "protect", "volt switch"]
        )

        # Call multiple times and verify consistency
        action1 = await self.agent.choose_action(state, self.game_data)
        action2 = await self.agent.choose_action(state, self.game_data)
        action3 = await self.agent.choose_action(state, self.game_data)

        self.assertEqual(action1.move_index, 0)
        self.assertEqual(action2.move_index, 0)
        self.assertEqual(action3.move_index, 0)

    async def test_agent_with_force_switch(self) -> None:
        """Test agent behavior when force switch is required."""
        state = BattleState(
            available_moves=["move1", "move2"],
            available_switches=[0, 2, 4],
            force_switch=True,
        )

        action = await self.agent.choose_action(state, self.game_data)

        self.assertEqual(action.action_type, ActionType.SWITCH)
        self.assertEqual(action.switch_index, 0)

    async def test_agent_raises_error_when_no_actions_available(self) -> None:
        """Test that agent raises error when no actions are available."""
        state = BattleState(available_moves=[], available_switches=[])

        with self.assertRaises(ValueError) as context:
            await self.agent.choose_action(state, self.game_data)

        self.assertIn("switch", str(context.exception).lower())

    async def test_agent_raises_error_on_force_switch_with_no_switches(self) -> None:
        """Test error when force switch is true but no switches available."""
        state = BattleState(
            available_moves=["move1"], available_switches=[], force_switch=True
        )

        with self.assertRaises(ValueError):
            await self.agent.choose_action(state, self.game_data)

    async def test_agent_never_mega_evolves(self) -> None:
        """Test that agent never chooses to mega evolve."""
        state = self._create_test_state(["move1", "move2"])
        state = replace(state, can_mega=True)

        action = await self.agent.choose_action(state, self.game_data)

        self.assertEqual(action.action_type, ActionType.MOVE)
        self.assertEqual(action.move_index, 0)
        self.assertFalse(action.mega)

    async def test_agent_never_terastallizes(self) -> None:
        """Test that agent never chooses to terastallize."""
        state = self._create_test_state(["move1", "move2"])
        state = replace(state, can_tera=True)

        action = await self.agent.choose_action(state, self.game_data)

        self.assertEqual(action.action_type, ActionType.MOVE)
        self.assertEqual(action.move_index, 0)
        self.assertFalse(action.tera)

    async def test_agent_never_uses_mega_or_tera_when_both_available(self) -> None:
        """Test that agent never uses mega or tera even when both are available."""
        state = self._create_test_state(["move1", "move2"])
        state = replace(state, can_mega=True, can_tera=True)

        action = await self.agent.choose_action(state, self.game_data)

        self.assertEqual(action.action_type, ActionType.MOVE)
        self.assertEqual(action.move_index, 0)
        self.assertFalse(action.mega)
        self.assertFalse(action.tera)

    async def test_agent_with_single_move(self) -> None:
        """Test agent with only one available move."""
        state = self._create_test_state(["tackle"])

        action = await self.agent.choose_action(state, self.game_data)

        self.assertEqual(action.action_type, ActionType.MOVE)
        self.assertEqual(action.move_index, 0)

    async def test_agent_with_single_switch(self) -> None:
        """Test agent with only one available switch."""
        state = BattleState(available_moves=[], available_switches=[3])

        action = await self.agent.choose_action(state, self.game_data)

        self.assertEqual(action.action_type, ActionType.SWITCH)
        self.assertEqual(action.switch_index, 3)

    async def test_agent_prefers_move_over_switch(self) -> None:
        """Test that agent prefers moves over switches when both available."""
        state = self._create_test_state(
            available_moves=["move1", "move2"], available_switches=[1, 2, 3]
        )

        action = await self.agent.choose_action(state, self.game_data)

        # Should always pick move when available and not forced to switch
        self.assertEqual(action.action_type, ActionType.MOVE)
        self.assertEqual(action.move_index, 0)

    async def test_agent_ignores_switch_order_when_picking_first(self) -> None:
        """Test that agent picks first element from available_switches list."""
        # Test with different switch orderings
        state1 = BattleState(available_moves=[], available_switches=[5, 3, 1])
        action1 = await self.agent.choose_action(state1, self.game_data)
        self.assertEqual(action1.switch_index, 5)

        state2 = BattleState(available_moves=[], available_switches=[0, 1, 2])
        action2 = await self.agent.choose_action(state2, self.game_data)
        self.assertEqual(action2.switch_index, 0)

        state3 = BattleState(available_moves=[], available_switches=[4])
        action3 = await self.agent.choose_action(state3, self.game_data)
        self.assertEqual(action3.switch_index, 4)

    async def test_agent_deterministic_across_different_states(self) -> None:
        """Test that agent behavior is deterministic for the same state."""
        state = self._create_test_state(["move1", "move2", "move3"])

        # Same state should always produce same result
        actions = [
            await self.agent.choose_action(state, self.game_data) for _ in range(10)
        ]

        # All actions should be identical
        for action in actions:
            self.assertEqual(action.action_type, ActionType.MOVE)
            self.assertEqual(action.move_index, 0)
            self.assertFalse(action.mega)
            self.assertFalse(action.tera)


if __name__ == "__main__":
    unittest.main()
