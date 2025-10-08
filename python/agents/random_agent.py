"""Random agent that selects random valid actions."""

import random

from python.agents.agent_interface import Agent
from python.game.data.game_data import GameData
from python.game.interface.battle_action import ActionType, BattleAction
from python.game.schema.battle_state import BattleState


class RandomAgent(Agent):
    """Agent that picks random valid actions from available options.

    This agent makes completely random decisions during battles:
    - 90% chance to pick a random move (when moves are available)
    - 10% chance to pick a random switch (when switches are available)
    - Always switches when forced or when no moves available
    - Never mega evolves or terastallizes

    The randomness makes this agent useful as:
    - A baseline for comparing other agents
    - A testing opponent for human players
    - A sanity check for battle mechanics

    This agent does not use game data for decision making and does not attempt
    to make strategic decisions. It simply picks uniformly at random from
    available actions.

    Example Usage:
        ```python
        agent = RandomAgent()
        env = BattleEnvironment(client)
        game_data = GameData()

        state = await env.reset()
        while not env.is_battle_over():
            action = await agent.choose_action(state, game_data)
            state = await env.step(action)
        ```

    Attributes:
        switch_probability: Probability of choosing switch over move (default 0.1)
    """

    def __init__(
        self,
        switch_probability: float = 0.1,
    ) -> None:
        """Initialize RandomAgent with customizable probabilities.

        Args:
            switch_probability: Probability (0-1) of choosing switch over move
                               when both are available (default 0.1)
        """
        self.switch_probability = switch_probability

    async def choose_action(
        self, state: BattleState, game_data: GameData
    ) -> BattleAction:
        """Choose a random action from available moves and switches.

        Decision logic:
        1. If force_switch or no moves available: pick random switch
        2. Otherwise: 90% chance pick random move, 10% chance pick random switch

        Args:
            state: Current battle state with available actions
            game_data: Game data (unused by this agent)

        Returns:
            BattleAction with randomly selected move or switch

        Raises:
            ValueError: If no actions are available (should not happen in valid battles)

        Examples:
            Random move selection:
            >>> state = BattleState(available_moves=["move1", "move2", "move3"])
            >>> action = await agent.choose_action(state, game_data)
            >>> action.action_type == ActionType.MOVE
            True
            >>> 0 <= action.move_index < 3
            True

            Forced switch:
            >>> state = BattleState(available_switches=[0, 2, 4], force_switch=True)
            >>> action = await agent.choose_action(state, game_data)
            >>> action.action_type == ActionType.SWITCH
            True
        """
        if state.force_switch or not state.available_moves:
            if not state.available_switches:
                raise ValueError("No available switches when switch is required")

            switch_index = random.choice(state.available_switches)
            return BattleAction(
                action_type=ActionType.SWITCH,
                switch_index=switch_index,
            )

        should_switch = (
            state.available_switches and random.random() < self.switch_probability
        )

        if should_switch:
            switch_index = random.choice(state.available_switches)
            return BattleAction(
                action_type=ActionType.SWITCH,
                switch_index=switch_index,
            )

        move_index = random.randint(0, len(state.available_moves) - 1)

        return BattleAction(
            action_type=ActionType.MOVE,
            move_index=move_index,
        )
