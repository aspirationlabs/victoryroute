import tempfile
import unittest
from pathlib import Path

from python.game.interface.team_loader import TeamLoader


class TeamLoaderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.teams_dir = Path(self.temp_dir) / "teams"
        self.teams_dir.mkdir()

    def test_parse_simple_pokemon(self) -> None:
        team_content = """Pikachu @ Light Ball
Ability: Static
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Thunderbolt
- Grass Knot
- Hidden Power Ice
- Volt Switch
"""
        team_file = self.teams_dir / "gen9ou"
        team_file.mkdir()
        (team_file / "0.team").write_text(team_content)

        loader = TeamLoader(format_name="gen9ou", teams_dir=str(self.teams_dir))
        team = loader.parse_team_file(str(team_file / "0.team"))

        self.assertEqual(len(team), 1)
        pokemon = team[0]
        self.assertEqual(pokemon.species, "Pikachu")
        self.assertEqual(pokemon.item, "Light Ball")
        self.assertEqual(pokemon.ability, "Static")
        self.assertEqual(pokemon.nature, "Timid")
        self.assertEqual(len(pokemon.moves), 4)
        self.assertIn("Thunderbolt", pokemon.moves)
        self.assertEqual(pokemon.evs["SpA"], 252)
        self.assertEqual(pokemon.evs["Spe"], 252)
        self.assertEqual(pokemon.evs["SpD"], 4)
        self.assertEqual(pokemon.ivs["Atk"], 0)

    def test_parse_pokemon_with_gender(self) -> None:
        team_content = """Kingambit (M) @ Leftovers
Ability: Supreme Overlord
EVs: 200 HP / 252 Atk / 56 Spe
Adamant Nature
- Iron Head
- Sucker Punch
"""
        team_file = self.teams_dir / "gen9ou"
        team_file.mkdir()
        (team_file / "0.team").write_text(team_content)

        loader = TeamLoader(format_name="gen9ou", teams_dir=str(self.teams_dir))
        team = loader.parse_team_file(str(team_file / "0.team"))

        self.assertEqual(len(team), 1)
        pokemon = team[0]
        self.assertEqual(pokemon.species, "Kingambit")
        self.assertEqual(pokemon.gender, "M")
        self.assertEqual(pokemon.item, "Leftovers")

    def test_parse_pokemon_with_tera_type(self) -> None:
        team_content = """Kyurem @ Loaded Dice
Ability: Pressure
Tera Type: Electric
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Dragon Dance
- Icicle Spear
"""
        team_file = self.teams_dir / "gen9ou"
        team_file.mkdir()
        (team_file / "0.team").write_text(team_content)

        loader = TeamLoader(format_name="gen9ou", teams_dir=str(self.teams_dir))
        team = loader.parse_team_file(str(team_file / "0.team"))

        self.assertEqual(len(team), 1)
        pokemon = team[0]
        self.assertEqual(pokemon.tera_type, "Electric")

    def test_to_packed_format(self) -> None:
        team_content = """Pikachu @ Light Ball
Ability: Static
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
IVs: 0 Atk
- Thunderbolt
- Grass Knot
- Hidden Power Ice
- Volt Switch
"""
        team_file = self.teams_dir / "gen9ou"
        team_file.mkdir()
        (team_file / "0.team").write_text(team_content)

        loader = TeamLoader(format_name="gen9ou", teams_dir=str(self.teams_dir))
        packed = loader.load_team(team_index=0)

        self.assertIn("Pikachu", packed)
        self.assertIn("lightball", packed)
        self.assertIn("static", packed)
        self.assertIn("thunderbolt", packed)
        self.assertIn("Timid", packed)
        self.assertTrue(packed.endswith("]"))

    def test_load_team_by_index(self) -> None:
        team_content = """Pikachu @ Light Ball
Ability: Static
EVs: 252 SpA / 4 SpD / 252 Spe
Timid Nature
- Thunderbolt
"""
        team_file = self.teams_dir / "gen9ou"
        team_file.mkdir()
        (team_file / "5.team").write_text(team_content)

        loader = TeamLoader(format_name="gen9ou", teams_dir=str(self.teams_dir))
        packed = loader.load_team(team_index=5)

        self.assertIn("Pikachu", packed)

    def test_parse_full_team(self) -> None:
        team_content = """Kyurem @ Loaded Dice
Ability: Pressure
Tera Type: Electric
EVs: 252 Atk / 4 SpD / 252 Spe
Adamant Nature
- Dragon Dance
- Icicle Spear

Iron Moth @ Booster Energy
Ability: Quark Drive
Tera Type: Fairy
EVs: 124 Def / 132 SpA / 252 Spe
Timid Nature
IVs: 0 Atk
- Fiery Dance
- Sludge Wave
"""
        team_file = self.teams_dir / "gen9ou"
        team_file.mkdir()
        (team_file / "0.team").write_text(team_content)

        loader = TeamLoader(format_name="gen9ou", teams_dir=str(self.teams_dir))
        team = loader.parse_team_file(str(team_file / "0.team"))

        self.assertEqual(len(team), 2)
        self.assertEqual(team[0].species, "Kyurem")
        self.assertEqual(team[1].species, "Iron Moth")


if __name__ == "__main__":
    unittest.main()
