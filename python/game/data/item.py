from dataclasses import dataclass
from typing import Optional

from python.game.data.base import GameDataObject


@dataclass(frozen=True)
class Item(GameDataObject):
    name: str
    num: int
    gen: int
    description: Optional[str] = None
