"""First available move agent that always picks the first valid action."""

from python.agents.agent_interface import Agent
from python.game.data.game_data import GameData
from python.game.interface.battle_action import ActionType, BattleAction
from python.game.schema.battle_state import BattleState


class FirstAvailableAgent(Agent):
    """Agent that always picks the first available move or switch.

    This agent implements the simplest possible strategy:
    - If moves are available: always pick the first move (index 0)
    - If only switches are available: always pick the first available switch

    This deterministic behavior makes this agent useful for:
    - Baseline comparisons (simplest possible strategy)
    - Testing and debugging (predictable, reproducible behavior)
    - Sanity checks for battle flow (ensures battles can complete)

    The agent never mega evolves or terastallizes, and does not use game data
    for decision making. It is purely a deterministic baseline agent.

    Example Usage:
        ```python
        agent = FirstAvailableAgent()
        env = BattleEnvironment(client)
        game_data = GameData()

        state = await env.reset()
        while not env.is_battle_over():
            action = await agent.choose_action(state, game_data)
            state = await env.step(action)
        ```

    Attributes:
        None - this agent has no configurable state
    """

    async def choose_action(
        self, state: BattleState, game_data: GameData, battle_room: str
    ) -> BattleAction:
        """Choose the first available action from moves or switches.

        Decision logic:
        1. If team_preview: choose first Pokemon to lead (team 1)
        2. If moves are available and not force_switch: return first move (index 0)
        3. Otherwise: return first available switch

        Args:
            state: Current battle state with available actions
            game_data: Game data (unused by this agent)
            battle_room: Battle room identifier (unused by this agent)

        Returns:
            BattleAction with first available move or switch

        Raises:
            ValueError: If no actions are available (should not happen in valid battles)

        Examples:
            First move selection:
            >>> state = BattleState(available_moves=["move1", "move2", "move3"])
            >>> action = await agent.choose_action(state, game_data)
            >>> action.action_type
            ActionType.MOVE
            >>> action.move_index
            0

            First switch when no moves:
            >>> state = BattleState(available_switches=[2, 3, 4])
            >>> action = await agent.choose_action(state, game_data)
            >>> action.action_type
            ActionType.SWITCH
            >>> action.switch_index
            2

            Forced switch:
            >>> state = BattleState(available_switches=[0, 2, 4], force_switch=True)
            >>> action = await agent.choose_action(state, game_data)
            >>> action.action_type
            ActionType.SWITCH
            >>> action.switch_index
            0
        """
        if state.team_preview:
            return BattleAction(action_type=ActionType.TEAM_ORDER, team_order="123456")

        if state.our_player_id is None:
            raise ValueError("our_player_id is not set in battle state")

        if state.force_switch or not state.available_moves:
            if not state.available_switches:
                raise ValueError("No available switches when switch is required")

            switch_index = state.available_switches[0]
            team = state.get_team(state.our_player_id)
            pokemon = team.pokemon[switch_index]
            return BattleAction(
                action_type=ActionType.SWITCH,
                switch_pokemon_name=pokemon.species,
            )

        first_move_name = state.available_moves[0]

        return BattleAction(
            action_type=ActionType.MOVE,
            move_name=first_move_name,
        )
