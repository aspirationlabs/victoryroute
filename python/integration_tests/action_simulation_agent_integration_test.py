"""Integration tests for ActionSimulationAgent using real battle logs."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Never

from absl.testing import absltest, parameterized

from python.agents.tools.battle_simulator import BattleSimulator
from python.agents.turn_predictor.action_simulation_agent import ActionSimulationAgent
from python.agents.turn_predictor.simulation_result import SimulationResult
from python.agents.turn_predictor.turn_predictor_state import (
    MovePrediction,
    OpponentPokemonPrediction,
    TurnPredictorState,
)
from python.agents.turn_predictor.turn_predictor_prompt_builder import (
    TurnPredictorPromptBuilder,
)
from python.game.data.game_data import GameData
from python.game.environment.battle_stream_store import BattleStreamStore
from python.game.environment.state_transition import StateTransition
from python.game.events.battle_event import BattleEvent, RequestEvent, TurnEvent
from python.game.interface.battle_action import ActionType, BattleAction
from python.game.protocol.message_parser import MessageParser
from python.game.schema.battle_state import BattleState


def _should_skip_request(event: RequestEvent) -> bool:
    """Return True if the request should not result in a decision state."""
    if not event.request_json:
        return False

    try:
        data = json.loads(event.request_json)
    except json.JSONDecodeError:
        return True

    if data.get("wait") or data.get("teamPreview"):
        return True

    force_switches = data.get("forceSwitch")
    if isinstance(force_switches, list) and any(force_switches):
        return True

    return False


def _iter_replay_events(path: Path) -> Iterable[BattleEvent]:
    """Yield structured events from the given log file."""
    parser = MessageParser()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            event_text = payload.get("event")
            if not event_text:
                continue
            yield parser.parse(event_text)


def _collect_turn_states(
    log_path: Path, past_turns: int = 3
) -> Dict[int, TurnPredictorState]:
    """Replay the battle log and capture TurnPredictorState snapshots."""
    store = BattleStreamStore()
    battle_state = BattleState()
    prompt_builder = TurnPredictorPromptBuilder(store)
    pending_turn: Optional[int] = None
    results: Dict[int, TurnPredictorState] = {}

    for event in _iter_replay_events(log_path):
        store.add_events([event])
        battle_state = StateTransition.apply(battle_state, event)

        if isinstance(event, TurnEvent):
            pending_turn = event.turn_number
            continue

        if not isinstance(event, RequestEvent):
            continue

        if pending_turn is None:
            continue

        if _should_skip_request(event):
            pending_turn = None
            continue

        turn_state = prompt_builder.get_new_turn_state_prompt(
            battle_state=battle_state, past_turns=past_turns
        )
        results[pending_turn] = turn_state
        pending_turn = None

    return results


def _state_dict_from_turn_state(
    state: TurnPredictorState,
    opponent_prediction: OpponentPokemonPrediction,
) -> "StateDict":
    """Create a mutable InvocationContext-like state container."""
    return StateDict(
        our_player_id=state.our_player_id,
        turn_number=state.turn_number,
        available_actions=list(state.available_actions),
        battle_state=state.battle_state,
        past_battle_event_logs=state.past_battle_event_logs,
        past_player_actions=state.past_player_actions,
        opponent_predicted_active_pokemon=opponent_prediction,
    )


class StateDict(dict):
    """Dict subclass exposing selected items as attributes for the agent."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__()
        for key, value in kwargs.items():
            setattr(self, key, value)


class InvocationContextStub:
    """Minimal InvocationContext substitute for driving the agent in tests."""

    def __init__(self, state: StateDict) -> None:
        self.state = state


