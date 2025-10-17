"""Utility to extract TurnPredictorState snapshots from battle replay logs.

Run this as a module, e.g.:
    python -m python.agents.adk_agents.generate_turn_predictor_state \
        --battle-id battle-gen9ou-822 --turn 1
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, List, Optional, Sequence, Tuple

from absl import logging

from python.agents.turn_predictor.turn_predictor_prompt_builder import (
    TurnPredictorPromptBuilder,
)
from python.game.environment.battle_stream_store import BattleStreamStore
from python.game.environment.state_transition import StateTransition
from python.game.events.battle_event import BattleEvent, RequestEvent, TurnEvent
from python.game.protocol.message_parser import MessageParser
from python.game.schema.battle_state import BattleState
from python.agents.turn_predictor.turn_predictor_state import TurnPredictorState


def _iter_log_lines(paths: Sequence[Path]) -> Iterator[str]:
    """Yield raw event strings from a collection of log files."""
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    logging.warning("Skipping malformed log line in %s: %s", path, line)
                    continue
                event = payload.get("event")
                if not isinstance(event, str):
                    logging.warning(
                        "Skipping log line without event string in %s: %s", path, line
                    )
                    continue
                yield event


def _should_skip_request(event: RequestEvent) -> bool:
    """Return True if the request shouldn't create a new decision state."""
    try:
        data = json.loads(event.request_json) if event.request_json else {}
    except json.JSONDecodeError:
        logging.warning("Failed to parse request JSON: %s", event.request_json)
        return True

    if data.get("wait"):
        return True

    if data.get("teamPreview"):
        return True

    force_switches = data.get("forceSwitch")
    if isinstance(force_switches, list) and any(force_switches):
        return True

    return False


def _battle_state_to_json(state: BattleState) -> dict:
    """Convert BattleState dataclass (and children) into plain JSON data."""
    if is_dataclass(state):
        return asdict(state)
    raise TypeError("BattleState must be a dataclass instance")


def _turn_predictor_state_to_json(state: TurnPredictorState) -> dict[str, Any]:
    """Convert TurnPredictorState into JSON-serialisable data."""
    data = state.model_dump(mode="json")
    battle_state = data.get("battle_state")
    if not isinstance(battle_state, dict):
        data["battle_state"] = _battle_state_to_json(state.battle_state)
    return data


def _collect_states(
    events: Iterable[str],
    target_turns: Optional[set[int]],
    past_turns: int,
) -> List[Tuple[int, TurnPredictorState]]:
    """Replay events and collect TurnPredictorStates for selected turns."""
    parser = MessageParser()
    store = BattleStreamStore()
    prompt_builder = TurnPredictorPromptBuilder(battle_stream_store=store)
    battle_state = BattleState()

    pending_turn: Optional[int] = None
    results: List[Tuple[int, TurnPredictorState]] = []

    for raw_event in events:
        battle_event: BattleEvent = parser.parse(raw_event)
        store.add_events([battle_event])
        battle_state = StateTransition.apply(battle_state, battle_event)

        if isinstance(battle_event, TurnEvent):
            pending_turn = battle_event.turn_number
            continue

        if not isinstance(battle_event, RequestEvent):
            continue

        if pending_turn is None:
            continue

        if _should_skip_request(battle_event):
            continue

        if target_turns is not None and pending_turn not in target_turns:
            pending_turn = None
            continue

        turn_state = prompt_builder.get_new_turn_state_prompt(
            battle_state, past_turns=past_turns
        )
        results.append((pending_turn, turn_state))

        if target_turns is not None:
            target_turns.discard(pending_turn)
            if not target_turns:
                break

        pending_turn = None

    missing = target_turns if target_turns else set()
    if missing:
        missing_list = ", ".join(str(t) for t in sorted(missing))
        raise ValueError(f"No decision found for turn(s): {missing_list}")

    return results


def find_log_files(log_dir: Path, battle_id: str) -> List[Path]:
    """Find replay log files for a specific battle ID."""
    pattern = f"*{battle_id}*.txt"
    paths = sorted(log_dir.glob(pattern))
    if not paths:
        raise FileNotFoundError(
            f"No log files found in {log_dir} matching pattern {pattern}"
        )
    return paths


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate TurnPredictorState JSON snapshots from battle logs."
    )
    parser.add_argument(
        "--battle-id",
        required=True,
        help="Battle room ID (e.g., battle-gen9ou-822).",
    )
    parser.add_argument(
        "--turn",
        type=int,
        action="append",
        help="Turn number to extract. Repeat flag to capture multiple turns.",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("/tmp/logs"),
        help="Directory containing replay log files.",
    )
    parser.add_argument(
        "--past-turns",
        type=int,
        default=3,
        help="Number of past turns to include in history fields.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    log_dir: Path = args.log_dir
    battle_id: str = args.battle_id

    log_paths = find_log_files(log_dir, battle_id)
    event_strings = list(_iter_log_lines(log_paths))

    if not event_strings:
        raise RuntimeError(f"No events found for battle {battle_id}")

    target_turns = set(args.turn) if args.turn else None

    results = _collect_states(
        events=event_strings, target_turns=target_turns, past_turns=args.past_turns
    )

    payload = [
        {"turn": turn, "state": _turn_predictor_state_to_json(state)}
        for turn, state in results
    ]

    if len(payload) == 1:
        print(json.dumps(payload[0], indent=2))
    else:
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
