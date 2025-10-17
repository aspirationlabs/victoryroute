"""Agent for simulating all possible action pairs in a Pokemon battle turn."""

from typing import Any, AsyncGenerator, List, Optional
from dataclasses import replace

from absl import logging
from google.adk.agents import BaseAgent, InvocationContext
from google.adk.events import Event
from google.genai.types import Content, Part

from python.agents.tools.battle_simulator import BattleSimulator
from python.agents.turn_predictor.simulation_result import (
    SimulationResult,
)
from python.agents.turn_predictor.turn_predictor_state import (
    OpponentPokemonPrediction,
)
from python.game.interface.battle_action import ActionType
from python.game.schema.battle_state import BattleState
from python.game.schema.field_state import FieldState
from python.game.schema.pokemon_state import PokemonMove, PokemonState


class ActionSimulationAgent(BaseAgent):
    """Computes projected outcomes for each action pair using the BattleSimulator."""

    def __init__(self, name: str, battle_simulator: BattleSimulator):
        super().__init__(name=name)
        self._simulator = battle_simulator

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Main agent execution that simulates all action combinations."""
        # InvocationContext.state is dynamically added in ADK framework
        state: Any = ctx.state  # type: ignore[attr-defined]
        our_player_id = state.our_player_id
        opponent_player_id = "p2" if our_player_id == "p1" else "p1"

        our_actions = state.available_actions

        if not state.opponent_predicted_active_pokemon:
            yield Event(
                author="ActionSimulationAgent",
                content=Content(
                    role="model",
                    parts=[Part(text="Error: No opponent prediction available")],
                ),
            )
            return

        battle_state = state.battle_state
        our_active_pokemon = battle_state.get_active_pokemon(our_player_id)
        if not our_active_pokemon:
            yield Event(
                author="ActionSimulationAgent",
                content=Content(
                    role="model",
                    parts=[Part(text="Error: No active Pokemon for our player")],
                ),
            )
            return

        opponent_switches = self._get_opponent_switches(
            battle_state, opponent_player_id
        )

        # We've already checked that opponent_predicted_active_pokemon exists
        opponent_active_pokemon = self._build_opponent_pokemon_state(
            battle_state,
            state.opponent_predicted_active_pokemon,
            opponent_player_id,
        )

        field_state = battle_state.field_state
        simulation_results = []
        move_move_results = 0
        move_switch_results = 0
        switch_move_results = 0
        switch_switch_results = 0
        for our_action in our_actions:
            if our_action.action_type == ActionType.MOVE:
                for move_prediction in state.opponent_predicted_active_pokemon.moves:
                    result = await self._simulate_move_vs_move(
                        our_pokemon=our_active_pokemon,
                        our_move=our_action.move_name,
                        our_tera=our_action.tera,
                        opponent_pokemon=opponent_active_pokemon,
                        opponent_move=move_prediction.name,
                        field_state=field_state,
                        our_player_id=our_player_id,
                        opponent_player_id=opponent_player_id,
                    )
                    simulation_results.append(result)
                    move_move_results += 1
                for switch_target in opponent_switches:
                    result = await self._simulate_move_vs_switch(
                        our_pokemon=our_active_pokemon,
                        our_move=our_action.move_name,
                        our_tera=our_action.tera,
                        opponent_switching_to=switch_target,
                        field_state=field_state,
                        our_player_id=our_player_id,
                        opponent_player_id=opponent_player_id,
                    )
                    simulation_results.append(result)
                    move_switch_results += 1
            elif our_action.action_type == ActionType.SWITCH:
                our_switch_target = self._get_switch_target(
                    battle_state, our_player_id, our_action.switch_pokemon_name
                )
                if not our_switch_target:
                    continue
                for move_prediction in state.opponent_predicted_active_pokemon.moves:
                    result = await self._simulate_switch_vs_move(
                        our_switching_to=our_switch_target,
                        opponent_pokemon=opponent_active_pokemon,
                        opponent_move=move_prediction.name,
                        field_state=field_state,
                        our_player_id=our_player_id,
                        opponent_player_id=opponent_player_id,
                    )
                    switch_move_results += 1
                    simulation_results.append(result)
                for switch_target in opponent_switches:
                    result = await self._simulate_switch_vs_switch(
                        our_switching_to=our_switch_target,
                        opponent_switching_to=switch_target,
                        our_player_id=our_player_id,
                        opponent_player_id=opponent_player_id,
                    )
                    switch_switch_results += 1
                    simulation_results.append(result)
        ctx.state["simulation_actions"] = simulation_results  # type: ignore[attr-defined]
        logging.info(
            f"Action simulator found {move_move_results} move-move, {move_switch_results} move-switch, {switch_move_results} switch-move, {switch_switch_results} switch-switch results."
        )
        yield Event(
            author="ActionSimulationAgent",
            content=Content(
                role="model",
                parts=[
                    Part(text=f"Simulation complete: {len(simulation_results)} results")
                ],
            ),
        )

    def _get_opponent_switches(
        self, battle_state: BattleState, opponent_player_id: str
    ) -> List[PokemonState]:
        """Get list of valid switch targets for opponent."""
        opponent_team = battle_state.teams.get(opponent_player_id)
        if not opponent_team:
            return []

        switches = []
        for pokemon in opponent_team.pokemon:
            # Skip if fainted or currently active
            if not pokemon.is_alive() or pokemon.is_active:
                continue
            switches.append(pokemon)

        return switches

    def _build_opponent_pokemon_state(
        self,
        battle_state: BattleState,
        opponent_predicted: OpponentPokemonPrediction,
        opponent_player_id: str,
    ) -> PokemonState:
        current_active: Optional[PokemonState] = battle_state.get_active_pokemon(
            opponent_player_id
        )
        if not current_active:
            raise ValueError("No active Pokemon for opponent")
        predicted_moves = [
            # TODO: Get max pp from game data
            PokemonMove(name=move.name, current_pp=5, max_pp=5)
            for move in opponent_predicted.moves
        ]
        return replace(
            current_active,
            moves=predicted_moves,
            item=opponent_predicted.item,
            ability=opponent_predicted.ability,
            tera_type=opponent_predicted.tera_type,
        )

    def _get_switch_target(
        self, battle_state: BattleState, player_id: str, pokemon_name: str
    ) -> Optional[PokemonState]:
        team = battle_state.teams.get(player_id)
        if not team:
            return None
        for pokemon in team.pokemon:
            if pokemon.species == pokemon_name or pokemon.nickname == pokemon_name:
                return pokemon
        return None

    async def _simulate_move_vs_move(
        self,
        our_pokemon: PokemonState,  # noqa: ARG002
        our_move: str,  # noqa: ARG002
        our_tera: bool,  # noqa: ARG002
        opponent_pokemon: PokemonState,  # noqa: ARG002
        opponent_move: str,  # noqa: ARG002
        field_state: FieldState,  # noqa: ARG002
        our_player_id: str,  # noqa: ARG002
        opponent_player_id: str,  # noqa: ARG002
    ) -> SimulationResult:
        """Simulate both Pokemon using moves."""
        # TODO: Implement full simulation logic
        # 1. Determine move order using self._simulator.get_move_order
        # 2. Simulate first move using self._simulator.estimate_move_result
        # 3. Check if target faints (knockout_probability)
        # 4. If not, simulate second move
        # 5. Calculate final outcomes and create PokemonOutcome for each player
        raise NotImplementedError("_simulate_move_vs_move not yet implemented")

    async def _simulate_move_vs_switch(
        self,
        our_pokemon: PokemonState,  # noqa: ARG002
        our_move: str,  # noqa: ARG002
        our_tera: bool,  # noqa: ARG002
        opponent_switching_to: PokemonState,  # noqa: ARG002
        field_state: FieldState,  # noqa: ARG002
        our_player_id: str,  # noqa: ARG002
        opponent_player_id: str,  # noqa: ARG002
    ) -> SimulationResult:
        """Simulate our move while opponent switches."""
        # TODO: Implement simulation logic
        # 1. Opponent switches first (no damage)
        # 2. Our move targets the new Pokemon
        # 3. Calculate outcomes
        raise NotImplementedError("_simulate_move_vs_switch not yet implemented")

    async def _simulate_switch_vs_move(
        self,
        our_switching_to: PokemonState,  # noqa: ARG002
        opponent_pokemon: PokemonState,  # noqa: ARG002
        opponent_move: str,  # noqa: ARG002
        field_state: FieldState,  # noqa: ARG002
        our_player_id: str,  # noqa: ARG002
        opponent_player_id: str,  # noqa: ARG002
    ) -> SimulationResult:
        """Simulate us switching while opponent uses move."""
        # TODO: Implement simulation logic
        # 1. We switch first (no damage)
        # 2. Opponent's move targets our new Pokemon
        # 3. Calculate outcomes
        raise NotImplementedError("_simulate_switch_vs_move not yet implemented")

    async def _simulate_switch_vs_switch(
        self,
        our_switching_to: PokemonState,  # noqa: ARG002
        opponent_switching_to: PokemonState,  # noqa: ARG002
        our_player_id: str,  # noqa: ARG002
        opponent_player_id: str,  # noqa: ARG002
    ) -> SimulationResult:
        """Simulate both players switching."""
        # TODO: Implement simulation logic
        # 1. Both players switch (no damage exchanged)
        # 2. Create outcomes with no damage
        raise NotImplementedError("_simulate_switch_vs_switch not yet implemented")
