from dataclasses import dataclass
from typing import Dict, List

from python.game.data.base import GameDataObject


@dataclass(frozen=True)
class Pokemon(GameDataObject):
    name: str
    num: int
    types: List[str]
    base_stats: Dict[str, int]
    abilities: Dict[str, str]
