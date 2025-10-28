"""Agent for simulating all possible action pairs in a Pokemon battle turn."""

from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Optional,
    Tuple,
    Protocol,
    runtime_checkable,
)
from dataclasses import replace

from absl import logging
from google.adk.agents import BaseAgent, InvocationContext
from google.adk.events import Event
from google.genai.types import Content, Part

from python.agents.tools.battle_simulator import (
    BattleSimulator,
    EffortValues,
    MoveResult,
)
from python.agents.tools.pokemon_state_priors_reader import (
    PokemonStatePriorsReader,
)
from python.agents.turn_predictor.simulation_result import (
    PokemonOutcome,
    SimulationResult,
)
from python.agents.turn_predictor.turn_predictor_state import (
    OpponentPokemonPrediction,
    TurnPredictorState,
)
from python.game.interface.battle_action import ActionType, BattleAction
from python.game.schema.battle_state import BattleState
from python.game.schema.enums import FieldEffect, SideCondition, Weather
from python.game.schema.field_state import FieldState
from python.game.schema.pokemon_state import PokemonMove, PokemonState
from python.game.schema.team_state import TeamState


class ActionSimulationAgent(BaseAgent):
    """Computes projected outcomes for each action pair using the BattleSimulator."""

    def __init__(
        self,
        name: str,
        battle_simulator: BattleSimulator,
        priors_reader: Optional[PokemonStatePriorsReader] = None,
    ):
        super().__init__(name=name)
        self._simulator = battle_simulator
        self._priors_reader = priors_reader or PokemonStatePriorsReader()
        self._usage_spread_cache: Dict[
            str, Tuple[Optional[str], Optional[EffortValues]]
        ] = {}

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Main agent execution that simulates all action combinations."""
        raw_state: Any = ctx.state  # type: ignore[attr-defined]
        state = TurnPredictorState.model_validate(raw_state)

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
                if not our_action.move_name:
                    raise ValueError(
                        "Action type is MOVE, but move_name unset: {our_action}"
                    )
                for move_prediction in state.opponent_predicted_active_pokemon.moves:
                    result = await self._simulate_move_vs_move(
                        battle_state=battle_state,
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
                        battle_state=battle_state,
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
                if not our_action.switch_pokemon_name:
                    raise ValueError(
                        "Action type is SWITCH, but switch_pokemon_name unset: {our_action}"
                    )
                our_switch_target = self._get_switch_target(
                    battle_state, our_player_id, our_action.switch_pokemon_name
                )
                if not our_switch_target:
                    raise ValueError(
                        "No switch target found for our action: {our_action}"
                    )
                for move_prediction in state.opponent_predicted_active_pokemon.moves:
                    result = await self._simulate_switch_vs_move(
                        battle_state=battle_state,
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
                        battle_state=battle_state,
                        our_switching_to=our_switch_target,
                        opponent_switching_to=switch_target,
                        our_player_id=our_player_id,
                        opponent_player_id=opponent_player_id,
                    )
                    switch_switch_results += 1
                    simulation_results.append(result)
        if isinstance(raw_state, dict):
            raw_state["simulation_actions"] = simulation_results  # type: ignore[index]
        else:
            setattr(raw_state, "simulation_actions", simulation_results)
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

    def _get_usage_spread(
        self, pokemon: PokemonState
    ) -> Tuple[Optional[str], Optional[EffortValues]]:
        """Return the top usage nature and EVs for a given Pokemon species."""
        species = pokemon.species
        if species not in self._usage_spread_cache:
            spread = self._priors_reader.get_top_usage_spread(species)
            if not spread:
                self._usage_spread_cache[species] = (None, None)
            else:
                nature, ev_values = spread
                try:
                    evs = EffortValues(*ev_values)
                except (TypeError, ValueError):
                    evs = None
                self._usage_spread_cache[species] = (nature, evs)
        return self._usage_spread_cache[species]

    def _build_move_order_kwargs(
        self,
        *,
        prefix: str,
        nature: Optional[str],
        evs: Optional[EffortValues],
    ) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        if nature is not None:
            kwargs[f"{prefix}_nature"] = nature
        if evs is not None:
            kwargs[f"{prefix}_evs"] = evs
        return kwargs

    def _build_estimate_kwargs(
        self,
        *,
        attacker_nature: Optional[str],
        attacker_evs: Optional[EffortValues],
        defender_nature: Optional[str],
        defender_evs: Optional[EffortValues],
    ) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {}
        if attacker_nature is not None:
            kwargs["attacker_nature"] = attacker_nature
        if attacker_evs is not None:
            kwargs["attacker_evs"] = attacker_evs
        if defender_nature is not None:
            kwargs["defender_nature"] = defender_nature
        if defender_evs is not None:
            kwargs["defender_evs"] = defender_evs
        return kwargs

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

    def _maybe_terastallize_pokemon(
        self, pokemon: PokemonState, use_tera: bool
    ) -> PokemonState:
        """Return a PokemonState reflecting terastallization if requested."""
        if not use_tera:
            return pokemon
        if pokemon.has_terastallized:
            return pokemon
        return replace(pokemon, has_terastallized=True)

    def _get_move_from_pokemon(
        self, pokemon: PokemonState, move_name: str
    ) -> PokemonMove:
        """Get a PokemonMove by name, creating a placeholder if unseen."""
        for move in pokemon.moves:
            if move.name.lower() == move_name.lower():
                return move
        # Fallback: create a placeholder move with nominal PP to allow simulation.
        return PokemonMove(name=move_name, current_pp=5, max_pp=5)

    def _get_side_condition_set(self, team: TeamState) -> Optional[set[SideCondition]]:
        """Return the active side conditions for a team as a set."""
        if not team.side_conditions:
            return None
        return set(team.side_conditions.keys())

    @staticmethod
    def _hp_range_after_damage(
        current_hp: int, min_damage: int, max_damage: int
    ) -> Tuple[int, int]:
        """Compute HP range after taking damage between min_damage and max_damage."""
        min_hp = max(0, current_hp - max_damage)
        max_hp = max(0, current_hp - min_damage)
        if max_hp < min_hp:
            max_hp = min_hp
        return (min_hp, max_hp)

    @staticmethod
    def _crit_hp_range_after_damage(
        current_hp: int, crit_min_damage: int, crit_max_damage: int
    ) -> Tuple[int, int]:
        """Compute HP range after taking critical damage."""
        min_hp = max(0, current_hp - crit_max_damage)
        max_hp = max(0, current_hp - crit_min_damage)
        if max_hp < min_hp:
            max_hp = min_hp
        return (min_hp, max_hp)

    @staticmethod
    def _apply_self_inflicted_hp_changes(
        current_hp: int, max_hp: int, recoil_damage: int, drain_heal: int
    ) -> int:
        """Apply recoil and drain effects to the attacker's HP."""
        hp_after_recoil = max(0, current_hp - max(recoil_damage, 0))
        hp_after_drain = hp_after_recoil + drain_heal
        if hp_after_drain < 0:
            return 0
        if hp_after_drain > max_hp:
            return max_hp
        return hp_after_drain

    @staticmethod
    def _clamp_probability(value: float) -> float:
        """Clamp probability values into [0.0, 1.0]."""
        if value < 0.0:
            return 0.0
        if value > 1.0:
            return 1.0
        return value

    async def _simulate_move_vs_move(
        self,
        battle_state: BattleState,
        our_pokemon: PokemonState,
        our_move: str,
        our_tera: bool,
        opponent_pokemon: PokemonState,
        opponent_move: str,
        field_state: FieldState,
        our_player_id: str,
        opponent_player_id: str,
    ) -> SimulationResult:
        """Simulate both Pokemon using moves."""
        our_team = battle_state.get_team(our_player_id)
        opponent_team = battle_state.get_team(opponent_player_id)

        our_sim_pokemon = self._maybe_terastallize_pokemon(our_pokemon, our_tera)
        opponent_sim_pokemon = opponent_pokemon

        our_nature, our_evs = self._get_usage_spread(our_sim_pokemon)
        opponent_nature, opponent_evs = self._get_usage_spread(opponent_sim_pokemon)

        our_move_obj = self._get_move_from_pokemon(our_sim_pokemon, our_move)
        opponent_move_obj = self._get_move_from_pokemon(
            opponent_sim_pokemon, opponent_move
        )

        our_side_conditions = self._get_side_condition_set(our_team)
        opponent_side_conditions = self._get_side_condition_set(opponent_team)
        trick_room_active = FieldEffect.TRICK_ROOM in field_state.get_field_effects()

        move_order_kwargs: Dict[str, Any] = {}
        move_order_kwargs.update(
            self._build_move_order_kwargs(
                prefix="pokemon_1", nature=our_nature, evs=our_evs
            )
        )
        move_order_kwargs.update(
            self._build_move_order_kwargs(
                prefix="pokemon_2", nature=opponent_nature, evs=opponent_evs
            )
        )

        move_order = self._simulator.get_move_order(
            our_sim_pokemon,
            our_move_obj,
            opponent_sim_pokemon,
            opponent_move_obj,
            side_1_conditions=our_side_conditions,
            side_2_conditions=opponent_side_conditions,
            weather=field_state.get_weather() or Weather.NONE,
            terrain=field_state.get_terrain(),
            trick_room_active=trick_room_active,
            **move_order_kwargs,
        )

        player_move_order: List[str] = []
        move_results: Dict[str, Optional[MoveResult]] = {
            our_player_id: None,
            opponent_player_id: None,
        }

        first_player = (
            our_player_id
            if move_order[0].pokemon is our_sim_pokemon
            else opponent_player_id
        )

        actions = {
            our_player_id: BattleAction(
                action_type=ActionType.MOVE, move_name=our_move, tera=our_tera
            ),
            opponent_player_id: BattleAction(
                action_type=ActionType.MOVE, move_name=opponent_move
            ),
        }

        if first_player == our_player_id:
            first_estimate_kwargs = self._build_estimate_kwargs(
                attacker_nature=our_nature,
                attacker_evs=our_evs,
                defender_nature=opponent_nature,
                defender_evs=opponent_evs,
            )
            first_result = self._simulator.estimate_move_result(
                our_sim_pokemon,
                opponent_sim_pokemon,
                our_move_obj,
                field_state,
                list(opponent_side_conditions) if opponent_side_conditions else None,
                **first_estimate_kwargs,
            )
            move_results[our_player_id] = first_result
            player_move_order.append(our_player_id)

            our_post_move_hp = self._apply_self_inflicted_hp_changes(
                our_sim_pokemon.current_hp,
                our_sim_pokemon.max_hp,
                first_result.recoil_damage,
                first_result.drain_heal,
            )
            our_self_fainted = our_post_move_hp == 0

            opponent_survival = self._clamp_probability(
                1.0 - first_result.knockout_probability
            )

            second_result: Optional[MoveResult] = None
            if opponent_survival > 0 and not our_self_fainted:
                defender_after_self_damage = replace(
                    our_sim_pokemon, current_hp=our_post_move_hp
                )
                second_estimate_kwargs = self._build_estimate_kwargs(
                    attacker_nature=opponent_nature,
                    attacker_evs=opponent_evs,
                    defender_nature=our_nature,
                    defender_evs=our_evs,
                )
                second_result = self._simulator.estimate_move_result(
                    opponent_sim_pokemon,
                    defender_after_self_damage,
                    opponent_move_obj,
                    field_state,
                    list(our_side_conditions) if our_side_conditions else None,
                    **second_estimate_kwargs,
                )
                move_results[opponent_player_id] = second_result
                player_move_order.append(opponent_player_id)

            opp_hp_min, opp_hp_max = self._hp_range_after_damage(
                opponent_sim_pokemon.current_hp,
                first_result.min_damage,
                first_result.max_damage,
            )
            opp_crit_min, opp_crit_max = self._crit_hp_range_after_damage(
                opponent_sim_pokemon.current_hp,
                first_result.crit_min_damage,
                first_result.crit_max_damage,
            )

            if our_self_fainted:
                our_hp_min = our_hp_max = 0
                our_crit_min = our_crit_max = 0
                our_faint_prob = 1.0
                our_crit_prob = 0.0
            elif second_result is not None:
                our_hp_hit_min, our_hp_hit_max = self._hp_range_after_damage(
                    our_post_move_hp,
                    second_result.min_damage,
                    second_result.max_damage,
                )
                our_crit_hit_min, our_crit_hit_max = self._crit_hp_range_after_damage(
                    our_post_move_hp,
                    second_result.crit_min_damage,
                    second_result.crit_max_damage,
                )
                if opponent_survival < 1.0:
                    our_hp_max = our_post_move_hp
                    our_crit_max = our_post_move_hp
                else:
                    our_hp_max = our_hp_hit_max
                    our_crit_max = our_crit_hit_max
                our_hp_min = our_hp_hit_min
                our_crit_min = our_crit_hit_min
                our_faint_prob = self._clamp_probability(
                    opponent_survival * second_result.knockout_probability
                )
                our_crit_prob = self._clamp_probability(
                    opponent_survival * second_result.critical_hit_probability
                )
            else:
                our_hp_min = our_hp_max = our_post_move_hp
                our_crit_min = our_crit_max = our_post_move_hp
                our_faint_prob = 0.0
                our_crit_prob = 0.0

            our_outcome = PokemonOutcome(
                active_pokemon=our_sim_pokemon.species,
                active_pokemon_hp_range=(our_hp_min, max(our_hp_max, our_hp_min)),
                active_pokemon_max_hp=our_sim_pokemon.max_hp,
                critical_hit_received_hp_range=(
                    our_crit_min,
                    max(our_crit_max, our_crit_min),
                ),
                active_pokemon_moves_probability=0.0 if our_self_fainted else 1.0,
                active_pokemon_fainted_probability=our_faint_prob,
                critical_hit_received_probability=our_crit_prob,
                active_pokemon_status_probability={},
                active_pokemon_stat_changes={},
            )
            opponent_outcome = PokemonOutcome(
                active_pokemon=opponent_sim_pokemon.species,
                active_pokemon_hp_range=(opp_hp_min, max(opp_hp_max, opp_hp_min)),
                active_pokemon_max_hp=opponent_sim_pokemon.max_hp,
                critical_hit_received_hp_range=(
                    opp_crit_min,
                    max(opp_crit_max, opp_crit_min),
                ),
                active_pokemon_moves_probability=opponent_survival,
                active_pokemon_fainted_probability=self._clamp_probability(
                    first_result.knockout_probability
                ),
                critical_hit_received_probability=self._clamp_probability(
                    first_result.critical_hit_probability
                ),
                active_pokemon_status_probability={},
                active_pokemon_stat_changes={},
            )
        else:
            first_estimate_kwargs = self._build_estimate_kwargs(
                attacker_nature=opponent_nature,
                attacker_evs=opponent_evs,
                defender_nature=our_nature,
                defender_evs=our_evs,
            )
            first_result = self._simulator.estimate_move_result(
                opponent_sim_pokemon,
                our_sim_pokemon,
                opponent_move_obj,
                field_state,
                list(our_side_conditions) if our_side_conditions else None,
                **first_estimate_kwargs,
            )
            move_results[opponent_player_id] = first_result
            player_move_order.append(opponent_player_id)

            our_survival = self._clamp_probability(
                1.0 - first_result.knockout_probability
            )

            second_result = None
            if our_survival > 0:
                second_estimate_kwargs = self._build_estimate_kwargs(
                    attacker_nature=our_nature,
                    attacker_evs=our_evs,
                    defender_nature=opponent_nature,
                    defender_evs=opponent_evs,
                )
                second_result = self._simulator.estimate_move_result(
                    our_sim_pokemon,
                    opponent_sim_pokemon,
                    our_move_obj,
                    field_state,
                    list(opponent_side_conditions)
                    if opponent_side_conditions
                    else None,
                    **second_estimate_kwargs,
                )
                move_results[our_player_id] = second_result
                player_move_order.append(our_player_id)

            our_hp_min, our_hp_max = self._hp_range_after_damage(
                our_sim_pokemon.current_hp,
                first_result.min_damage,
                first_result.max_damage,
            )
            our_crit_min, our_crit_max = self._crit_hp_range_after_damage(
                our_sim_pokemon.current_hp,
                first_result.crit_min_damage,
                first_result.crit_max_damage,
            )

            if second_result is not None:
                opp_hp_hit_min, opp_hp_hit_max = self._hp_range_after_damage(
                    opponent_sim_pokemon.current_hp,
                    second_result.min_damage,
                    second_result.max_damage,
                )
                opp_crit_hit_min, opp_crit_hit_max = self._crit_hp_range_after_damage(
                    opponent_sim_pokemon.current_hp,
                    second_result.crit_min_damage,
                    second_result.crit_max_damage,
                )
                if our_survival < 1.0:
                    opp_hp_max = opponent_sim_pokemon.current_hp
                    opp_crit_max = opponent_sim_pokemon.current_hp
                else:
                    opp_hp_max = opp_hp_hit_max
                    opp_crit_max = opp_crit_hit_max
                opp_hp_min = opp_hp_hit_min
                opp_crit_min = opp_crit_hit_min
                opp_faint_prob = self._clamp_probability(
                    our_survival * second_result.knockout_probability
                )
                opp_crit_prob = self._clamp_probability(
                    our_survival * second_result.critical_hit_probability
                )
            else:
                opp_hp_min = opp_hp_max = opponent_sim_pokemon.current_hp
                opp_crit_min = opp_crit_max = opponent_sim_pokemon.current_hp
                opp_faint_prob = 0.0
                opp_crit_prob = 0.0

            our_outcome = PokemonOutcome(
                active_pokemon=our_sim_pokemon.species,
                active_pokemon_hp_range=(our_hp_min, max(our_hp_max, our_hp_min)),
                active_pokemon_max_hp=our_sim_pokemon.max_hp,
                critical_hit_received_hp_range=(
                    our_crit_min,
                    max(our_crit_max, our_crit_min),
                ),
                active_pokemon_moves_probability=our_survival,
                active_pokemon_fainted_probability=self._clamp_probability(
                    first_result.knockout_probability
                ),
                critical_hit_received_probability=self._clamp_probability(
                    first_result.critical_hit_probability
                ),
                active_pokemon_status_probability={},
                active_pokemon_stat_changes={},
            )
            opponent_outcome = PokemonOutcome(
                active_pokemon=opponent_sim_pokemon.species,
                active_pokemon_hp_range=(opp_hp_min, max(opp_hp_max, opp_hp_min)),
                active_pokemon_max_hp=opponent_sim_pokemon.max_hp,
                critical_hit_received_hp_range=(
                    opp_crit_min,
                    max(opp_crit_max, opp_crit_min),
                ),
                active_pokemon_moves_probability=1.0,
                active_pokemon_fainted_probability=opp_faint_prob,
                critical_hit_received_probability=opp_crit_prob,
                active_pokemon_status_probability={},
                active_pokemon_stat_changes={},
            )

        return SimulationResult(
            actions=actions,
            player_move_order=tuple(player_move_order),
            move_results=move_results,
            player_outcomes={
                our_player_id: our_outcome,
                opponent_player_id: opponent_outcome,
            },
        )

    async def _simulate_move_vs_switch(
        self,
        battle_state: BattleState,
        our_pokemon: PokemonState,
        our_move: str,
        our_tera: bool,
        opponent_switching_to: PokemonState,
        field_state: FieldState,
        our_player_id: str,
        opponent_player_id: str,
    ) -> SimulationResult:
        """Simulate our move while opponent switches."""
        opponent_team = battle_state.get_team(opponent_player_id)

        our_sim_pokemon = self._maybe_terastallize_pokemon(our_pokemon, our_tera)
        our_move_obj = self._get_move_from_pokemon(our_sim_pokemon, our_move)
        our_nature, our_evs = self._get_usage_spread(our_sim_pokemon)
        opponent_nature, opponent_evs = self._get_usage_spread(opponent_switching_to)

        opponent_side_conditions = self._get_side_condition_set(opponent_team)

        estimate_kwargs = self._build_estimate_kwargs(
            attacker_nature=our_nature,
            attacker_evs=our_evs,
            defender_nature=opponent_nature,
            defender_evs=opponent_evs,
        )

        move_result = self._simulator.estimate_move_result(
            our_sim_pokemon,
            opponent_switching_to,
            our_move_obj,
            field_state,
            list(opponent_side_conditions) if opponent_side_conditions else None,
            **estimate_kwargs,
        )

        opp_hp_min, opp_hp_max = self._hp_range_after_damage(
            opponent_switching_to.current_hp,
            move_result.min_damage,
            move_result.max_damage,
        )
        opp_crit_min, opp_crit_max = self._crit_hp_range_after_damage(
            opponent_switching_to.current_hp,
            move_result.crit_min_damage,
            move_result.crit_max_damage,
        )
        attacker_post_move_hp = self._apply_self_inflicted_hp_changes(
            our_sim_pokemon.current_hp,
            our_sim_pokemon.max_hp,
            move_result.recoil_damage,
            move_result.drain_heal,
        )
        attacker_fainted = attacker_post_move_hp == 0

        actions = {
            our_player_id: BattleAction(
                action_type=ActionType.MOVE, move_name=our_move, tera=our_tera
            ),
            opponent_player_id: BattleAction(
                action_type=ActionType.SWITCH,
                switch_pokemon_name=opponent_switching_to.species,
            ),
        }

        return SimulationResult(
            actions=actions,
            player_move_order=(opponent_player_id, our_player_id),
            move_results={
                our_player_id: move_result,
                opponent_player_id: None,
            },
            player_outcomes={
                our_player_id: PokemonOutcome(
                    active_pokemon=our_sim_pokemon.species,
                    active_pokemon_hp_range=(
                        attacker_post_move_hp,
                        attacker_post_move_hp,
                    ),
                    active_pokemon_max_hp=our_sim_pokemon.max_hp,
                    critical_hit_received_hp_range=(
                        attacker_post_move_hp,
                        attacker_post_move_hp,
                    ),
                    active_pokemon_moves_probability=0.0 if attacker_fainted else 1.0,
                    active_pokemon_fainted_probability=1.0 if attacker_fainted else 0.0,
                    critical_hit_received_probability=0.0,
                    active_pokemon_status_probability={},
                    active_pokemon_stat_changes={},
                ),
                opponent_player_id: PokemonOutcome(
                    active_pokemon=opponent_switching_to.species,
                    active_pokemon_hp_range=(opp_hp_min, max(opp_hp_max, opp_hp_min)),
                    active_pokemon_max_hp=opponent_switching_to.max_hp,
                    critical_hit_received_hp_range=(
                        opp_crit_min,
                        max(opp_crit_max, opp_crit_min),
                    ),
                    active_pokemon_moves_probability=0.0,
                    active_pokemon_fainted_probability=self._clamp_probability(
                        move_result.knockout_probability
                    ),
                    critical_hit_received_probability=self._clamp_probability(
                        move_result.critical_hit_probability
                    ),
                    active_pokemon_status_probability={},
                    active_pokemon_stat_changes={},
                ),
            },
        )

    async def _simulate_switch_vs_move(
        self,
        battle_state: BattleState,
        our_switching_to: PokemonState,
        opponent_pokemon: PokemonState,
        opponent_move: str,
        field_state: FieldState,
        our_player_id: str,
        opponent_player_id: str,
    ) -> SimulationResult:
        """Simulate us switching while opponent uses move."""
        our_team = battle_state.get_team(our_player_id)

        opponent_move_obj = self._get_move_from_pokemon(opponent_pokemon, opponent_move)
        our_side_conditions = self._get_side_condition_set(our_team)
        opponent_nature, opponent_evs = self._get_usage_spread(opponent_pokemon)
        our_nature, our_evs = self._get_usage_spread(our_switching_to)

        estimate_kwargs = self._build_estimate_kwargs(
            attacker_nature=opponent_nature,
            attacker_evs=opponent_evs,
            defender_nature=our_nature,
            defender_evs=our_evs,
        )

        move_result = self._simulator.estimate_move_result(
            opponent_pokemon,
            our_switching_to,
            opponent_move_obj,
            field_state,
            list(our_side_conditions) if our_side_conditions else None,
            **estimate_kwargs,
        )

        our_hp_min, our_hp_max = self._hp_range_after_damage(
            our_switching_to.current_hp,
            move_result.min_damage,
            move_result.max_damage,
        )
        our_crit_min, our_crit_max = self._crit_hp_range_after_damage(
            our_switching_to.current_hp,
            move_result.crit_min_damage,
            move_result.crit_max_damage,
        )

        actions = {
            our_player_id: BattleAction(
                action_type=ActionType.SWITCH,
                switch_pokemon_name=our_switching_to.species,
            ),
            opponent_player_id: BattleAction(
                action_type=ActionType.MOVE, move_name=opponent_move
            ),
        }

        return SimulationResult(
            actions=actions,
            player_move_order=(our_player_id, opponent_player_id),
            move_results={
                our_player_id: None,
                opponent_player_id: move_result,
            },
            player_outcomes={
                our_player_id: PokemonOutcome(
                    active_pokemon=our_switching_to.species,
                    active_pokemon_hp_range=(our_hp_min, max(our_hp_max, our_hp_min)),
                    active_pokemon_max_hp=our_switching_to.max_hp,
                    critical_hit_received_hp_range=(
                        our_crit_min,
                        max(our_crit_max, our_crit_min),
                    ),
                    active_pokemon_moves_probability=0.0,
                    active_pokemon_fainted_probability=self._clamp_probability(
                        move_result.knockout_probability
                    ),
                    critical_hit_received_probability=self._clamp_probability(
                        move_result.critical_hit_probability
                    ),
                    active_pokemon_status_probability={},
                    active_pokemon_stat_changes={},
                ),
                opponent_player_id: PokemonOutcome(
                    active_pokemon=opponent_pokemon.species,
                    active_pokemon_hp_range=(
                        opponent_pokemon.current_hp,
                        opponent_pokemon.current_hp,
                    ),
                    active_pokemon_max_hp=opponent_pokemon.max_hp,
                    critical_hit_received_hp_range=(
                        opponent_pokemon.current_hp,
                        opponent_pokemon.current_hp,
                    ),
                    active_pokemon_moves_probability=1.0,
                    active_pokemon_fainted_probability=0.0,
                    critical_hit_received_probability=0.0,
                    active_pokemon_status_probability={},
                    active_pokemon_stat_changes={},
                ),
            },
        )

    async def _simulate_switch_vs_switch(
        self,
        battle_state: BattleState,
        our_switching_to: PokemonState,
        opponent_switching_to: PokemonState,
        our_player_id: str,
        opponent_player_id: str,
    ) -> SimulationResult:
        """Simulate both players switching."""
        actions = {
            our_player_id: BattleAction(
                action_type=ActionType.SWITCH,
                switch_pokemon_name=our_switching_to.species,
            ),
            opponent_player_id: BattleAction(
                action_type=ActionType.SWITCH,
                switch_pokemon_name=opponent_switching_to.species,
            ),
        }

        return SimulationResult(
            actions=actions,
            player_move_order=(our_player_id, opponent_player_id),
            move_results={our_player_id: None, opponent_player_id: None},
            player_outcomes={
                our_player_id: PokemonOutcome(
                    active_pokemon=our_switching_to.species,
                    active_pokemon_hp_range=(
                        our_switching_to.current_hp,
                        our_switching_to.current_hp,
                    ),
                    active_pokemon_max_hp=our_switching_to.max_hp,
                    critical_hit_received_hp_range=(
                        our_switching_to.current_hp,
                        our_switching_to.current_hp,
                    ),
                    active_pokemon_moves_probability=0.0,
                    active_pokemon_fainted_probability=0.0,
                    critical_hit_received_probability=0.0,
                    active_pokemon_status_probability={},
                    active_pokemon_stat_changes={},
                ),
                opponent_player_id: PokemonOutcome(
                    active_pokemon=opponent_switching_to.species,
                    active_pokemon_hp_range=(
                        opponent_switching_to.current_hp,
                        opponent_switching_to.current_hp,
                    ),
                    active_pokemon_max_hp=opponent_switching_to.max_hp,
                    critical_hit_received_hp_range=(
                        opponent_switching_to.current_hp,
                        opponent_switching_to.current_hp,
                    ),
                    active_pokemon_moves_probability=0.0,
                    active_pokemon_fainted_probability=0.0,
                    critical_hit_received_probability=0.0,
                    active_pokemon_status_probability={},
                    active_pokemon_stat_changes={},
                ),
            },
        )


@runtime_checkable
class _StatefulContext(Protocol):
    state: Any
