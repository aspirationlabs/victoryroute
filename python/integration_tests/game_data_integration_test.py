"""Integration tests that validate game data lookups for all battle elements."""

import os
import unittest
from typing import List, Set

from absl.testing import absltest, parameterized

from python.game.data.game_data import GameData
from python.game.environment.state_transition import StateTransition
from python.game.protocol.message_parser import MessageParser
from python.game.schema.battle_state import BattleState


class GameDataIntegrationTest(unittest.IsolatedAsyncioTestCase, parameterized.TestCase):
    """Tests that validate all game data can be successfully retrieved."""

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

    def _validate_pokemon_data(self, pokemon_name: str) -> None:
        """Validate that Pokemon data can be retrieved and is non-empty.

        Args:
            pokemon_name: Name of the Pokemon to validate
        """
        game_data = GameData()
        pokemon = game_data.get_pokemon(pokemon_name)
        self.assertIsNotNone(pokemon, f"Pokemon data is null for {pokemon_name}")
        self.assertTrue(pokemon.name, f"Pokemon name is empty for {pokemon_name}")
        self.assertTrue(
            pokemon.types, f"Pokemon types list is empty for {pokemon_name}"
        )
        self.assertTrue(
            pokemon.base_stats,
            f"Pokemon base_stats dict is empty for {pokemon_name}",
        )
        self.assertTrue(
            pokemon.abilities,
            f"Pokemon abilities dict is empty for {pokemon_name}",
        )

    def _validate_move_data(self, move_name: str) -> None:
        """Validate that move data can be retrieved and is non-empty.

        Args:
            move_name: Name of the move to validate
        """
        game_data = GameData()
        move = game_data.get_move(move_name)
        self.assertIsNotNone(move, f"Move data is null for {move_name}")
        self.assertTrue(move.name, f"Move name is empty for {move_name}")
        self.assertTrue(move.type, f"Move type is empty for {move_name}")
        self.assertTrue(move.category, f"Move category is empty for {move_name}")
        self.assertGreaterEqual(move.pp, 0, f"Move PP is negative for {move_name}")

    def _validate_ability_data(self, ability_name: str) -> None:
        """Validate that ability data can be retrieved and is non-empty.

        Args:
            ability_name: Name of the ability to validate
        """
        game_data = GameData()
        ability = game_data.get_ability(ability_name)
        self.assertIsNotNone(ability, f"Ability data is null for {ability_name}")
        self.assertTrue(ability.name, f"Ability name is empty for {ability_name}")
        self.assertTrue(
            ability.description,
            f"Ability description is empty for {ability_name}",
        )

    def _validate_item_data(self, item_name: str) -> None:
        """Validate that item data can be retrieved and is non-empty.

        Args:
            item_name: Name of the item to validate
        """
        if not item_name or item_name == "":
            return

        game_data = GameData()
        item = game_data.get_item(item_name)
        self.assertIsNotNone(item, f"Item data is null for {item_name}")
        self.assertTrue(item.name, f"Item name is empty for {item_name}")

    def _collect_all_game_data_references(
        self, state: BattleState
    ) -> tuple[Set[str], Set[str], Set[str], Set[str]]:
        """Collect all references to game data from the current battle state.

        Args:
            state: Current battle state

        Returns:
            Tuple of (pokemon_names, move_names, ability_names, item_names)
        """
        pokemon_names: Set[str] = set()
        move_names: Set[str] = set()
        ability_names: Set[str] = set()
        item_names: Set[str] = set()

        # Extract Pokemon data from both teams
        for player_id in ["p1", "p2"]:
            team = state.get_team(player_id)

            for pokemon in team.get_pokemon_team():
                if pokemon.species:
                    pokemon_names.add(pokemon.species)

                if pokemon.ability:
                    ability_names.add(pokemon.ability)

                if pokemon.item:
                    item_names.add(pokemon.item)

                for move in pokemon.moves:
                    if move.name:
                        move_names.add(move.name)

        return pokemon_names, move_names, ability_names, item_names

    @parameterized.named_parameters(
        ("battle_1", "live_battle_1.txt"),
        ("battle_2", "live_battle_2.txt"),
        ("battle_3", "live_battle_3.txt"),
    )
    def test_all_game_data_retrievable(self, battle_file: str) -> None:
        """Test that all game data referenced in battle can be retrieved.

        This test validates that:
        1. All Pokemon species have valid game data with non-empty fields
        2. All moves have valid game data with non-empty fields
        3. All abilities have valid game data with non-empty fields
        4. All items have valid game data with non-empty fields

        Args:
            battle_file: Battle log file to test
        """
        raw_messages = self._load_battle_log(battle_file)

        state = BattleState()
        parser = MessageParser()

        # Collect all unique game data references throughout the battle
        all_pokemon: Set[str] = set()
        all_moves: Set[str] = set()
        all_abilities: Set[str] = set()
        all_items: Set[str] = set()

        for message in raw_messages:
            event = parser.parse(message)
            state = StateTransition.apply(state, event)

            # After each event, collect game data references
            pokemon, moves, abilities, items = self._collect_all_game_data_references(
                state
            )
            all_pokemon.update(pokemon)
            all_moves.update(moves)
            all_abilities.update(abilities)
            all_items.update(items)

        # Now validate all collected game data
        for pokemon_name in all_pokemon:
            self._validate_pokemon_data(pokemon_name)

        for move_name in all_moves:
            self._validate_move_data(move_name)

        for ability_name in all_abilities:
            self._validate_ability_data(ability_name)

        for item_name in all_items:
            if item_name:
                self._validate_item_data(item_name)

    @parameterized.named_parameters(
        ("battle_1", "live_battle_1.txt"),
        ("battle_2", "live_battle_2.txt"),
        ("battle_3", "live_battle_3.txt"),
    )
    def test_pokemon_team_data(self, battle_file: str) -> None:
        """Test that all Pokemon team data is valid and non-empty.

        This validates:
        - Pokemon species data
        - Abilities
        - Moves
        - Items (when equipped)

        Args:
            battle_file: Battle log file to test
        """
        raw_messages = self._load_battle_log(battle_file)

        state = BattleState()
        parser = MessageParser()

        for message in raw_messages:
            event = parser.parse(message)
            state = StateTransition.apply(state, event)

            # Validate all Pokemon data for both teams
            for player_id in ["p1", "p2"]:
                team = state.get_team(player_id)
                for pokemon in team.get_pokemon_team():
                    # Validate Pokemon species
                    if pokemon.species:
                        self._validate_pokemon_data(pokemon.species)

                    # Validate ability
                    if pokemon.ability:
                        self._validate_ability_data(pokemon.ability)

                    # Validate item
                    if pokemon.item:
                        self._validate_item_data(pokemon.item)

                    # Validate moves
                    for move in pokemon.moves:
                        if move.name:
                            self._validate_move_data(move.name)


if __name__ == "__main__":
    absltest.main()
