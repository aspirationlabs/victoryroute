import json
import os
from dataclasses import asdict
from enum import Enum
from typing import Any, Dict

from python.game.schema.battle_state import BattleState
from python.game.environment.battle_stream_store import BattleStreamStore


class ZeroShotPromptBuilder:
    def __init__(self, BattleStreamStore: BattleStreamStore):
        self._battle_stream_store = BattleStreamStore

    def _format_available_actions(self, state: BattleState) -> str:
        available_actions: Dict[str, Any] = {
            "moves": state.available_moves,
            "switches": state.available_switches,
            "can_mega": state.can_mega,
            "can_tera": state.can_tera,
            "can_dynamax": state.can_dynamax,
            "force_switch": state.force_switch,
            "team_preview": state.team_preview,
        }
        return json.dumps(available_actions)

    def _format_opponent_potential_actions(self, state: BattleState) -> str:
        actions_data = [
            asdict(action) for action in state.get_opponent_potential_actions()
        ]
        return json.dumps(
            actions_data,
            default=lambda obj: obj.value if isinstance(obj, Enum) else obj,
        )

    def _format_past_actions_from_store(
        self,
        our_player_id: str,
        opponent_player_id: str,
        past_turns: int = 3,
    ) -> str:
        actions = {
            player_id: self._battle_stream_store.get_past_battle_actions(
                player_id, past_turns
            )
            for player_id in [our_player_id, opponent_player_id]
        }

        all_turn_ids = sorted(
            set(actions[our_player_id].keys()) | set(actions[opponent_player_id].keys())
        )
        recent_turn_ids = (
            all_turn_ids[-past_turns:]
            if len(all_turn_ids) > past_turns
            else all_turn_ids
        )

        if not recent_turn_ids:
            return ""

        lines = ["<past_actions>"]
        for player_id in [our_player_id, opponent_player_id]:
            lines.append(f"<{player_id}>")
            for turn_id in recent_turn_ids:
                if turn_id in actions[player_id]:
                    for action in actions[player_id][turn_id]:
                        lines.append(
                            f"<turn_{turn_id}>{json.dumps(asdict(action), default=lambda obj: obj.value if isinstance(obj, Enum) else obj)}</turn_{turn_id}>"
                        )
            lines.append(f"</{player_id}>")
        lines.append("</past_actions>")
        return "\n".join(lines)

    def _format_past_raw_events(self, past_turns: int) -> str:
        raw_events_by_turn = self._battle_stream_store.get_past_raw_events(
            past_turns=past_turns
        )

        if not raw_events_by_turn:
            return ""

        lines = ["<past_server_events>"]

        for turn_id in sorted(raw_events_by_turn.keys()):
            events = raw_events_by_turn[turn_id]
            lines.append(f"<turn_{turn_id}>")
            for event_str in events:
                lines.append(f"<event>{event_str}</event>")
            lines.append(f"</turn_{turn_id}>")

        lines.append("</past_server_events>")

        return "\n".join(lines)

    def build_turn_context(
        self,
        state: BattleState,
        opponent_player_id,
    ) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(
            current_dir, "..", "prompts", "zero_shot_agent_turn_prompt.md"
        )

        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()

        available_moves_data = self._format_available_actions(state)
        opponent_actions_data = self._format_opponent_potential_actions(state)

        return (
            template.replace("{{TURN_NUMBER}}", str(state.field_state.turn_number))
            .replace("{{OUR_PLAYER_ID}}", str(state.our_player_id))
            .replace("{{AVAILABLE_ACTIONS}}", available_moves_data)
            .replace("{{BATTLE_STATE}}", str(state))
            .replace("{{OPPONENT_POTENTIAL_ACTIONS}}", opponent_actions_data)
            .replace(
                "{{PAST_ACTIONS}}",
                self._format_past_actions_from_store(
                    state.our_player_id, opponent_player_id
                ),
            )
            .replace("{{PAST_RAW_EVENTS}}", self._format_past_raw_events(past_turns=2))
            .replace("{{PAST_SERVER_COUNT}}", str(2))
            .replace("{{PAST_ACTIONS_COUNT}}", str(3))
        )
