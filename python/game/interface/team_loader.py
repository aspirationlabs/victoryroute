import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class PokemonTeamMember:
    species: str
    nickname: Optional[str]
    item: Optional[str]
    ability: str
    moves: List[str]
    nature: str
    evs: Dict[str, int]
    ivs: Dict[str, int]
    gender: Optional[str]
    shiny: bool
    level: int
    tera_type: Optional[str]


class TeamLoader:
    def __init__(self, format_name: str = "gen9ou", teams_dir: str = "data/teams"):
        self.format_name = format_name
        self.teams_dir = Path(teams_dir)

    def load_team(self, team_index: Optional[int] = None) -> str:
        if team_index is None:
            return self.get_random_team()

        team_file = self.teams_dir / self.format_name / f"{team_index}.team"
        if not team_file.exists():
            raise FileNotFoundError(f"Team file not found: {team_file}")

        team = self.parse_team_file(str(team_file))
        return self.to_packed_format(team)

    def get_random_team(self) -> str:
        format_dir = self.teams_dir / self.format_name
        if not format_dir.exists():
            raise FileNotFoundError(f"Format directory not found: {format_dir}")

        team_files = list(format_dir.glob("*.team"))
        if not team_files:
            raise FileNotFoundError(f"No team files found in {format_dir}")

        team_file = random.choice(team_files)
        team = self.parse_team_file(str(team_file))
        return self.to_packed_format(team)

    def parse_team_file(self, file_path: str) -> List[PokemonTeamMember]:
        content = Path(file_path).read_text()
        pokemon_blocks = content.strip().split("\n\n")

        team = []
        for block in pokemon_blocks:
            if not block.strip():
                continue
            team.append(self._parse_pokemon_block(block))

        return team

    def _parse_pokemon_block(self, block: str) -> PokemonTeamMember:
        lines = [line.strip() for line in block.strip().split("\n") if line.strip()]

        first_line = lines[0]
        nickname = None
        species = first_line
        item = None
        gender = None

        # Extract item if present
        if " @ " in first_line:
            species_part, item = first_line.split(" @ ", 1)
            species = species_part
        else:
            species = first_line

        # Check for nickname pattern: "Nickname (Species)" or species with gender "(M/F)"
        # We need to distinguish between nickname and gender markers
        if " (" in species and ")" in species:
            before_paren, paren_content = species.rsplit(" (", 1)
            paren_content = paren_content.rstrip(")")

            # Check if it's a gender marker (M, F, or N)
            if paren_content in ("M", "F", "N"):
                gender = paren_content
                species = before_paren
            else:
                # It's a nickname pattern: "Nickname (Species)"
                nickname = before_paren
                species = paren_content

        ability = "No Ability"
        nature = "Serious"
        evs = {}
        ivs = {}
        moves = []
        level = 100
        shiny = False
        tera_type = None

        for line in lines[1:]:
            if line.startswith("Ability:"):
                ability = line.split(":", 1)[1].strip()
            elif line.startswith("Tera Type:"):
                tera_type = line.split(":", 1)[1].strip()
            elif line.startswith("EVs:"):
                evs = self._parse_stats(line.split(":", 1)[1])
            elif line.startswith("IVs:"):
                ivs = self._parse_stats(line.split(":", 1)[1])
            elif " Nature" in line:
                nature = line.replace(" Nature", "").strip()
            elif line.startswith("Level:"):
                level = int(line.split(":", 1)[1].strip())
            elif line.startswith("Shiny:"):
                shiny = line.split(":", 1)[1].strip().lower() == "yes"
            elif line.startswith("-"):
                move = line[1:].strip()
                moves.append(move)

        return PokemonTeamMember(
            species=species,
            nickname=nickname,
            item=item,
            ability=ability,
            moves=moves,
            nature=nature,
            evs=evs,
            ivs=ivs,
            gender=gender,
            shiny=shiny,
            level=level,
            tera_type=tera_type,
        )

    def _parse_stats(self, stats_str: str) -> Dict[str, int]:
        stats = {}
        parts = stats_str.strip().split("/")
        for part in parts:
            part = part.strip()
            match = re.match(r"(\d+)\s+(\w+)", part)
            if match:
                value, stat = match.groups()
                stats[stat] = int(value)
        return stats

    def to_packed_format(self, team: List[PokemonTeamMember]) -> str:
        packed_pokemon: List[str] = []
        for pokemon in team:
            packed = self._pack_pokemon(pokemon)
            packed_pokemon.append(packed)
        return "]".join(packed_pokemon)

    def _pack_pokemon(self, pokemon: PokemonTeamMember) -> str:
        # Per Showdown spec: "SPECIES is left blank if it's identical to NICKNAME"
        # This means: if no nickname, put species in NICKNAME field and leave SPECIES blank
        if pokemon.nickname:
            # Has explicit nickname
            nickname = self._normalize_name(pokemon.nickname)
            # Species blank if same as nickname, otherwise fill it
            if self._normalize_name(pokemon.nickname) == self._normalize_name(
                pokemon.species
            ):
                species = ""
            else:
                species = self._normalize_name(pokemon.species)
        else:
            # No nickname: put species in NICKNAME field, leave SPECIES blank
            nickname = self._normalize_name(pokemon.species)
            species = ""
        item = self._normalize_name(pokemon.item) if pokemon.item else ""
        ability = self._normalize_name(pokemon.ability)
        moves = ",".join(self._normalize_name(m) for m in pokemon.moves)
        nature = pokemon.nature

        evs_list = [
            str(pokemon.evs.get("HP", 0)),
            str(pokemon.evs.get("Atk", 0)),
            str(pokemon.evs.get("Def", 0)),
            str(pokemon.evs.get("SpA", 0)),
            str(pokemon.evs.get("SpD", 0)),
            str(pokemon.evs.get("Spe", 0)),
        ]
        evs = ",".join(evs_list)

        gender = pokemon.gender or ""

        ivs_list = [
            str(pokemon.ivs.get("HP", 31)),
            str(pokemon.ivs.get("Atk", 31)),
            str(pokemon.ivs.get("Def", 31)),
            str(pokemon.ivs.get("SpA", 31)),
            str(pokemon.ivs.get("SpD", 31)),
            str(pokemon.ivs.get("Spe", 31)),
        ]
        ivs = ",".join(ivs_list)

        shiny = "S" if pokemon.shiny else ""
        level = str(pokemon.level)

        # Extras field: HAPPINESS,POKEBALL,HIDDENPOWERTYPE,GIGANTAMAX,DYNAMAXLEVEL,TERATYPE
        # All are optional, blank means default values
        happiness = ""  # Blank = 255
        pokeball = ""  # Blank = regular Poké Ball
        hiddenpowertype = ""  # Blank = not hyper trained
        gigantamax = ""  # Blank = not Gmax
        dynamaxlevel = ""  # Blank = 10
        teratype = self._normalize_name(pokemon.tera_type) if pokemon.tera_type else ""

        # If all extras are blank, leave off commas entirely
        if (
            happiness
            or pokeball
            or hiddenpowertype
            or gigantamax
            or dynamaxlevel
            or teratype
        ):
            extras_str = f"{happiness},{pokeball},{hiddenpowertype},{gigantamax},{dynamaxlevel},{teratype}"
        else:
            extras_str = ""

        parts = [
            nickname,
            species,
            item,
            ability,
            moves,
            nature,
            evs,
            gender,
            ivs,
            shiny,
            level,
            extras_str,
        ]

        return "|".join(parts)

    def _normalize_name(self, name: str) -> str:
        if not name:
            return ""
        normalized = name.lower().replace(" ", "").replace("-", "").replace("'", "")
        return normalized
