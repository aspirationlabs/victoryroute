"""Integration tests for BattleEnvironment using real battle logs."""

import os
import unittest
from typing import Any, Dict, List, Tuple

from absl.testing import absltest, parameterized

from python.game.environment.state_transition import StateTransition
from python.game.events.battle_event import (
    BattleEvent,
    FaintEvent,
    BattleEndEvent,
    PlayerEvent,
)
from python.game.interface.battle_action import ActionType
from python.game.protocol.message_parser import MessageParser
from python.game.schema.battle_state import BattleState


class BattleEnvironmentIntegrationTest(
    unittest.IsolatedAsyncioTestCase, parameterized.TestCase
):
    """Integration tests that replay full battle logs."""

    def _load_battle_log(self, filename: str) -> List[str]:
        """Load battle log from testdata directory.

        Args:
            filename: Name of battle log file (e.g., 'battle1.txt')

        Returns:
            List of raw message lines from the battle log
        """
        testdata_dir = os.path.join(os.path.dirname(__file__), "testdata")
        filepath = os.path.join(testdata_dir, filename)

        with open(filepath, "r") as f:
            lines = f.readlines()

        return [line.strip() for line in lines if line.strip()]

    def _parse_events(self, raw_messages: List[str]) -> List[BattleEvent]:
        """Parse raw battle log messages into BattleEvent objects.

        Args:
            raw_messages: List of raw protocol messages

        Returns:
            List of parsed BattleEvent objects
        """
        parser = MessageParser()
        events = []

        for message in raw_messages:
            event = parser.parse(message)
            events.append(event)

        return events

    def _replay_battle(
        self, events: List[BattleEvent]
    ) -> Tuple[BattleState, List[Tuple[BattleEvent, BattleState]]]:
        """Replay all events and track state transitions.

        Args:
            events: List of BattleEvent objects to process

        Returns:
            Tuple of (final_state, list of (event, state_after_event) pairs)
        """
        state = BattleState()
        history = []

        for event in events:
            state = StateTransition.apply(state, event)
            history.append((event, state))

        return state, history

    def _get_faint_events(
        self, history: List[Tuple[BattleEvent, BattleState]]
    ) -> List[Tuple[FaintEvent, BattleState]]:
        """Extract faint events and their resulting states from history.

        Args:
            history: List of (event, state) tuples

        Returns:
            List of (FaintEvent, state_after_faint) tuples
        """
        faint_history = []
        for event, state in history:
            if isinstance(event, FaintEvent):
                faint_history.append((event, state))
        return faint_history

    def _verify_pokemon_fainted(
        self,
        state: BattleState,
        player_id: str,
        pokemon_name: str,
    ) -> None:
        """Verify that a specific pokemon has fainted.

        Args:
            state: Battle state to check
            player_id: Player ID (p1 or p2)
            pokemon_name: Name of the pokemon that should be fainted
        """
        team = state.get_team(player_id)
        found = False

        for pokemon in team.get_pokemon_team():
            # Handle species variations like zoroark-hisui vs zoroark
            species_base = pokemon.species.split("-")[0].lower()
            pokemon_name_base = pokemon_name.split("-")[0].lower()

            matches_name = (
                pokemon.species.lower() == pokemon_name.lower()
                or species_base == pokemon_name_base
                or (
                    pokemon.nickname
                    and pokemon.nickname.lower() == pokemon_name.lower()
                )
            )

            if matches_name:
                found = True
                self.assertEqual(
                    0,
                    pokemon.current_hp,
                    f"Pokemon {pokemon_name} should have 0 HP but has {pokemon.current_hp}",
                )
                self.assertFalse(
                    pokemon.is_alive(),
                    f"Pokemon {pokemon_name} should not be alive",
                )

        self.assertTrue(
            found,
            f"Pokemon {pokemon_name} not found in {player_id} team",
        )

    def _verify_battle_ended(
        self, final_state: BattleState, expected_winner: str
    ) -> None:
        """Verify that the battle has ended correctly.

        Args:
            final_state: Final battle state
            expected_winner: Expected winner player ID (p1 or p2)
        """
        # Check that at least one team has all pokemon fainted
        p1_team = final_state.get_team("p1")
        p2_team = final_state.get_team("p2")

        p1_alive = any(p.is_alive() for p in p1_team.get_pokemon_team())
        p2_alive = any(p.is_alive() for p in p2_team.get_pokemon_team())

        # At least one team should have no alive pokemon
        self.assertFalse(
            p1_alive and p2_alive,
            "Battle ended but both teams still have alive pokemon",
        )

        # Verify the expected winner has alive pokemon (or the loser has none)
        if expected_winner == "p1":
            self.assertFalse(
                p2_alive,
                "Player 1 won but Player 2 still has alive pokemon",
            )
        elif expected_winner == "p2":
            self.assertFalse(
                p1_alive,
                "Player 2 won but Player 1 still has alive pokemon",
            )

    @parameterized.named_parameters(
        ("battle1", "battle1.txt"),
        ("battle2", "battle2.txt"),
        ("battle3", "battle3.txt"),
        ("battle5", "battle5.txt"),
        ("battle9", "battle9.txt"),
        ("battle10", "battle10.txt"),
        ("battle11", "battle11.txt"),
        ("battle12", "battle12.txt"),
        ("battle13", "battle13.txt"),
    )
    def test_battle_replay(self, battle_file: str) -> None:
        """Test replaying a complete battle and verifying state transitions.

        Args:
            battle_file: Name of battle log file to replay
        """
        raw_messages = self._load_battle_log(battle_file)
        events = self._parse_events(raw_messages)

        final_state, history = self._replay_battle(events)

        faint_events = self._get_faint_events(history)

        for faint_event, state_after_faint in faint_events:
            self._verify_pokemon_fainted(
                state_after_faint,
                faint_event.player_id,
                faint_event.pokemon_name,
            )

        winner = None
        for event, _ in history:
            if isinstance(event, BattleEndEvent):
                winner = event.winner
                break
        player_map = {}
        for event, _ in history:
            if isinstance(event, PlayerEvent):
                player_map[event.username] = event.player_id

        winner_player_id = player_map.get(winner, winner)
        self._verify_battle_ended(final_state, winner_player_id)
        p1_all_fainted = all(
            not p.is_alive() for p in final_state.get_team("p1").get_pokemon_team()
        )
        p2_all_fainted = all(
            not p.is_alive() for p in final_state.get_team("p2").get_pokemon_team()
        )

        self.assertTrue(
            p1_all_fainted or p2_all_fainted,
            "Battle ended but no team has all fainted pokemon",
        )

    @parameterized.named_parameters(
        (
            "battle1",
            "battle1.txt",
            {
                1: {
                    "moves": set(),
                    "switches": {
                        "Kingambit",
                        "Dragonite",
                        "Enamorus",
                        "Gholdengo",
                        "Rotom-Wash",
                    },
                },
                2: {
                    "moves": {"Stealth Rock"},
                    "switches": {
                        "Kingambit",
                        "Dragonite",
                        "Enamorus",
                        "Gholdengo",
                        "Rotom-Wash",
                    },
                },
                4: {
                    "moves": {"Shadow Ball"},
                    "switches": {
                        "Kingambit",
                        "Dragonite",
                        "Enamorus",
                        "Kommo-o",
                        "Rotom-Wash",
                    },
                },
                6: {
                    "moves": {"Hydro Pump", "Volt Switch"},
                    "switches": {
                        "Kingambit",
                        "Dragonite",
                        "Enamorus",
                        "Kommo-o",
                        "Gholdengo",
                    },
                },
                8: {
                    "moves": {"Substitute", "Moonblast"},
                    "switches": {
                        "Kingambit",
                        "Dragonite",
                        "Kommo-o",
                        "Gholdengo",
                        "Rotom-Wash",
                    },
                },
                10: {
                    "moves": {"Volt Switch", "Hydro Pump"},
                    "switches": {
                        "Kingambit",
                        "Dragonite",
                        "Enamorus",
                        "Kommo-o",
                        "Gholdengo",
                    },
                },
                13: {
                    "moves": {"Dragon Dance"},
                    "switches": {"Kingambit", "Enamorus", "Gholdengo", "Rotom-Wash"},
                },
                14: {
                    "moves": {"Dragon Dance", "Ice Spinner"},
                    "switches": {"Kingambit", "Enamorus", "Gholdengo", "Rotom-Wash"},
                },
                17: {
                    "moves": {"Dragon Dance", "Ice Spinner", "Earthquake"},
                    "switches": {"Kingambit", "Enamorus", "Gholdengo", "Rotom-Wash"},
                },
                20: {
                    "moves": {"Hydro Pump", "Volt Switch", "Will-O-Wisp"},
                    "switches": {"Kingambit", "Enamorus", "Gholdengo"},
                },
                24: {
                    "moves": {"Tera Blast", "Sucker Punch"},
                    "switches": {"Enamorus"},
                },
                26: {
                    "moves": {"Substitute", "Moonblast", "Superpower"},
                    "switches": set(),
                },
            },
        ),
        (
            "battle2",
            "battle2.txt",
            {
                1: {
                    "moves": set(),
                    "switches": {
                        "Kingambit",
                        "Ninetales-Alola",
                        "Toxapex",
                        "Roaring Moon",
                        "Glimmora",
                    },
                },
                2: {
                    "moves": {"Earthquake"},
                    "switches": {
                        "Kingambit",
                        "Ninetales-Alola",
                        "Toxapex",
                        "Roaring Moon",
                        "Glimmora",
                    },
                },
                8: {
                    "moves": {"Power Gem", "Mortal Spin"},
                    "switches": {
                        "Dondozo",
                        "Kingambit",
                        "Ninetales-Alola",
                        "Toxapex",
                        "Roaring Moon",
                    },
                },
            },
        ),
        (
            "battle3",
            "battle3.txt",
            {
                1: {
                    "moves": set(),
                    "switches": {
                        "Great Tusk",
                        "Samurott-Hisui",
                        "Cinderace",
                        "Weezing-Galar",
                        "Ribombee",
                    },
                },
                3: {
                    "moves": {"Ice Beam"},
                    "switches": {
                        "Heatran",
                        "Samurott-Hisui",
                        "Cinderace",
                        "Weezing-Galar",
                        "Ribombee",
                    },
                },
                4: {
                    "moves": {"Razor Shell", "Aqua Jet"},
                    "switches": {
                        "Heatran",
                        "Great Tusk",
                        "Cinderace",
                        "Weezing-Galar",
                        "Ribombee",
                    },
                },
            },
        ),
    )
    def test_opponent_potential_actions(
        self,
        battle_file: str,
        turn_expectations: Dict[int, Dict[str, Any]],
    ) -> None:
        """Test opponent action inference at specific turns across different battles.

        Args:
            battle_file: Name of battle log file to test
            turn_expectations: Dict mapping turn number to expected moves and switches
        """
        raw_messages = self._load_battle_log(battle_file)
        events = self._parse_events(raw_messages)

        _, history = self._replay_battle(events)

        for turn_number, expectations in turn_expectations.items():
            expected_moves = expectations["moves"]
            expected_switches = expectations["switches"]

            _, state_at_turn = next(
                (
                    (event, state)
                    for event, state in history
                    if hasattr(event, "turn_number")
                    and event.turn_number == turn_number
                ),
                (None, None),
            )

            if state_at_turn is None:
                continue

            if state_at_turn.our_player_id is None:
                continue

            actions = state_at_turn.get_opponent_potential_actions()

            move_actions = [a for a in actions if a.action_type == ActionType.MOVE]
            unknown_move_actions = [
                a for a in actions if a.action_type == ActionType.UNKNOWN_MOVE
            ]
            switch_actions = [a for a in actions if a.action_type == ActionType.SWITCH]

            expected_known_moves = len(expected_moves)
            expected_unknown_moves = 4 - expected_known_moves

            self.assertEqual(
                len(move_actions),
                expected_known_moves,
                f"Turn {turn_number}: expected {expected_known_moves} known moves",
            )
            self.assertEqual(
                len(unknown_move_actions),
                expected_unknown_moves,
                f"Turn {turn_number}: expected {expected_unknown_moves} unknown moves",
            )

            actual_move_names = {a.move_name for a in move_actions}
            self.assertEqual(
                actual_move_names,
                expected_moves,
                f"Turn {turn_number}: move names don't match",
            )

            actual_switch_names = {a.switch_pokemon_name for a in switch_actions}
            self.assertEqual(
                actual_switch_names,
                expected_switches,
                f"Turn {turn_number}: switch options don't match",
            )


if __name__ == "__main__":
    absltest.main()