def _select_min_damage_action(
    results: Sequence[SimulationResult],
    our_player_id: str,
    opponent_player_id: str,
) -> BattleAction:
    """Return the action whose worst-case damage across opponent moves is minimal."""
    action_damage: Dict[
        tuple[ActionType, Optional[str], Optional[str], Optional[int], bool, bool],
        tuple[BattleAction, List[int]],
    ] = {}

    for result in results:
        opponent_action = result.actions[opponent_player_id]
        if opponent_action.action_type != ActionType.MOVE:
            continue

        our_action = result.actions[our_player_id]
        key = (
            our_action.action_type,
            our_action.move_name,
            our_action.switch_pokemon_name,
            our_action.target_index,
            our_action.mega,
            our_action.tera,
        )

        our_outcome = result.player_outcomes[our_player_id]
        starting_hp = our_outcome.active_pokemon_max_hp
        min_hp_after = our_outcome.active_pokemon_hp_range[0]
        damage_taken = max(0, starting_hp - min_hp_after)

        if key not in action_damage:
            action_damage[key] = (our_action, [damage_taken])
        else:
            action_damage[key][1].append(damage_taken)

    if not action_damage:
        raise AssertionError("No move-vs-move results found to compute min damage")

    best_action: Optional[BattleAction] = None
    best_worst_damage: Optional[int] = None

    for action, damages in action_damage.values():
        worst_case = max(damages) if damages else 0
        if best_worst_damage is None or worst_case < best_worst_damage:
            best_worst_damage = worst_case
            best_action = action

    if best_action is None or best_worst_damage is None:
        raise AssertionError("Failed to determine minimum-damage action")

    return best_action


def _select_max_damage_action(
    results: Sequence[SimulationResult],
    our_player_id: str,
    opponent_player_id: str,
) -> BattleAction:
    """Return our move action that maximises damage on the opponent."""
    selected_action: Optional[BattleAction] = None
    max_damage: Optional[int] = None

    for result in results:
        opponent_action = result.actions[opponent_player_id]
        our_action = result.actions[our_player_id]
        if opponent_action.action_type != ActionType.MOVE:
            continue
        if our_action.action_type != ActionType.MOVE:
            continue

        opponent_outcome = result.player_outcomes[opponent_player_id]
        starting_hp = opponent_outcome.active_pokemon_max_hp
        min_hp_after = opponent_outcome.active_pokemon_hp_range[0]
        damage_dealt = max(0, starting_hp - min_hp_after)

        if max_damage is None or damage_dealt > max_damage:
            max_damage = damage_dealt
            selected_action = our_action

    if selected_action is None or max_damage is None:
        raise AssertionError("No move-vs-move results found to compute max damage")

    return selected_action


