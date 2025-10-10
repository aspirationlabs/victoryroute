"""Abstract base class for battle agents."""

from abc import ABC, abstractmethod
from typing import Optional

from python.game.environment.battle_stream_store import BattleStreamStore
from python.game.interface.battle_action import BattleAction
from python.game.schema.battle_state import BattleState


class Agent(ABC):
    """Abstract base class for all battle agents.

    All agents must implement the choose_action method, which receives the current
    battle state and game data, and returns a valid battle action. The agent is
    responsible for selecting actions from the available moves and switches in the
    battle state.

    The agent interface follows these design principles:

    1. **Immutable State**: Agents receive an immutable BattleState snapshot and
       should not attempt to modify it. Each turn produces a new state.

    2. **Available Actions**: The BattleState contains available_moves and
       available_switches lists that represent legal actions. Agents should
       choose from these options. No validation is performed - agents are
       trusted to pick valid actions.

    3. **Game Data Access**: Agents have access to GameData for looking up
       Pokemon stats, move information, abilities, items, natures, and type
       effectiveness. This data is immutable and shared across all agents.

    4. **Async Interface**: All agents must implement choose_action as an async
       method to support async I/O operations (e.g., LLM API calls, network
       requests, file I/O).

    Example Implementation:
        ```python
        class RandomAgent(Agent):
            async def choose_action(
                self, state: BattleState, game_data: GameData
            ) -> BattleAction:
                # Pick random move or switch
                if state.available_moves and random.random() > 0.1:
                    move_index = random.choice(range(len(state.available_moves)))
                    return BattleAction(
                        action_type=ActionType.MOVE,
                        move_index=move_index
                    )
                else:
                    switch_index = random.choice(state.available_switches)
                    return BattleAction(
                        action_type=ActionType.SWITCH,
                        switch_index=switch_index
                    )
        ```

    Example Usage:
        ```python
        # Initialize agent and environment
        agent = RandomAgent()
        env = BattleEnvironment(client)
        game_data = GameData()

        # Main battle loop
        state = await env.reset()
        while not env.is_battle_over():
            # Agent chooses action based on current state
            action = await agent.choose_action(state, game_data)

            # Execute action and get next state
            state = await env.step(action)
        ```

    Attributes:
        None - subclasses may define their own attributes (e.g., model, config)

    Methods:
        choose_action: Abstract method that all agents must implement
        retry_action_on_server_error: Optional method for handling server errors
    """

    @abstractmethod
    async def choose_action(
        self,
        state: BattleState,
        battle_room: str,
        battle_stream_store: Optional[BattleStreamStore] = None,
    ) -> BattleAction:
        """Choose a battle action based on the current state.

        This is the core method that defines an agent's behavior. Given the
        current battle state, the agent must return a valid battle action.

        The agent should:
        1. Analyze the current battle state (active Pokemon, field conditions, etc.)
        2. Query game data for relevant information (move power, type effectiveness, etc.)
        3. Select a move from state.available_moves or a switch from state.available_switches
        4. Return a BattleAction with the chosen action

        No validation is performed on the returned action - the agent is responsible
        for ensuring the action is valid (i.e., picking from available options).

        Args:
            state: Immutable snapshot of the current battle state, including:
                - Both teams' Pokemon (HP, status, stat boosts, etc.)
                - Field conditions (weather, terrain, side conditions)
                - Available actions (moves, switches, mega/tera flags)
            battle_room: The battle room identifier (e.g., "battle-gen9ou-12345")
            battle_stream_store: Optional store containing all battle events seen
                               so far, for accessing historical battle actions

        Returns:
            A BattleAction representing the agent's chosen action. This will be
            sent to the Showdown server and executed in the battle.

        Raises:
            Any exceptions raised by the agent implementation. The battle
            environment may catch and handle these (e.g., retry, forfeit).

        Examples:
            Simple move selection:
            >>> action = await agent.choose_action(state, game_data)
            >>> action.action_type
            ActionType.MOVE
            >>> action.move_index
            0

            Forced switch (after faint):
            >>> if state.force_switch:
            ...     action = await agent.choose_action(state, game_data)
            ...     assert action.action_type == ActionType.SWITCH

            Mega Evolution:
            >>> if state.can_mega:
            ...     action = BattleAction(
            ...         action_type=ActionType.MOVE,
            ...         move_index=0,
            ...         mega=True
            ...     )
        """
        pass

    async def retry_action_on_server_error(
        self,
        error_text: str,
        state: BattleState,
        battle_room: str,
        battle_stream_store: Optional[BattleStreamStore] = None,
    ) -> Optional[BattleAction]:
        """Handle a server error and optionally retry with a new action.

        This method is called when the Pokemon Showdown server returns an error
        after an action is sent. The agent can analyze the error and decide
        whether to retry with a different action.

        The default implementation returns None (don't retry). Agents can override
        this to implement retry logic.

        Args:
            error_text: The error message from the server
            state: Current battle state (same state that was used for the failed action)
            battle_room: The battle room identifier
            battle_stream_store: Optional store containing all battle events

        Returns:
            A new BattleAction to retry, or None to give up and re-raise the error.

        Examples:
            No retry (default):
            >>> retry_action = await agent.retry_action_on_server_error(
            ...     "Invalid move", state, battle_room
            ... )
            >>> retry_action is None
            True

            Retry with new action:
            >>> retry_action = await agent.retry_action_on_server_error(
            ...     "Move locked by choice item", state, battle_room
            ... )
            >>> retry_action.action_type
            ActionType.SWITCH
        """
        return None
