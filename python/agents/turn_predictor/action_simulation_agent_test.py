"""Unit tests for ActionSimulationAgent."""

import unittest
from typing import List
from unittest.mock import AsyncMock, Mock

from absl.testing import absltest
from google.adk.agents import InvocationContext
from google.adk.events import Event

from python.agents.tools.battle_simulator import (
    BattleSimulator,
    MoveAction,
    MoveResult,
)
from python.agents.tools.pokemon_state_priors_reader import (
    PokemonStatePriorsReader,
)
from python.agents.turn_predictor.action_simulation_agent import (
    ActionSimulationAgent,
)
from python.agents.turn_predictor.simulation_result import SimulationResult
from python.agents.turn_predictor.turn_predictor_state import (
    MovePrediction,
    OpponentPokemonPrediction,
    TurnPredictorState,
)
from python.game.interface.battle_action import ActionType, BattleAction
from python.game.schema.battle_state import BattleState, TeamState
from python.game.schema.enums import Status
from python.game.schema.field_state import FieldState
from python.game.schema.pokemon_state import PokemonMove, PokemonState


class ActionSimulationAgentTest(absltest.TestCase, unittest.IsolatedAsyncioTestCase):
    """Test cases for ActionSimulationAgent."""

    def setUp(self) -> None:  # type: ignore[override]
        """Set up test fixtures."""
        super().setUp()

        self.mock_simulator = Mock(spec=BattleSimulator)
        self.mock_simulator.get_move_order = Mock()
        self.mock_simulator.estimate_move_result = Mock()

        self.mock_priors_reader = Mock(spec=PokemonStatePriorsReader)
        self.mock_priors_reader.get_top_usage_spread.return_value = None

        self.agent = ActionSimulationAgent(
            name="test_simulation_agent",
            battle_simulator=self.mock_simulator,
            priors_reader=self.mock_priors_reader,
        )

        self.sample_our_pokemon = self._create_sample_pokemon(
            species="Garchomp",
            current_hp=300,
            max_hp=300,
            moves=["Earthquake", "Dragon Claw", "Swords Dance", "Stone Edge"],
            is_active=True,
        )

        self.sample_opponent_pokemon = self._create_sample_pokemon(
            species="Landorus-Therian",
            current_hp=250,
            max_hp=250,
            moves=["U-turn", "Earthquake", "Rock Slide", "Stealth Rock"],
            is_active=True,
        )
        self.sample_battle_state = BattleState(
            teams={
                "p1": TeamState(
                    player_id="p1",
                    pokemon=[
                        self.sample_our_pokemon,
                        self._create_sample_pokemon(
                            "Rotom-Wash", 250, 250, ["Hydro Pump", "Volt Switch"]
                        ),
                    ],
                    active_pokemon_index=0,
                    side_conditions={},
                ),
                "p2": TeamState(
                    player_id="p2",
                    pokemon=[
                        self.sample_opponent_pokemon,
                        self._create_sample_pokemon(
                            "Ferrothorn", 280, 280, ["Power Whip", "Gyro Ball"]
                        ),
                    ],
                    active_pokemon_index=0,
                    side_conditions={},
                ),
            },
            field_state=FieldState(),
            battle_format="singles",
            available_moves=["Earthquake", "Dragon Claw", "Swords Dance", "Stone Edge"],
            available_switches=[1],  # Can switch to Rotom-Wash
            can_mega=False,
            can_tera=True,
            can_dynamax=False,
            force_switch=False,
            team_preview=False,
            waiting=False,
            battle_over=False,
            our_player_id="p1",
        )
        self.sample_opponent_prediction = OpponentPokemonPrediction(
            species="Landorus-Therian",
            moves=[
                MovePrediction(name="U-turn", confidence=0.8),
                MovePrediction(name="Earthquake", confidence=0.9),
                MovePrediction(name="Rock Slide", confidence=0.6),
                MovePrediction(name="Stealth Rock", confidence=0.7),
            ],
            item="Choice Scarf",
            ability="Intimidate",
            tera_type="Flying",
        )

    def _create_sample_pokemon(
        self,
        species: str,
        current_hp: int,
        max_hp: int,
        moves: List[str],
        is_active: bool = False,
    ) -> PokemonState:
        """Create a sample PokemonState for testing."""
        pokemon_moves = [
            PokemonMove(name=move, current_pp=5, max_pp=5) for move in moves
        ]
        return PokemonState(
            species=species,
            level=50,
            current_hp=current_hp,
            max_hp=max_hp,
            status=Status.NONE,
            stat_boosts={},
            moves=pokemon_moves,
            item="Leftovers",
            ability="Rough Skin",
            tera_type="Ground",
            has_terastallized=False,
            volatile_conditions={},
            is_active=is_active,
            active_effects={},
        )

    async def test_agent_produces_simulation_results(self):
        """Test that agent produces simulation results for all action combinations."""
        # Create a mock state with proper spec
        mock_state = Mock(spec=TurnPredictorState)
        mock_state.our_player_id = "p1"
        mock_state.available_actions = [
            BattleAction(action_type=ActionType.MOVE, move_name="Earthquake"),
            BattleAction(
                action_type=ActionType.MOVE, move_name="Dragon Claw", tera=True
            ),
            BattleAction(
                action_type=ActionType.SWITCH, switch_pokemon_name="Rotom-Wash"
            ),
        ]
        mock_state.opponent_predicted_active_pokemon = self.sample_opponent_prediction
        mock_state.battle_state = self.sample_battle_state

        # Mock the InvocationContext
        ctx = Mock(spec=InvocationContext)

        # Create a dict-like object that supports both attribute access and item assignment
        class StateDict(dict):
            def __init__(self, mock_state):
                super().__init__()
                self.our_player_id = mock_state.our_player_id
                self.available_actions = mock_state.available_actions
                self.opponent_predicted_active_pokemon = (
                    mock_state.opponent_predicted_active_pokemon
                )
                self.battle_state = mock_state.battle_state

        ctx.state = StateDict(mock_state)

        # Mock the simulation methods to return placeholder results
        mock_result = Mock(spec=SimulationResult)
        self.agent._simulate_move_vs_move = AsyncMock(return_value=mock_result)
        self.agent._simulate_move_vs_switch = AsyncMock(return_value=mock_result)
        self.agent._simulate_switch_vs_move = AsyncMock(return_value=mock_result)
        self.agent._simulate_switch_vs_switch = AsyncMock(return_value=mock_result)

        events: List[Event] = []
        async for event in self.agent._run_async_impl(ctx):
            events.append(event)

        self.assertIn("simulation_actions", ctx.state)
        simulation_actions = ctx.state["simulation_actions"]

        # Should have results for:
        # - 2 moves * (4 opponent moves + 1 opponent switch) = 10
        # - 1 switch * (4 opponent moves + 1 opponent switch) = 5
        # Total: 15 simulations
        self.assertEqual(len(simulation_actions), 15)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].author, "ActionSimulationAgent")
        self.assertIsNotNone(events[0].content)
        self.assertIsNotNone(events[0].content.parts)  # type: ignore[union-attr]
        self.assertIn(str(len(simulation_actions)), events[0].content.parts[0].text)  # type: ignore[union-attr]

    async def test_agent_with_turn_predictor_state(self):
        """Test agent execution with a TurnPredictorState converted to StateDict."""
        ctx = Mock(spec=InvocationContext)

        # Create a TurnPredictorState with all necessary fields
        initial_state = TurnPredictorState(
            our_player_id="p1",
            turn_number=1,
            opponent_active_pokemon=self.sample_opponent_pokemon,
            past_battle_event_logs="",
            past_player_actions="",
            battle_state=self.sample_battle_state,
            available_actions=[
                BattleAction(action_type=ActionType.MOVE, move_name="Earthquake"),
                BattleAction(
                    action_type=ActionType.MOVE, move_name="Dragon Claw", tera=True
                ),
                BattleAction(
                    action_type=ActionType.SWITCH, switch_pokemon_name="Rotom-Wash"
                ),
            ],
            opponent_predicted_active_pokemon=self.sample_opponent_prediction,
        )

        # Create a dict-like state from the TurnPredictorState
        class StateDict(dict):
            def __init__(self, state: TurnPredictorState):
                super().__init__()
                self.our_player_id = state.our_player_id
                self.available_actions = state.available_actions
                self.opponent_predicted_active_pokemon = (
                    state.opponent_predicted_active_pokemon
                )
                self.battle_state = state.battle_state

        ctx.state = StateDict(initial_state)

        mock_result = Mock(spec=SimulationResult)
        self.agent._simulate_move_vs_move = AsyncMock(return_value=mock_result)
        self.agent._simulate_move_vs_switch = AsyncMock(return_value=mock_result)
        self.agent._simulate_switch_vs_move = AsyncMock(return_value=mock_result)
        self.agent._simulate_switch_vs_switch = AsyncMock(return_value=mock_result)

        events: List[Event] = []
        async for event in self.agent._run_async_impl(ctx):
            events.append(event)

        # Check that simulation_actions was added to the state dict
        self.assertIn("simulation_actions", ctx.state)
        simulation_actions = ctx.state["simulation_actions"]
        self.assertEqual(len(simulation_actions), 15)
        self.assertEqual(len(events), 1)

    async def test_agent_handles_no_opponent_prediction(self):
        """Test that agent handles case when no opponent prediction is available."""
        mock_state = Mock()
        mock_state.our_player_id = "p1"
        mock_state.available_actions = [
            BattleAction(action_type=ActionType.MOVE, move_name="Earthquake")
        ]
        mock_state.opponent_predicted_active_pokemon = None
        mock_state.battle_state = self.sample_battle_state

        # Mock the InvocationContext
        ctx = Mock(spec=InvocationContext)
        ctx.state = mock_state

        events = []
        async for event in self.agent._run_async_impl(ctx):
            events.append(event)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].author, "ActionSimulationAgent")
        self.assertIsNotNone(events[0].content)
        self.assertIsNotNone(events[0].content.parts)  # type: ignore[union-attr]
        self.assertIn("opponent prediction", events[0].content.parts[0].text)  # type: ignore[union-attr]

    async def test_get_opponent_switches(self):
        """Test getting valid switch targets for opponent."""
        switches = self.agent._get_opponent_switches(self.sample_battle_state, "p2")

        # Should have 1 switch option (Ferrothorn)
        self.assertEqual(len(switches), 1)
        self.assertEqual(switches[0].species, "Ferrothorn")

    async def test_get_opponent_switches_no_valid_targets(self):
        """Test getting switches when all Pokemon are fainted or active."""
        from dataclasses import replace

        # Create a fainted Ferrothorn
        fainted_ferrothorn = replace(
            self.sample_battle_state.teams["p2"].pokemon[1], current_hp=0
        )

        # Create a new team with the fainted Pokemon
        modified_team = replace(
            self.sample_battle_state.teams["p2"],
            pokemon=[
                self.sample_battle_state.teams["p2"].pokemon[0],  # Active Landorus
                fainted_ferrothorn,  # Fainted Ferrothorn
            ],
        )

        # Create a new battle state with the modified team
        battle_state = replace(
            self.sample_battle_state,
            teams={"p1": self.sample_battle_state.teams["p1"], "p2": modified_team},
        )

        switches = self.agent._get_opponent_switches(battle_state, "p2")
        self.assertEqual(len(switches), 0)

    def test_build_opponent_pokemon_state(self):
        """Test building opponent Pokemon state with predicted attributes."""
        updated_pokemon = self.agent._build_opponent_pokemon_state(
            self.sample_battle_state,
            self.sample_opponent_prediction,
            "p2",
        )

        # Check that predicted attributes are applied
        self.assertEqual(updated_pokemon.item, "Choice Scarf")
        self.assertEqual(updated_pokemon.ability, "Intimidate")
        self.assertEqual(updated_pokemon.tera_type, "Flying")

        # Check that moves are updated to predicted moves (PokemonMove objects have .name attribute)
        move_names = [move.name for move in updated_pokemon.moves]
        self.assertIn("U-turn", move_names)
        self.assertIn("Earthquake", move_names)

        # Check that other attributes are preserved
        self.assertEqual(updated_pokemon.current_hp, 250)
        self.assertEqual(updated_pokemon.max_hp, 250)
        self.assertEqual(updated_pokemon.species, "Landorus-Therian")

    def test_get_switch_target(self):
        """Test getting a specific Pokemon by name for switching."""
        # Test getting by species name
        target = self.agent._get_switch_target(
            self.sample_battle_state, "p1", "Rotom-Wash"
        )
        self.assertIsNotNone(target)
        self.assertEqual(target.species, "Rotom-Wash")

        # Test getting non-existent Pokemon
        target = self.agent._get_switch_target(
            self.sample_battle_state, "p1", "Pikachu"
        )
        self.assertIsNone(target)

    async def test_simulate_move_vs_move(self):
        """Verify move-vs-move simulations produce expected outcomes."""
        self.mock_simulator.reset_mock()

        our_move_obj = next(
            move for move in self.sample_our_pokemon.moves if move.name == "Earthquake"
        )
        opponent_move_obj = next(
            move for move in self.sample_opponent_pokemon.moves if move.name == "U-turn"
        )

        self.mock_simulator.get_move_order.return_value = [
            MoveAction(
                pokemon=self.sample_our_pokemon,
                move=our_move_obj,
                priority=0,
                fractional_priority=0.0,
                speed=120,
            ),
            MoveAction(
                pokemon=self.sample_opponent_pokemon,
                move=opponent_move_obj,
                priority=0,
                fractional_priority=0.0,
                speed=100,
            ),
        ]

        our_result = MoveResult(
            min_damage=50,
            max_damage=70,
            knockout_probability=0.2,
            critical_hit_probability=0.1,
            crit_min_damage=90,
            crit_max_damage=110,
            status_effects={},
            additional_effects=[],
        )
        opponent_result = MoveResult(
            min_damage=40,
            max_damage=60,
            knockout_probability=0.1,
            critical_hit_probability=0.05,
            crit_min_damage=80,
            crit_max_damage=100,
            status_effects={},
            additional_effects=[],
        )
        self.mock_simulator.estimate_move_result.side_effect = [
            our_result,
            opponent_result,
        ]

        result = await self.agent._simulate_move_vs_move(
            battle_state=self.sample_battle_state,
            our_pokemon=self.sample_our_pokemon,
            our_move="Earthquake",
            our_tera=False,
            opponent_pokemon=self.sample_opponent_pokemon,
            opponent_move="U-turn",
            field_state=self.sample_battle_state.field_state,
            our_player_id="p1",
            opponent_player_id="p2",
        )

        self.mock_simulator.get_move_order.assert_called_once()
        called_species = {
            call.args[0]
            for call in self.mock_priors_reader.get_top_usage_spread.call_args_list
        }
        self.assertEqual({"Garchomp", "Landorus-Therian"}, called_species)
        self.assertEqual(result.actions["p1"].move_name, "Earthquake")
        self.assertEqual(result.actions["p2"].move_name, "U-turn")
        self.assertEqual(result.player_move_order, ("p1", "p2"))
        self.assertEqual(result.move_results["p1"], our_result)
        self.assertEqual(result.move_results["p2"], opponent_result)

        our_outcome = result.player_outcomes["p1"]
        opp_outcome = result.player_outcomes["p2"]
        self.assertEqual(our_outcome.active_pokemon_hp_range, (240, 300))
        self.assertEqual(our_outcome.critical_hit_received_hp_range, (200, 300))
        self.assertAlmostEqual(our_outcome.active_pokemon_fainted_probability, 0.08)
        self.assertAlmostEqual(opp_outcome.active_pokemon_moves_probability, 0.8)
        self.assertEqual(opp_outcome.active_pokemon_hp_range, (180, 200))
        self.assertEqual(opp_outcome.critical_hit_received_hp_range, (140, 160))

    async def test_simulate_move_vs_move_applies_recoil_before_retaliation(self):
        """Ensure recoil adjusts our HP before potential counterattacks."""
        self.mock_simulator.reset_mock()

        our_move_obj = next(
            move for move in self.sample_our_pokemon.moves if move.name == "Earthquake"
        )
        opponent_move_obj = next(
            move for move in self.sample_opponent_pokemon.moves if move.name == "U-turn"
        )

        self.mock_simulator.get_move_order.return_value = [
            MoveAction(
                pokemon=self.sample_our_pokemon,
                move=our_move_obj,
                priority=0,
                fractional_priority=0.0,
                speed=120,
            ),
            MoveAction(
                pokemon=self.sample_opponent_pokemon,
                move=opponent_move_obj,
                priority=0,
                fractional_priority=0.0,
                speed=100,
            ),
        ]

        our_result = MoveResult(
            min_damage=50,
            max_damage=70,
            knockout_probability=0.2,
            critical_hit_probability=0.1,
            crit_min_damage=90,
            crit_max_damage=110,
            status_effects={},
            additional_effects=[],
            recoil_damage=50,
        )
        opponent_result = MoveResult(
            min_damage=40,
            max_damage=60,
            knockout_probability=0.1,
            critical_hit_probability=0.05,
            crit_min_damage=80,
            crit_max_damage=100,
            status_effects={},
            additional_effects=[],
        )
        self.mock_simulator.estimate_move_result.side_effect = [
            our_result,
            opponent_result,
        ]

        result = await self.agent._simulate_move_vs_move(
            battle_state=self.sample_battle_state,
            our_pokemon=self.sample_our_pokemon,
            our_move="Earthquake",
            our_tera=False,
            opponent_pokemon=self.sample_opponent_pokemon,
            opponent_move="U-turn",
            field_state=self.sample_battle_state.field_state,
            our_player_id="p1",
            opponent_player_id="p2",
        )

        second_call_args = self.mock_simulator.estimate_move_result.call_args_list[1][0]
        self.assertEqual(second_call_args[1].current_hp, 250)
        our_outcome = result.player_outcomes["p1"]
        self.assertEqual(our_outcome.active_pokemon_hp_range, (190, 250))
        self.assertEqual(our_outcome.critical_hit_received_hp_range, (150, 250))
        self.assertAlmostEqual(our_outcome.active_pokemon_fainted_probability, 0.08)
        self.assertAlmostEqual(our_outcome.active_pokemon_moves_probability, 1.0)

    async def test_simulate_move_vs_switch(self):
        """Verify move-vs-switch simulation applies damage to incoming Pokemon."""
        self.mock_simulator.reset_mock()

        our_move_result = MoveResult(
            min_damage=60,
            max_damage=80,
            knockout_probability=0.3,
            critical_hit_probability=0.15,
            crit_min_damage=90,
            crit_max_damage=110,
            status_effects={},
            additional_effects=[],
        )
        self.mock_simulator.estimate_move_result.return_value = our_move_result

        result = await self.agent._simulate_move_vs_switch(
            battle_state=self.sample_battle_state,
            our_pokemon=self.sample_our_pokemon,
            our_move="Earthquake",
            our_tera=False,
            opponent_switching_to=self.sample_opponent_pokemon,
            field_state=self.sample_battle_state.field_state,
            our_player_id="p1",
            opponent_player_id="p2",
        )

        self.mock_simulator.estimate_move_result.assert_called_once()
        self.assertEqual(result.actions["p2"].action_type, ActionType.SWITCH)
        self.assertEqual(result.player_move_order, ("p2", "p1"))
        self.assertEqual(result.move_results["p1"], our_move_result)
        self.assertIsNone(result.move_results["p2"])

        opponent_outcome = result.player_outcomes["p2"]
        self.assertEqual(opponent_outcome.active_pokemon_hp_range, (170, 190))
        self.assertAlmostEqual(opponent_outcome.active_pokemon_fainted_probability, 0.3)
        self.assertAlmostEqual(opponent_outcome.critical_hit_received_probability, 0.15)

    async def test_simulate_move_vs_switch_recoil_updates_attacker_hp(self):
        """Recoil should be reflected in our outcome when opponent switches."""
        self.mock_simulator.reset_mock()

        recoil_result = MoveResult(
            min_damage=60,
            max_damage=80,
            knockout_probability=0.3,
            critical_hit_probability=0.15,
            crit_min_damage=90,
            crit_max_damage=110,
            status_effects={},
            additional_effects=[],
            recoil_damage=320,
        )
        self.mock_simulator.estimate_move_result.return_value = recoil_result

        result = await self.agent._simulate_move_vs_switch(
            battle_state=self.sample_battle_state,
            our_pokemon=self.sample_our_pokemon,
            our_move="Earthquake",
            our_tera=False,
            opponent_switching_to=self.sample_opponent_pokemon,
            field_state=self.sample_battle_state.field_state,
            our_player_id="p1",
            opponent_player_id="p2",
        )

        our_outcome = result.player_outcomes["p1"]
        self.assertEqual(our_outcome.active_pokemon_hp_range, (0, 0))
        self.assertEqual(our_outcome.critical_hit_received_hp_range, (0, 0))
        self.assertAlmostEqual(our_outcome.active_pokemon_moves_probability, 0.0)
        self.assertAlmostEqual(our_outcome.active_pokemon_fainted_probability, 1.0)

    async def test_simulate_switch_vs_move(self):
        """Verify switch-vs-move applies damage to the incoming Pokemon."""
        self.mock_simulator.reset_mock()

        opponent_move_result = MoveResult(
            min_damage=45,
            max_damage=65,
            knockout_probability=0.25,
            critical_hit_probability=0.05,
            crit_min_damage=70,
            crit_max_damage=90,
            status_effects={},
            additional_effects=[],
        )
        self.mock_simulator.estimate_move_result.return_value = opponent_move_result

        result = await self.agent._simulate_switch_vs_move(
            battle_state=self.sample_battle_state,
            our_switching_to=self.sample_our_pokemon,
            opponent_pokemon=self.sample_opponent_pokemon,
            opponent_move="U-turn",
            field_state=self.sample_battle_state.field_state,
            our_player_id="p1",
            opponent_player_id="p2",
        )

        self.mock_simulator.estimate_move_result.assert_called_once()
        self.assertEqual(result.actions["p1"].action_type, ActionType.SWITCH)
        self.assertEqual(result.actions["p2"].move_name, "U-turn")
        self.assertEqual(result.player_move_order, ("p1", "p2"))
        self.assertIsNone(result.move_results["p1"])
        self.assertEqual(result.move_results["p2"], opponent_move_result)

        our_outcome = result.player_outcomes["p1"]
        self.assertEqual(our_outcome.active_pokemon_hp_range, (235, 255))
        self.assertAlmostEqual(our_outcome.active_pokemon_fainted_probability, 0.25)

    async def test_simulate_switch_vs_switch(self):
        """Verify switch-vs-switch leaves HP untouched and no damage results."""
        self.mock_simulator.reset_mock()

        result = await self.agent._simulate_switch_vs_switch(
            battle_state=self.sample_battle_state,
            our_switching_to=self.sample_our_pokemon,
            opponent_switching_to=self.sample_opponent_pokemon,
            our_player_id="p1",
            opponent_player_id="p2",
        )

        self.mock_simulator.get_move_order.assert_not_called()
        self.mock_simulator.estimate_move_result.assert_not_called()
        self.assertEqual(result.actions["p1"].action_type, ActionType.SWITCH)
        self.assertEqual(result.actions["p2"].action_type, ActionType.SWITCH)
        self.assertEqual(result.move_results["p1"], None)
        self.assertEqual(result.move_results["p2"], None)
        self.assertEqual(
            result.player_outcomes["p1"].active_pokemon_hp_range,
            (self.sample_our_pokemon.current_hp, self.sample_our_pokemon.current_hp),
        )
        self.assertEqual(
            result.player_outcomes["p2"].active_pokemon_hp_range,
            (
                self.sample_opponent_pokemon.current_hp,
                self.sample_opponent_pokemon.current_hp,
            ),
        )


if __name__ == "__main__":
    absltest.main()
