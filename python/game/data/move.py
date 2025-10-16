from dataclasses import dataclass
from typing import Optional, Tuple, Union

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
    override_offensive_stat: Optional[str] = None
    override_defensive_stat: Optional[str] = None
    multihit: Optional[Union[int, Tuple[int, int]]] = None
