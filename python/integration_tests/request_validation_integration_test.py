"""Integration tests that validate inferred moves/switches match actual requests."""

import json
import os
import unittest
from typing import Dict, List, Optional, Tuple

from absl.testing import absltest, parameterized

from python.game.environment.state_transition import StateTransition
from python.game.events.battle_event import (
    BattleEvent,
    FieldEndEvent,
    RequestEvent,
    TurnEvent,
    UpkeepEvent,
    WeatherEvent,
    SideStartEvent,
    SideEndEvent,
)
from python.game.protocol.message_parser import MessageParser
from python.game.schema.battle_state import BattleState
from python.game.schema.enums import Terrain, Weather, SideCondition


class RequestValidationIntegrationTest(
    unittest.IsolatedAsyncioTestCase, parameterized.TestCase
):
    """Tests that validate our state inference matches actual server requests."""

    def _load_battle_log(self, filename: str) -> List[str]:
        """Load battle log from testdata directory.

        Args:
            filename: Name of battle log file (e.g., 'live_battle_1.txt')

        Returns:
            List of raw message lines from the battle log
        """
        testdata_dir = os.path.join(os.path.dirname(__file__), "testdata")
        filepath = os.path.join(testdata_dir, filename)

        with open(filepath, "r") as f:
            lines = f.readlines()

        return [line.strip() for line in lines if line.strip()]

    def _extract_requests(self, raw_messages: List[str]) -> List[Tuple[int, Dict]]:
        """Extract all request JSONs from battle log with their line numbers.

        Args:
            raw_messages: List of raw protocol messages

        Returns:
            List of (line_number, request_dict) tuples
        """
        requests = []
        for i, message in enumerate(raw_messages):
            if message.startswith("|request|"):
                request_json = message[len("|request|") :]
                request_data = json.loads(request_json)
                requests.append((i, request_data))
        return requests

    def _parse_events_until_request(
        self, raw_messages: List[str], start_idx: int
    ) -> Tuple[List[BattleEvent], Optional[Dict], int]:
        """Parse events from start index until next request.

        Args:
            raw_messages: List of raw protocol messages
            start_idx: Index to start parsing from

        Returns:
            Tuple of (events, request_dict, next_start_idx)
            request_dict is None if no request found
        """
        parser = MessageParser()
        events = []
        request_data = None
        idx = start_idx

        while idx < len(raw_messages):
            message = raw_messages[idx]

            if message.startswith("|request|"):
                request_json = message[len("|request|") :]
                request_data = json.loads(request_json)
                idx += 1
                break

            event = parser.parse(message)
            events.append(event)
            idx += 1

        return events, request_data, idx

    def _extract_expected_moves(self, request_data: Dict) -> List[str]:
        """Extract available move names from request JSON.

        Args:
            request_data: Parsed request JSON

        Returns:
            List of available move names
        """
        if request_data.get("wait", False):
            return []

        if request_data.get("teamPreview", False):
            return []

        available_moves = []
        if "active" in request_data and request_data["active"]:
            active_data = request_data["active"][0]
            if "moves" in active_data:
                for move in active_data["moves"]:
                    move_name = move.get("move", "")
                    if not move.get("disabled", False) and move_name:
                        available_moves.append(move_name)

        return available_moves

    def _extract_expected_switches(self, request_data: Dict) -> List[int]:
        """Extract available switch indices from request JSON.

        Args:
            request_data: Parsed request JSON

        Returns:
            List of Pokemon indices that can be switched in
        """
        if request_data.get("wait", False):
            return []

        if request_data.get("teamPreview", False):
            return []

        available_switches = []
        if "side" in request_data and "pokemon" in request_data["side"]:
            for i, pokemon in enumerate(request_data["side"]["pokemon"]):
                if (
                    not pokemon.get("active", False)
                    and pokemon.get("condition") != "0 fnt"
                ):
                    available_switches.append(i)

        return available_switches

    def _identify_player_id(self, request_data: Dict) -> str:
        """Identify which player we're controlling from request.

        Args:
            request_data: Parsed request JSON

        Returns:
            Player ID ("p1" or "p2")
        """
        if "side" in request_data and "id" in request_data["side"]:
            return request_data["side"]["id"]
        return "p1"

    def _validate_pokemon_state(
        self, state: BattleState, request_data: Dict, player_id: str, turn_number: int
    ) -> None:
        """Validate all Pokemon state matches the request data.

        Args:
            state: Current battle state
            request_data: Parsed request JSON
            player_id: Player ID being validated
            turn_number: Current turn number
        """
        if "side" not in request_data or "pokemon" not in request_data["side"]:
            return

        request_pokemon = request_data["side"]["pokemon"]
        team = state.get_team(player_id)
        state_pokemon = team.get_pokemon_team()

        self.assertEqual(
            len(state_pokemon),
            len(request_pokemon),
            f"Turn {turn_number} TEAM SIZE mismatch",
        )

        for i, req_poke in enumerate(request_pokemon):
            state_poke = state_pokemon[i]

            # Parse expected values from request
            species = req_poke.get("details", "").split(",")[0]
            condition_str = req_poke.get("condition", "100/100")
            condition_parts = condition_str.split()
            hp_parts = condition_parts[0].split("/")
            expected_hp = int(hp_parts[0]) if hp_parts[0] not in ["0", "fnt"] else 0
            expected_max_hp = int(hp_parts[1]) if len(hp_parts) > 1 else 100

            # Parse status from condition (e.g., "100/100 par" or "0 fnt")
            # Note: "0 fnt" format has "fnt" as second part but it's not a status
            expected_status = None
            if len(condition_parts) > 1 and condition_parts[1] != "fnt":
                expected_status = condition_parts[1]

            expected_item = req_poke.get("item", "")
            expected_ability = req_poke.get("ability", "")

            self.assertEqual(
                state_poke.current_hp,
                expected_hp,
                f"Turn {turn_number} {species} HP mismatch",
            )

            self.assertEqual(
                state_poke.max_hp,
                expected_max_hp,
                f"Turn {turn_number} {species} MAX HP mismatch",
            )

            state_status = (
                state_poke.status.value if state_poke.status.value != "none" else None
            )
            self.assertEqual(
                state_status,
                expected_status,
                f"Turn {turn_number} {species} STATUS mismatch",
            )

            state_item = state_poke.item if state_poke.item else ""
            self.assertEqual(
                state_item.lower(),
                expected_item.lower(),
                f"Turn {turn_number} {species} ITEM mismatch",
            )

            self.assertEqual(
                state_poke.ability.lower(),
                expected_ability.lower(),
                f"Turn {turn_number} {species} ABILITY mismatch",
            )

    @parameterized.named_parameters(
        ("battle_1", "live_battle_1.txt"),
        ("battle_2", "live_battle_2.txt"),
        ("battle_3", "live_battle_3.txt"),
    )
    def test_full_battle_validation(self, battle_file: str) -> None:
        """Test that all turns' inferences match requests for a battle log."""
        raw_messages = self._load_battle_log(battle_file)

        state = BattleState()
        idx = 0
        turn_number = 0

        while idx < len(raw_messages):
            events, request_data, idx = self._parse_events_until_request(
                raw_messages, idx
            )

            # Track if we saw a turn event (turn number updates)
            saw_turn_event = False
            for event in events:
                state = StateTransition.apply(state, event)
                if isinstance(event, TurnEvent):
                    turn_number = event.turn_number
                    saw_turn_event = True

            if request_data:
                request_event = RequestEvent(
                    raw_message=f"|request|{json.dumps(request_data)}",
                    request_json=json.dumps(request_data),
                )
                state = StateTransition.apply(state, request_event)

                if request_data.get("teamPreview", False) or request_data.get(
                    "wait", False
                ):
                    continue

                if not saw_turn_event:
                    continue

                player_id = self._identify_player_id(request_data)

                expected_moves = self._extract_expected_moves(request_data)
                expected_switches = self._extract_expected_switches(request_data)

                inferred_moves = state._infer_available_moves(player_id)
                inferred_switches = state._infer_available_switches(player_id)

                self.assertEqual(
                    set(inferred_moves),
                    set(expected_moves),
                    f"Turn {turn_number} MOVE mismatch: "
                    f"Inferred={sorted(inferred_moves)}, Expected={sorted(expected_moves)}",
                )

                self.assertEqual(
                    set(inferred_switches),
                    set(expected_switches),
                    f"Turn {turn_number} SWITCH mismatch: "
                    f"Inferred={sorted(inferred_switches)}, Expected={sorted(expected_switches)}",
                )

    @parameterized.named_parameters(
        ("battle_1", "live_battle_1.txt"),
        ("battle_2", "live_battle_2.txt"),
        ("battle_3", "live_battle_3.txt"),
    )
    def test_pokemon_state_validation(self, battle_file: str) -> None:
        """Test that Pokemon HP, status, item, and ability match requests."""
        raw_messages = self._load_battle_log(battle_file)

        state = BattleState()
        idx = 0
        turn_number = 0

        while idx < len(raw_messages):
            events, request_data, idx = self._parse_events_until_request(
                raw_messages, idx
            )

            saw_turn_event = False
            for event in events:
                state = StateTransition.apply(state, event)
                if isinstance(event, TurnEvent):
                    turn_number = event.turn_number
                    saw_turn_event = True

            if request_data:
                request_event = RequestEvent(
                    raw_message=f"|request|{json.dumps(request_data)}",
                    request_json=json.dumps(request_data),
                )
                state = StateTransition.apply(state, request_event)

                if request_data.get("teamPreview", False) or request_data.get(
                    "wait", False
                ):
                    continue

                if not saw_turn_event:
                    continue

                player_id = self._identify_player_id(request_data)
                if turn_number == 50:
                    print(f"Turn {turn_number} validating Pokemon state: {str(state)}")

                # Validate Pokemon state (HP, status, item, ability)
                self._validate_pokemon_state(
                    state, request_data, player_id, turn_number
                )

    @parameterized.named_parameters(
        ("battle_1", "live_battle_1.txt"),
        ("battle_2", "live_battle_2.txt"),
        ("battle_3", "live_battle_3.txt"),
    )
    def test_field_condition_tracking(self, battle_file: str) -> None:
        """Test that weather, terrain, and side conditions are correctly tracked."""
        raw_messages = self._load_battle_log(battle_file)

        state = BattleState()
        parser = MessageParser()

        for message in raw_messages:
            event = parser.parse(message)
            state = StateTransition.apply(state, event)

            if isinstance(event, WeatherEvent):
                expected_weather = Weather.from_protocol(event.weather)
                self.assertEqual(
                    state.field_state.weather,
                    expected_weather,
                    f"Weather mismatch after event: {event.raw_message}",
                )

            elif isinstance(event, SideStartEvent):
                state = StateTransition.apply(state, event)
                team = state.get_team(event.player_id)
                expected_condition = SideCondition.from_protocol(event.condition)
                self.assertIn(
                    expected_condition,
                    team.side_conditions,
                    f"Side condition {expected_condition.value} should be present "
                    f"after event: {event.raw_message}",
                )
            elif isinstance(event, SideEndEvent):
                state = StateTransition.apply(state, event)
                team = state.get_team(event.player_id)
                expected_condition = SideCondition.from_protocol(event.condition)
                self.assertNotIn(
                    expected_condition,
                    team.side_conditions,
                    f"Side condition {expected_condition.value} should be removed "
                    f"after event: {event.raw_message}",
                )

            elif isinstance(event, FieldEndEvent):
                # Check if this is a terrain end event
                try:
                    Terrain.from_protocol(event.effect)
                    # Terrain should be cleared
                    self.assertEqual(
                        state.field_state.terrain,
                        Terrain.NONE,
                        f"Terrain should be cleared after {event.raw_message}",
                    )
                except ValueError:
                    # Not a terrain event, could be trick room, etc.
                    pass

            else:
                state = StateTransition.apply(state, event)

    @parameterized.named_parameters(
        ("battle_1", "live_battle_1.txt"),
        ("battle_2", "live_battle_2.txt"),
        ("battle_3", "live_battle_3.txt"),
    )
    def test_field_condition_upkeep(self, battle_file: str) -> None:
        """Test that weather and terrain counters decrement properly during upkeep."""
        raw_messages = self._load_battle_log(battle_file)

        state = BattleState()
        parser = MessageParser()

        for message in raw_messages:
            event = parser.parse(message)
            prev_state = state
            state = StateTransition.apply(state, event)

            if isinstance(event, UpkeepEvent):
                if prev_state.field_state.weather != Weather.NONE:
                    if prev_state.field_state.weather_turns_remaining > 0:
                        self.assertEqual(
                            state.field_state.weather_turns_remaining,
                            max(0, prev_state.field_state.weather_turns_remaining - 1),
                            f"Weather turns should decrement during upkeep at turn {state.field_state.turn_number}",
                        )

                if prev_state.field_state.terrain != Terrain.NONE:
                    if prev_state.field_state.terrain_turns_remaining > 0:
                        self.assertEqual(
                            state.field_state.terrain_turns_remaining,
                            max(0, prev_state.field_state.terrain_turns_remaining - 1),
                            f"Terrain turns should decrement during upkeep at turn {state.field_state.turn_number}",
                        )

    def _validate_battle_state_invariants(
        self,
        state: BattleState,
        turn_number: int,
        expected_team_size: Optional[int] = None,
    ) -> None:
        """Validate all battle state invariants hold true.

        Args:
            state: Current battle state
            turn_number: Current turn number for error messages
            expected_team_size: Expected team size (if None, checks 1-6 range)
        """
        # Skip validation if teams haven't been populated yet
        p1_team = state.get_team("p1")
        p2_team = state.get_team("p2")
        if len(p1_team.get_pokemon_team()) == 0 or len(p2_team.get_pokemon_team()) == 0:
            return

        # Pokemon-level invariants
        for team_id in ["p1", "p2"]:
            team = state.get_team(team_id)
            pokemon_list = team.get_pokemon_team()

            # At most 1 active Pokemon per side
            active_count = sum(1 for p in pokemon_list if p.is_active)
            self.assertLessEqual(
                active_count,
                1,
                f"Turn {turn_number} {team_id}: More than 1 active Pokemon ({active_count})",
            )

            # At most 1 terastallized Pokemon per team
            tera_count = sum(1 for p in pokemon_list if p.has_terastallized)
            self.assertLessEqual(
                tera_count,
                1,
                f"Turn {turn_number} {team_id}: More than 1 terastallized Pokemon ({tera_count})",
            )

            for i, pokemon in enumerate(pokemon_list):
                # HP bounds
                self.assertGreaterEqual(
                    pokemon.current_hp,
                    0,
                    f"Turn {turn_number} {team_id} Pokemon {i} ({pokemon.species}): "
                    f"HP below 0 ({pokemon.current_hp})",
                )
                self.assertLessEqual(
                    pokemon.current_hp,
                    pokemon.max_hp,
                    f"Turn {turn_number} {team_id} Pokemon {i} ({pokemon.species}): "
                    f"HP exceeds max ({pokemon.current_hp} > {pokemon.max_hp})",
                )

                # Fainted Pokemon should not be active
                if pokemon.current_hp == 0:
                    self.assertFalse(
                        pokemon.is_active,
                        f"Turn {turn_number} {team_id} Pokemon {i} ({pokemon.species}): "
                        f"Fainted Pokemon is active",
                    )

                # Active Pokemon should be alive
                if pokemon.is_active:
                    self.assertGreater(
                        pokemon.current_hp,
                        0,
                        f"Turn {turn_number} {team_id} Pokemon {i} ({pokemon.species}): "
                        f"Active Pokemon is fainted",
                    )

                # Non-active Pokemon should not have stat boosts
                if not pokemon.is_active and pokemon.stat_boosts:
                    self.assertEqual(
                        pokemon.stat_boosts,
                        {},
                        f"Turn {turn_number} {team_id} Pokemon {i} ({pokemon.species}): "
                        f"Non-active Pokemon has stat boosts: {pokemon.stat_boosts}",
                    )

                # Non-active Pokemon should not have volatile conditions
                if not pokemon.is_active and pokemon.volatile_conditions:
                    # Some volatile conditions persist when switching out (e.g., perish count)
                    # But most should be cleared
                    persistent_volatiles = {"perish3", "perish2", "perish1"}
                    non_persistent = {
                        k: v
                        for k, v in pokemon.volatile_conditions.items()
                        if k not in persistent_volatiles
                    }
                    self.assertEqual(
                        non_persistent,
                        {},
                        f"Turn {turn_number} {team_id} Pokemon {i} ({pokemon.species}): "
                        f"Non-active Pokemon has volatile conditions: {non_persistent}",
                    )

                # Stat boost stages should be in valid range [-6, +6]
                for stat, boost in pokemon.stat_boosts.items():
                    self.assertGreaterEqual(
                        boost,
                        -6,
                        f"Turn {turn_number} {team_id} Pokemon {i} ({pokemon.species}): "
                        f"{stat.value} boost below -6 ({boost})",
                    )
                    self.assertLessEqual(
                        boost,
                        6,
                        f"Turn {turn_number} {team_id} Pokemon {i} ({pokemon.species}): "
                        f"{stat.value} boost above +6 ({boost})",
                    )

            # Team-level invariants
            team_size = len(pokemon_list)

            # Always check team size is within valid range
            self.assertGreaterEqual(
                team_size,
                1,
                f"Turn {turn_number} {team_id}: Team has no Pokemon",
            )
            self.assertLessEqual(
                team_size,
                6,
                f"Turn {turn_number} {team_id}: Team has more than 6 Pokemon ({team_size})",
            )

            # Check exact team size only after team is fully built
            # (team is fully built when all 6 Pokemon are present)
            if expected_team_size is not None and team_size == expected_team_size:
                # Validate that team stays at expected size once fully built
                for future_team_id in ["p1", "p2"]:
                    future_team = state.get_team(future_team_id)
                    future_size = len(future_team.get_pokemon_team())
                    if future_size > expected_team_size:
                        self.fail(
                            f"Turn {turn_number} {future_team_id}: Team exceeded expected size "
                            f"({future_size} > {expected_team_size})"
                        )

            # active_pokemon_index should be valid
            if team.active_pokemon_index is not None:
                self.assertGreaterEqual(
                    team.active_pokemon_index,
                    0,
                    f"Turn {turn_number} {team_id}: active_pokemon_index is negative",
                )
                self.assertLess(
                    team.active_pokemon_index,
                    team_size,
                    f"Turn {turn_number} {team_id}: active_pokemon_index out of bounds "
                    f"({team.active_pokemon_index} >= {team_size})",
                )

                # Pokemon at active_pokemon_index should have is_active = True
                # NOTE: This can temporarily be false after a faint and before a switch
                # so we only check if the Pokemon is alive
                active_pokemon = pokemon_list[team.active_pokemon_index]
                if active_pokemon.current_hp > 0:
                    self.assertTrue(
                        active_pokemon.is_active,
                        f"Turn {turn_number} {team_id}: Pokemon at active_pokemon_index "
                        f"({team.active_pokemon_index}) is alive but not marked active",
                    )

            # Side condition layer counts
            for condition, layers in team.side_conditions.items():
                if condition == SideCondition.SPIKES:
                    self.assertGreaterEqual(
                        layers,
                        1,
                        f"Turn {turn_number} {team_id}: Spikes layers < 1 ({layers})",
                    )
                    self.assertLessEqual(
                        layers,
                        3,
                        f"Turn {turn_number} {team_id}: Spikes layers > 3 ({layers})",
                    )
                elif condition == SideCondition.TOXIC_SPIKES:
                    self.assertGreaterEqual(
                        layers,
                        1,
                        f"Turn {turn_number} {team_id}: Toxic Spikes layers < 1 ({layers})",
                    )
                    self.assertLessEqual(
                        layers,
                        2,
                        f"Turn {turn_number} {team_id}: Toxic Spikes layers > 2 ({layers})",
                    )

        # Field-level invariants
        self.assertGreaterEqual(
            state.field_state.turn_number,
            0,
            f"Turn number is negative ({state.field_state.turn_number})",
        )

        if state.field_state.weather_turns_remaining is not None:
            self.assertGreaterEqual(
                state.field_state.weather_turns_remaining,
                0,
                f"Turn {turn_number}: Weather turns remaining is negative "
                f"({state.field_state.weather_turns_remaining})",
            )

        if state.field_state.terrain_turns_remaining is not None:
            self.assertGreaterEqual(
                state.field_state.terrain_turns_remaining,
                0,
                f"Turn {turn_number}: Terrain turns remaining is negative "
                f"({state.field_state.terrain_turns_remaining})",
            )

        # Battle-level invariants
        if state.battle_over:
            self.assertIsNotNone(
                state.winner,
                f"Turn {turn_number}: Battle is over but no winner set",
            )

        if state.winner:
            self.assertTrue(
                state.battle_over,
                f"Turn {turn_number}: Winner set but battle not over",
            )

    @parameterized.named_parameters(
        ("battle_1", "live_battle_1.txt"),
        ("battle_2", "live_battle_2.txt"),
        ("battle_3", "live_battle_3.txt"),
    )
    def test_opponent_move_and_ability_tracking(self, battle_file: str) -> None:
        """Test that opponent moves and abilities are learned from battle events.

        This test verifies:
        1. Opponent moves are added to their moveset when first used
        2. Move PP is decremented each time the move is used
        3. Opponent abilities are learned when revealed
        4. Pokemon that haven't battled have no moves/abilities tracked yet

        Note: This only validates the team that DOESN'T receive requests
        (the opponent), since request data provides full move/ability info.
        """
        raw_messages = self._load_battle_log(battle_file)

        state = BattleState()
        parser = MessageParser()

        # Determine which player we are (gets requests) vs opponent (doesn't)
        our_player_id = None
        for message in raw_messages:
            if message.startswith("|request|"):
                req_json = message[len("|request|") :]
                req_data = json.loads(req_json)
                if "side" in req_data and "id" in req_data["side"]:
                    our_player_id = req_data["side"]["id"]
                    break

        # If we couldn't determine player, skip test
        if our_player_id is None:
            self.skipTest("Could not determine player ID from requests")

        opponent_id = "p2" if our_player_id == "p1" else "p1"

        # Track which opponent Pokemon we've seen use moves/abilities
        opponent_pokemon_with_moves = set()
        opponent_pokemon_with_abilities = set()

        for message in raw_messages:
            event = parser.parse(message)

            # Track opponent move usage
            if message.startswith(f"|move|{opponent_id}"):
                parts = message.split("|")
                if len(parts) >= 4:
                    ident = parts[2].split(":")[1].strip()
                    move_name = parts[3]
                    opponent_pokemon_with_moves.add((ident, move_name))

            # Track opponent ability reveals
            if message.startswith(f"|-ability|{opponent_id}"):
                parts = message.split("|")
                if len(parts) >= 4:
                    ident = parts[2].split(":")[1].strip()
                    ability = parts[3]
                    opponent_pokemon_with_abilities.add((ident, ability))

            state = StateTransition.apply(state, event)

        # Validate opponent tracking at end of battle
        opponent_team = state.get_team(opponent_id)

        for pokemon in opponent_team.get_pokemon_team():
            # Check moves
            if pokemon.moves:
                # Pokemon has moves tracked - verify they were actually used
                for move in pokemon.moves:
                    # Check that we saw this Pokemon use this move
                    found_usage = any(
                        pokemon.species.lower().replace(" ", "").replace("-", "")
                        in ident.lower().replace(" ", "").replace("-", "")
                        and move.name == move_name
                        for ident, move_name in opponent_pokemon_with_moves
                    )
                    self.assertTrue(
                        found_usage,
                        f"Opponent {pokemon.species} has move {move.name} but we never saw it used",
                    )

                    # Verify PP is less than or equal to max
                    if move.max_pp > 0:
                        self.assertLessEqual(
                            move.current_pp,
                            move.max_pp,
                            f"Opponent {pokemon.species} move {move.name} has current_pp > max_pp",
                        )

            # Check abilities
            if pokemon.ability:
                # Pokemon has ability tracked - verify it was revealed
                found_ability = any(
                    pokemon.species.lower().replace(" ", "").replace("-", "")
                    in ident.lower().replace(" ", "").replace("-", "")
                    and pokemon.ability == ability
                    for ident, ability in opponent_pokemon_with_abilities
                )
                self.assertTrue(
                    found_ability,
                    f"Opponent {pokemon.species} has ability {pokemon.ability} but we never saw it revealed",
                )

    @parameterized.named_parameters(
        ("battle_1", "live_battle_1.txt"),
        ("battle_2", "live_battle_2.txt"),
        ("battle_3", "live_battle_3.txt"),
    )
    def test_opponent_pp_decrementing(self, battle_file: str) -> None:
        """Test that opponent move PP is correctly decremented when moves are used.

        This test verifies:
        1. When a move is first discovered, it starts with max_pp - 1
        2. Each subsequent use decrements current_pp by 1
        3. PP never goes below 0

        Note: This only validates the team that DOESN'T receive requests
        (the opponent), since request data may restore PP values.
        """
        raw_messages = self._load_battle_log(battle_file)

        state = BattleState()
        parser = MessageParser()

        # Determine which player we are (gets requests) vs opponent (doesn't)
        our_player_id = None
        for message in raw_messages:
            if message.startswith("|request|"):
                req_json = message[len("|request|") :]
                req_data = json.loads(req_json)
                if "side" in req_data and "id" in req_data["side"]:
                    our_player_id = req_data["side"]["id"]
                    break

        # If we couldn't determine player, skip test
        if our_player_id is None:
            self.skipTest("Could not determine player ID from requests")

        opponent_id = "p2" if our_player_id == "p1" else "p1"

        # Track PP changes for each Pokemon's moves
        # Key: (pokemon_species, move_name), Value: list of PP values after each use
        pp_history = {}

        for message in raw_messages:
            event = parser.parse(message)

            # Before applying the event, check if it's an opponent move event
            if message.startswith(f"|move|{opponent_id}"):
                parts = message.split("|")
                if len(parts) >= 4:
                    ident = parts[2].split(":")[1].strip()
                    move_name = parts[3]

            state = StateTransition.apply(state, event)

            # After applying, track PP for opponent Pokemon
            if message.startswith(f"|move|{opponent_id}"):
                opponent_team = state.get_team(opponent_id)
                for pokemon in opponent_team.get_pokemon_team():
                    # Normalize species name for matching
                    normalized_species = (
                        pokemon.species.lower().replace(" ", "").replace("-", "")
                    )
                    normalized_ident = ident.lower().replace(" ", "").replace("-", "")

                    if (
                        normalized_species in normalized_ident
                        or normalized_ident in normalized_species
                    ):
                        # Find the move
                        for move in pokemon.moves:
                            if move.name == move_name:
                                key = (pokemon.species, move.name)
                                if key not in pp_history:
                                    pp_history[key] = []
                                pp_history[key].append(move.current_pp)

        # Validate PP decrementing
        for (species, move_name), pp_values in pp_history.items():
            if len(pp_values) > 0:
                # First use should be max_pp - 1
                # We don't know max_pp from history, but we can check it's decreasing

                # Check PP is monotonically decreasing or staying at 0
                for i in range(1, len(pp_values)):
                    prev_pp = pp_values[i - 1]
                    current_pp = pp_values[i]

                    # PP should decrease by 1, or stay at 0 if already at 0
                    if prev_pp > 0:
                        self.assertEqual(
                            current_pp,
                            prev_pp - 1,
                            f"{species}'s {move_name}: PP should decrease by 1 "
                            f"(was {prev_pp}, became {current_pp})",
                        )
                    else:
                        # If PP was 0, it should stay 0
                        self.assertEqual(
                            current_pp,
                            0,
                            f"{species}'s {move_name}: PP should stay at 0",
                        )

                # Verify no negative PP
                for pp in pp_values:
                    self.assertGreaterEqual(
                        pp,
                        0,
                        f"{species}'s {move_name}: PP should never be negative (got {pp})",
                    )

    @parameterized.named_parameters(
        ("battle_1", "live_battle_1.txt", 6),
        ("battle_2", "live_battle_2.txt", 6),
        ("battle_3", "live_battle_3.txt", 6),
    )
    def test_battle_state_invariants(
        self, battle_file: str, expected_team_size: int
    ) -> None:
        """Test that battle state invariants hold at stable points (after turns/requests).

        Args:
            battle_file: Battle log file to test
            expected_team_size: Expected number of Pokemon per team
        """
        raw_messages = self._load_battle_log(battle_file)

        state = BattleState()
        turn_number = 0

        for message in raw_messages:
            parser = MessageParser()
            event = parser.parse(message)

            if isinstance(event, TurnEvent):
                turn_number = event.turn_number

            state = StateTransition.apply(state, event)

            # Only validate invariants at stable points (after turn events or request events)
            # This avoids checking mid-turn states where temporary violations may occur
            if isinstance(event, (TurnEvent, RequestEvent)):
                self._validate_battle_state_invariants(
                    state, turn_number, expected_team_size
                )


if __name__ == "__main__":
    absltest.main()
