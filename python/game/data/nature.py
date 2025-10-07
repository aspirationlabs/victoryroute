from dataclasses import dataclass
from typing import Optional

from python.game.data.base import GameDataObject


@dataclass(frozen=True)
class Nature(GameDataObject):
    name: str
    plus_stat: Optional[str]
    minus_stat: Optional[str]
