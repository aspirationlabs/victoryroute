"""Integration tests for TeamLoader using real team files."""

import unittest
from pathlib import Path

from python.game.interface.team_loader import TeamLoader


class TeamLoaderIntegrationTest(unittest.TestCase):
    """Integration tests that use real team files from data/teams/."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.data_dir = Path("data/teams")
        self.assertTrue(
            self.data_dir.exists(),
            "data/teams directory must exist for integration tests",
        )

    def test_load_real_gen9ou_team(self) -> None:
        """Test loading a real gen9ou team file."""
        gen9ou_dir = self.data_dir / "gen9ou"
        if not gen9ou_dir.exists():
            self.skipTest("gen9ou teams directory not found")

        team_files = list(gen9ou_dir.glob("*.team"))
        if not team_files:
            self.skipTest("No gen9ou team files found")

        loader = TeamLoader(format_name="gen9ou")
        team_file = team_files[0]

        team = loader.parse_team_file(str(team_file))

        self.assertGreater(len(team), 0, "Team should have at least one Pokemon")
        self.assertLessEqual(len(team), 6, "Team should have at most 6 Pokemon")

        for i, pokemon in enumerate(team):
            with self.subTest(pokemon=i):
                self.assertIsNotNone(
                    pokemon.species, f"Pokemon {i} should have species"
                )
                self.assertIsNotNone(
                    pokemon.ability, f"Pokemon {i} should have ability"
                )
                self.assertIsNotNone(pokemon.nature, f"Pokemon {i} should have nature")
                self.assertGreater(
                    len(pokemon.moves), 0, f"Pokemon {i} should have moves"
                )
                self.assertLessEqual(
                    len(pokemon.moves), 4, f"Pokemon {i} should have at most 4 moves"
                )

    def test_packed_format_structure(self) -> None:
        """Test that packed format follows Showdown protocol."""
        gen9ou_dir = self.data_dir / "gen9ou"
        if not gen9ou_dir.exists():
            self.skipTest("gen9ou teams directory not found")

        loader = TeamLoader(format_name="gen9ou")
        packed = loader.load_team(team_index=0)

        self.assertIsInstance(packed, str)

        pokemon_list = [p for p in packed.split("]") if p.strip()]

        self.assertGreater(len(pokemon_list), 0, "Should have at least one Pokemon")
        self.assertLessEqual(len(pokemon_list), 6, "Should have at most 6 Pokemon")

        for i, pokemon_str in enumerate(pokemon_list):
            with self.subTest(pokemon=i):
                parts = pokemon_str.split("|")

                self.assertGreaterEqual(
                    len(parts),
                    11,
                    f"Pokemon {i} should have at least 11 pipe-separated fields",
                )

    def test_multi_word_species_names(self) -> None:
        """Test that multi-word species names are handled correctly."""
        gen9ou_dir = self.data_dir / "gen9ou"
        if not gen9ou_dir.exists():
            self.skipTest("gen9ou teams directory not found")

        loader = TeamLoader(format_name="gen9ou")

        team_files = list(gen9ou_dir.glob("*.team"))
        found_multiword = False

        for team_file in team_files:
            team = loader.parse_team_file(str(team_file))
            for pokemon in team:
                if " " in pokemon.species or "-" in pokemon.species:
                    found_multiword = True

                    packed = loader.to_packed_format(team)
                    pokemon_parts = packed.split("]")

                    for p in pokemon_parts:
                        if pokemon.species in p:
                            fields = p.split("|")
                            if len(fields) > 1 and not pokemon.nickname:
                                self.assertEqual(
                                    fields[0],
                                    "",
                                    f"Nickname field should be empty for {pokemon.species}",
                                )

        if not found_multiword:
            self.skipTest("No multi-word species found in team files")

    def test_gender_markers(self) -> None:
        """Test that gender markers are parsed and packed correctly."""
        gen9ou_dir = self.data_dir / "gen9ou"
        if not gen9ou_dir.exists():
            self.skipTest("gen9ou teams directory not found")

        loader = TeamLoader(format_name="gen9ou")
        team_files = list(gen9ou_dir.glob("*.team"))

        found_gender = False
        for team_file in team_files:
            team = loader.parse_team_file(str(team_file))
            for pokemon in team:
                if pokemon.gender:
                    found_gender = True

                    self.assertIn(
                        pokemon.gender,
                        ["M", "F", "N"],
                        f"Gender should be M, F, or N, got {pokemon.gender}",
                    )

                    packed = loader.to_packed_format(team)
                    pokemon_parts = packed.split("]")
                    for p in pokemon_parts:
                        fields = p.split("|")
                        if (
                            len(fields) > 7
                            and pokemon.species.lower()
                            .replace(" ", "")
                            .replace("-", "")
                            in fields[1].lower()
                        ):
                            if pokemon.gender:
                                self.assertEqual(
                                    fields[7],
                                    pokemon.gender,
                                    f"Gender field should be {pokemon.gender}",
                                )

        if not found_gender:
            self.skipTest("No Pokemon with gender markers found")

    def test_tera_types(self) -> None:
        """Test that Tera Types are parsed and packed correctly."""
        gen9ou_dir = self.data_dir / "gen9ou"
        if not gen9ou_dir.exists():
            self.skipTest("gen9ou teams directory not found")

        loader = TeamLoader(format_name="gen9ou")
        team_files = list(gen9ou_dir.glob("*.team"))

        found_tera = False
        for team_file in team_files:
            team = loader.parse_team_file(str(team_file))
            for pokemon in team:
                if pokemon.tera_type:
                    found_tera = True

                    packed = loader.to_packed_format(team)

                    normalized_tera = (
                        pokemon.tera_type.lower().replace(" ", "").replace("-", "")
                    )
                    self.assertIn(
                        f",,,,,{normalized_tera}",
                        packed.lower(),
                        f"Tera type {pokemon.tera_type} should be in extras field as ,,,,,{normalized_tera}",
                    )

        if not found_tera:
            self.skipTest("No Pokemon with Tera Types found")

    def test_items_and_abilities(self) -> None:
        """Test that items and abilities are normalized correctly."""
        gen9ou_dir = self.data_dir / "gen9ou"
        if not gen9ou_dir.exists():
            self.skipTest("gen9ou teams directory not found")

        loader = TeamLoader(format_name="gen9ou")
        team = loader.parse_team_file(str(gen9ou_dir / "0.team"))

        for pokemon in team:
            packed = loader.to_packed_format(team)

            if pokemon.item:
                normalized_item = (
                    pokemon.item.lower()
                    .replace(" ", "")
                    .replace("-", "")
                    .replace("'", "")
                )
                self.assertIn(
                    normalized_item,
                    packed.lower(),
                    f"Item {pokemon.item} should be normalized in packed format",
                )

            if pokemon.ability:
                normalized_ability = (
                    pokemon.ability.lower()
                    .replace(" ", "")
                    .replace("-", "")
                    .replace("'", "")
                )
                self.assertIn(
                    normalized_ability,
                    packed.lower(),
                    f"Ability {pokemon.ability} should be normalized in packed format",
                )

    def test_evs_and_ivs(self) -> None:
        """Test that EVs and IVs are packed in the correct order."""
        gen9ou_dir = self.data_dir / "gen9ou"
        if not gen9ou_dir.exists():
            self.skipTest("gen9ou teams directory not found")

        loader = TeamLoader(format_name="gen9ou")
        team = loader.parse_team_file(str(gen9ou_dir / "0.team"))
        packed = loader.to_packed_format(team)

        pokemon_parts = packed.split("]")

        for p in pokemon_parts:
            if not p.strip():
                continue

            fields = p.split("|")

            if len(fields) > 6:
                evs = fields[6]
                if evs:
                    ev_values = evs.split(",")
                    self.assertEqual(
                        len(ev_values),
                        6,
                        "Should have 6 EV values (HP, Atk, Def, SpA, SpD, Spe)",
                    )

            if len(fields) > 8:
                ivs = fields[8]
                if ivs:
                    iv_values = ivs.split(",")
                    self.assertEqual(
                        len(iv_values),
                        6,
                        "Should have 6 IV values (HP, Atk, Def, SpA, SpD, Spe)",
                    )

    def test_load_random_team(self) -> None:
        """Test loading a random team without specifying index."""
        gen9ou_dir = self.data_dir / "gen9ou"
        if not gen9ou_dir.exists():
            self.skipTest("gen9ou teams directory not found")

        team_files = list(gen9ou_dir.glob("*.team"))
        if len(team_files) < 2:
            self.skipTest("Need at least 2 team files to test randomness")

        loader = TeamLoader(format_name="gen9ou")

        packed_teams = set()
        for _ in range(min(10, len(team_files))):
            packed = loader.load_team(team_index=None)
            self.assertIsInstance(packed, str)
            packed_teams.add(packed)

        if len(team_files) >= 3:
            self.assertGreater(
                len(packed_teams),
                1,
                "Random team selection should return different teams",
            )

    def test_gen1ou_team_if_available(self) -> None:
        """Test loading gen1ou team if available."""
        gen1ou_dir = self.data_dir / "gen1ou"
        if not gen1ou_dir.exists():
            self.skipTest("gen1ou teams directory not found")

        team_files = list(gen1ou_dir.glob("*.team"))
        if not team_files:
            self.skipTest("No gen1ou team files found")

        loader = TeamLoader(format_name="gen1ou")
        team = loader.parse_team_file(str(team_files[0]))

        for pokemon in team:
            self.assertIsNotNone(pokemon.species)
            self.assertIsNotNone(pokemon.nature)

        team_index = int(team_files[0].stem)
        packed = loader.load_team(team_index=team_index)
        self.assertIsInstance(packed, str)

    def test_round_trip_parsing(self) -> None:
        """Test that parsing and re-packing preserves essential data."""
        gen9ou_dir = self.data_dir / "gen9ou"
        if not gen9ou_dir.exists():
            self.skipTest("gen9ou teams directory not found")

        loader = TeamLoader(format_name="gen9ou")

        original_team = loader.parse_team_file(str(gen9ou_dir / "0.team"))

        packed = loader.to_packed_format(original_team)

        for pokemon in original_team:
            normalized_species = (
                pokemon.species.lower().replace(" ", "").replace("-", "")
            )
            self.assertIn(
                normalized_species,
                packed.lower(),
                f"Species {pokemon.species} should be in packed format",
            )

            for move in pokemon.moves:
                normalized_move = (
                    move.lower().replace(" ", "").replace("-", "").replace("'", "")
                )
                self.assertIn(
                    normalized_move,
                    packed.lower(),
                    f"Move {move} should be in packed format",
                )


if __name__ == "__main__":
    unittest.main()
