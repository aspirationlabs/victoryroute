import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from absl import logging

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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PokemonStatePriors):
            return False
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
            self._data_available = False
            self._load_stats()
            self._initialized = True

    def _load_stats(self) -> None:
        if not self.data_file.exists():
            logging.warning(
                "Pokemon stats file not found at %s. Continuing without priors data.",
                self.data_file,
            )
            return

        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            logging.warning(
                "Invalid JSON in stats file %s (%s). Continuing without priors data.",
                self.data_file,
                e,
            )
            return
        except OSError as e:
            logging.warning(
                "Failed to read stats file %s (%s). Continuing without priors data.",
                self.data_file,
                e,
            )
            return

        for key, stats in data.items():
            self._stats_lookup[normalize_name(key)] = PokemonStatePriors(
                abilities=stats.get("abilities", []),
                items=stats.get("items", []),
                moves=stats.get("moves", []),
                spreads=stats.get("spreads", []),
                tera=stats.get("tera", []),
                teammates=stats.get("teammates", []),
            )

        self._data_available = True

    def get_pokemon_state_priors(
        self, pokemon_species: str
    ) -> Optional[PokemonStatePriors]:
        key = normalize_name(pokemon_species)
        return self._stats_lookup.get(key, None)

    @property
    def data_available(self) -> bool:
        return self._data_available

    def get_top_usage_spread(
        self, pokemon_species: str
    ) -> Optional[Tuple[Optional[str], Tuple[int, int, int, int, int, int]]]:
        """Return the highest-usage nature/EV spread for the given species.

        Args:
            pokemon_species: Species name to look up.

        Returns:
            Tuple of (nature, EV spread) where EV spread is a 6-tuple in the order
            (hp, attack, defense, special_attack, special_defense, speed).
            Returns None if no spread information is available.
        """
        priors = self.get_pokemon_state_priors(pokemon_species)
        if not priors or not priors.spreads:
            return None

        top_spread = max(
            priors.spreads, key=lambda spread: spread.get("percentage", 0.0)
        )

        stats = top_spread.get("stats")
        if not isinstance(stats, list) or len(stats) != 6:
            return None

        try:
            ev_values_raw = tuple(int(value) for value in stats)
        except (TypeError, ValueError):
            return None

        if len(ev_values_raw) != 6:
            return None

        ev_values: Tuple[int, int, int, int, int, int] = (
            ev_values_raw[0],
            ev_values_raw[1],
            ev_values_raw[2],
            ev_values_raw[3],
            ev_values_raw[4],
            ev_values_raw[5],
        )

        nature = top_spread.get("nature")
        nature_str = nature.strip() if isinstance(nature, str) else None
        if nature_str == "":
            nature_str = None

        return nature_str, ev_values
