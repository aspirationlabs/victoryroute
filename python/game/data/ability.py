from dataclasses import dataclass

from python.game.data.base import GameDataObject


@dataclass(frozen=True)
class Ability(GameDataObject):
    name: str
    num: int
    rating: float