class ActionSimulationAgentIntegrationTest(
    unittest.IsolatedAsyncioTestCase, parameterized.TestCase
):
    """Integration tests that replay battle logs and validate simulations."""

    def setUp(self) -> Never:
        super().setUp()
        self._log_path = Path(
            "python/integration_tests/testdata/live_battle_4.txt"
        ).resolve()
        self._agent = ActionSimulationAgent(
            name="integration_action_simulator",
            battle_simulator=BattleSimulator(GameData()),
        )
        return

    @parameterized.named_parameters(
        (
            "turn_01_lokix_vs_iron_crown",
            1,
            OpponentPokemonPrediction(
                species="Iron Crown",
                moves=[
                    MovePrediction(name="Tachyon Cutter", confidence=0.85),
                    MovePrediction(name="Future Sight", confidence=0.8),
                    MovePrediction(name="Flash Cannon", confidence=0.6),
                    MovePrediction(name="Volt Switch", confidence=0.7),
                ],
                item="Booster Energy",
                ability="Quark Drive",
                tera_type="Steel",
            ),
            81,
            BattleAction(action_type=ActionType.SWITCH, switch_pokemon_name="Latios"),
            BattleAction(action_type=ActionType.MOVE, move_name="Sucker Punch"),
        ),
        (
            "turn_03_gliscor_vs_iron_crown",
            3,
            OpponentPokemonPrediction(
                species="Iron Crown",
                moves=[
                    MovePrediction(name="Tachyon Cutter", confidence=0.85),
                    MovePrediction(name="Future Sight", confidence=0.8),
                    MovePrediction(name="Flash Cannon", confidence=0.6),
                    MovePrediction(name="Volt Switch", confidence=0.7),
                ],
                item="Booster Energy",
                ability="Quark Drive",
                tera_type="Steel",
            ),
            72,
            BattleAction(action_type=ActionType.SWITCH, switch_pokemon_name="Latios"),
            BattleAction(action_type=ActionType.MOVE, move_name="Knock Off"),
        ),
        (
            "turn_06_gliscor_vs_samurott",
            6,
            OpponentPokemonPrediction(
                species="Samurott-Hisui",
                moves=[
                    MovePrediction(name="Razor Shell", confidence=0.9),
                    MovePrediction(name="Ceaseless Edge", confidence=0.75),
                    MovePrediction(name="Aqua Jet", confidence=0.6),
                    MovePrediction(name="Knock Off", confidence=0.65),
                ],
                item="Mystic Water",
                ability="Sharpness",
                tera_type="Water",
            ),
            64,
            BattleAction(
                action_type=ActionType.SWITCH, switch_pokemon_name="Zamazenta"
            ),
            BattleAction(action_type=ActionType.MOVE, move_name="U-turn"),
        ),
        (
            "turn_12_zamazenta_vs_landorus",
            12,
            OpponentPokemonPrediction(
                species="Landorus-Therian",
                moves=[
                    MovePrediction(name="Earth Power", confidence=0.85),
                    MovePrediction(name="U-turn", confidence=0.75),
                    MovePrediction(name="Stone Edge", confidence=0.8),
                    MovePrediction(name="Stealth Rock", confidence=0.7),
                ],
                item="Leftovers",
                ability="Intimidate",
                tera_type="Ground",
            ),
            42,
            BattleAction(action_type=ActionType.SWITCH, switch_pokemon_name="Latios"),
            BattleAction(action_type=ActionType.MOVE, move_name="Ice Fang"),
        ),
    )
    async def test_action_simulation_agent_turns(
        self,
        turn_number: int,
        opponent_prediction: OpponentPokemonPrediction,
        expected_total: int,
        expected_min_action: BattleAction,
        expected_max_action: BattleAction,
    ) -> None:
        """Validate ActionSimulationAgent results for specific battle turns."""
        turn_state_map = _collect_turn_states(self._log_path)
        self.assertIn(
            turn_number,
            turn_state_map,
            msg=f"Turn {turn_number} not found in replayed battle log.",
        )
        turn_state = turn_state_map[turn_number]

        state_dict = _state_dict_from_turn_state(
            state=turn_state, opponent_prediction=opponent_prediction
        )
        ctx = InvocationContextStub(state_dict)

        events = [event async for event in self._agent._run_async_impl(ctx)]  # type: ignore[arg-type]
        self.assertTrue(events, msg="Agent should emit a completion event.")

        self.assertIn("simulation_actions", ctx.state)
        simulation_results: List[SimulationResult] = ctx.state["simulation_actions"]

        opponent_player_id = "p2" if turn_state.our_player_id == "p1" else "p1"
        self.assertEqual(
            expected_total,
            len(simulation_results),
            msg="Mismatch in expected vs actual simulation results.",
        )

        our_player_id = turn_state.our_player_id

        min_damage_action = _select_min_damage_action(
            simulation_results,
            our_player_id=our_player_id,
            opponent_player_id=opponent_player_id,
        )
        max_damage_action = _select_max_damage_action(
            simulation_results,
            our_player_id=our_player_id,
            opponent_player_id=opponent_player_id,
        )
        breakpoint()
        self.assertEqual(expected_min_action, min_damage_action)
        self.assertEqual(expected_max_action, max_damage_action)


if __name__ == "__main__":
    absltest.main()
