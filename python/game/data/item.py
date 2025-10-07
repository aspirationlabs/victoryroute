from dataclasses import dataclass

from python.game.data.base import GameDataObject


@dataclass(frozen=True)
class Item(GameDataObject):
    name: str
    num: int
    gen: int
