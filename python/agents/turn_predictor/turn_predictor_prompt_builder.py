import json
import os
from dataclasses import asdict
from enum import Enum
from typing import Optional

from python.game.interface.battle_action import ActionType, BattleAction
from python.game.schema.battle_state import BattleState
from python.agents.turn_predictor.turn_predictor_state import TurnPredictorState
from python.game.environment.battle_stream_store import BattleStreamStore


class TurnPredictorPromptBuilder:
    def __init__(self, battle_stream_store: BattleStreamStore, mode: str = "gen9ou"):
        self._mode_rules = self._load_filename(f"modes/{mode}.md")
        self._team_predictor_prompt = self._load_filename("team_predictor_agent.md")
        self._initial_decision_prompt = self._load_filename("initial_decision_agent.md")
        self._decision_critique_prompt = self._load_filename(
            "decision_critique_agent.md"
        )
        self._final_decision_prompt = self._load_filename("final_decision_agent.md")
        self._battle_stream_store = battle_stream_store

    def _load_filename(self, filename: str) -> str:
        base_prompts_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "prompts"
        )
        candidate_paths = [
            os.path.join(base_prompts_dir, filename),
            os.path.join(base_prompts_dir, "turn_predictor", filename),
        ]

        for path in candidate_paths:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()

        raise FileNotFoundError(
            f"Prompt file '{filename}' not found in expected directories: {candidate_paths}"
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

    def get_system_instructions(self) -> str:
        return "\n".join([self._mode_rules, self._team_predictor_prompt])

    def get_team_predictor_system_prompt(self) -> str:
        return self._team_predictor_prompt

    def get_initial_decision_prompt(self) -> str:
        return self._initial_decision_prompt

    def get_decision_critique_prompt(self) -> str:
        return self._decision_critique_prompt

    def get_final_decision_prompt(self) -> str:
        return self._final_decision_prompt

    def get_new_turn_state_prompt(
        self, battle_state: BattleState, past_turns: int = 3
    ) -> TurnPredictorState:
        our_player_id = battle_state.our_player_id
        if our_player_id is None:
            raise ValueError("battle_state.our_player_id must be set")

        opponent_player_id: Optional[str] = next(
            (
                player_id
                for player_id in battle_state.player_usernames.keys()
                if player_id != our_player_id
            ),
            None,
        )
        if opponent_player_id is None:
            raise ValueError("Opponent player id not found in battle_state")

        opponent_active_pokemon = battle_state.get_team(
            opponent_player_id
        ).get_active_pokemon()
        if opponent_active_pokemon is None:
            raise ValueError("Opponent active pokemon is required")

        # Convert available moves and switches to BattleAction objects
        available_actions = []

        # Add move actions
        if battle_state.available_moves:
            for move in battle_state.available_moves:
                available_actions.append(
                    BattleAction(action_type=ActionType.MOVE, move_name=move)
                )

        # Add switch actions
        if battle_state.available_switches:
            our_team = battle_state.get_team(our_player_id)
            for switch_index in battle_state.available_switches:
                if 0 <= switch_index < len(our_team.pokemon):
                    pokemon_name = our_team.pokemon[switch_index].species
                    available_actions.append(
                        BattleAction(
                            action_type=ActionType.SWITCH,
                            switch_pokemon_name=pokemon_name,
                        )
                    )

        return TurnPredictorState(
            our_player_id=our_player_id,
            turn_number=battle_state.field_state.turn_number,
            opponent_active_pokemon=opponent_active_pokemon,
            past_battle_event_logs=self._format_past_raw_events(past_turns=past_turns),
            past_player_actions=self._format_past_actions_from_store(
                our_player_id, opponent_player_id, past_turns=past_turns
            ),
            available_actions=available_actions,
            battle_state=battle_state,
        )
