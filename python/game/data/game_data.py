import json
from pathlib import Path
from typing import Dict, Optional, Type, TypeVar

from python.game.data.ability import Ability
from python.game.data.item import Item
from python.game.data.move import Move
from python.game.data.nature import Nature
from python.game.data.pokemon import Pokemon
from python.game.data.type_chart import TypeChart

T = TypeVar("T")


class GameData:
    """Singleton class for accessing static game data.

    This class loads Pokemon, moves, abilities, items, natures, and type chart data
    once and provides read-only access throughout the application.
    """

    _instance: Optional["GameData"] = None

    def __new__(cls, data_dir: str = "data/game") -> "GameData":
        """Create or return the singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, data_dir: str = "data/game") -> None:
        """Initialize the game data (only runs once for the singleton)."""
        # Only initialize once
        if self._initialized:  # type: ignore
            return

        self.data_dir = Path(data_dir)
        self._pokemon_lookup = self._load_lookup_data("pokemon.json", Pokemon)
        self._moves_lookup = self._load_lookup_data("moves.json", Move)
        self._abilities_lookup = self._load_lookup_data("abilities.json", Ability)
        self._items_lookup = self._load_lookup_data("items.json", Item)
        self._natures_lookup = self._load_lookup_data("natures.json", Nature)
        self._type_chart = self._load_type_chart()
        self._initialized = True  # type: ignore

    def _normalize_key(self, name: str) -> str:
        return name.lower().replace(" ", "").replace("-", "").replace("'", "")

    def _load_lookup_data(self, filename: str, cls: Type[T]) -> Dict[str, T]:
        with open(self.data_dir / filename, "r") as f:
            data = json.load(f)
        return {
            self._normalize_key(entry["name"]): cls.from_dict(entry) for entry in data
        }

    def _load_type_chart(self) -> TypeChart:
        with open(self.data_dir / "type_chart.json", "r") as f:
            data = json.load(f)
        return TypeChart(effectiveness=data[0]["effectiveness"])

    def get_pokemon(self, name: str) -> Pokemon:
        key = self._normalize_key(name)
        if key not in self._pokemon_lookup:
            raise ValueError(f"Pokemon not found: {name}")
        return self._pokemon_lookup[key]

    def get_move(self, name: str) -> Move:
        key = self._normalize_key(name)
        if key not in self._moves_lookup:
            raise ValueError(f"Move not found: {name}")
        return self._moves_lookup[key]

    def get_ability(self, name: str) -> Ability:
        key = self._normalize_key(name)
        if key not in self._abilities_lookup:
            raise ValueError(f"Ability not found: {name}")
        return self._abilities_lookup[key]

    def get_item(self, name: str) -> Item:
        key = self._normalize_key(name)
        if key not in self._items_lookup:
            raise ValueError(f"Item not found: {name}")
        return self._items_lookup[key]

    def get_nature(self, name: str) -> Nature:
        key = self._normalize_key(name)
        if key not in self._natures_lookup:
            raise ValueError(f"Nature not found: {name}")
        return self._natures_lookup[key]

    def get_type_chart(self) -> TypeChart:
        return self._type_chart
