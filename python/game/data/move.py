from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

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
    base_power_callback_type: Optional[str] = None
    recoil: Optional[Tuple[int, int]] = None
    drain: Optional[Tuple[int, int]] = None
    secondary_effects: Optional[List[Dict[str, Any]]] = None
    flags: Optional[List[str]] = None
    has_secondary_effect: bool = False
