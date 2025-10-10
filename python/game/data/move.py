from dataclasses import dataclass
from typing import Optional

from python.game.data.base import GameDataObject


@dataclass(frozen=True)
class Move(GameDataObject):
    name: str
    num: int
    type: str
    base_power: int
    accuracy: Optional[int]
    pp: int
    priority: int
    category: str
    description: str = ""
