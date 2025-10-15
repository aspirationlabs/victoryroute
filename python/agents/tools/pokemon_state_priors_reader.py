import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from python.game.schema.object_name_normalizer import normalize_name


@dataclass
class PokemonStatePriors:
    """Usage statistics and priors for a Pokemon species.

    Each list contains dictionaries sorted by usage percentage (highest first).
    Common fields: 'name' (str), 'percentage' (float)
    Spreads also include: 'nature' (str), 'stats' (List[int]) with 6 EVs
    """

    abilities: List[Dict[str, Any]]
    items: List[Dict[str, Any]]
    moves: List[Dict[str, Any]]
    spreads: List[Dict[str, Any]]
    tera: List[Dict[str, Any]]
    teammates: List[Dict[str, Any]]

    def __eq__(self, other: "PokemonStatePriors") -> bool:
        return (
            self.abilities == other.abilities
            and self.items == other.items
            and self.moves == other.moves
            and self.spreads == other.spreads
            and self.tera == other.tera
            and self.teammates == other.teammates
        )


class PokemonStatePriorsReader:
    """Singleton class for accessing Pokemon usage statistics and priors.

    This class loads Pokemon usage data from Smogon stats JSON files
    and provides read-only access throughout the application.

    Thread-safe singleton implementation using double-checked locking pattern.

    Typical usage:
        reader = PokemonStatePriorsReader()
        priors = reader.get_pokemon_state_priors("Kingambit")
        if priors:
            top_ability = priors.abilities[0]["name"]
    """

    _instance: Optional["PokemonStatePriorsReader"] = None
    _instance_lock: threading.Lock = threading.Lock()
    _init_lock: threading.Lock = threading.Lock()

    def __new__(
        cls, mode: str = "gen9ou", file_name: str = "1500.json"
    ) -> "PokemonStatePriorsReader":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, mode: str = "gen9ou", file_name: str = "1500.json") -> None:
        if self._initialized:
            return

        with self._init_lock:
            if self._initialized:
                return

            module_dir = Path(__file__).resolve().parent
            repo_root = module_dir.parent.parent.parent
            self.data_file = repo_root / "data" / "stats" / mode / file_name
            self._stats_lookup: Dict[str, PokemonStatePriors] = {}
            self._load_stats()
            self._initialized = True

    def _load_stats(self) -> None:
        if not self.data_file.exists():
            raise FileNotFoundError(
                f"Pokemon stats file not found: {self.data_file}. "
                f"Ensure the file exists at the specified path."
            )

        try:
            with open(self.data_file, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in stats file {self.data_file}: {e}") from e
        except IOError as e:
            raise IOError(f"Failed to read stats file {self.data_file}: {e}") from e

        for key, stats in data.items():
            self._stats_lookup[normalize_name(key)] = PokemonStatePriors(
                abilities=stats.get("abilities", []),
                items=stats.get("items", []),
                moves=stats.get("moves", []),
                spreads=stats.get("spreads", []),
                tera=stats.get("tera", []),
                teammates=stats.get("teammates", []),
            )

    def get_pokemon_state_priors(
        self, pokemon_species: str
    ) -> Optional[PokemonStatePriors]:
        key = normalize_name(pokemon_species)
        return self._stats_lookup.get(key)
