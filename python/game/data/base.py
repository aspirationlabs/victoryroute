from dataclasses import dataclass
from typing import Any, Dict, TypeVar

T = TypeVar("T", bound="GameDataObject")


@dataclass(frozen=True)
class GameDataObject:
    @classmethod
    def from_dict(cls: type[T], data: Dict[str, Any]) -> T:
        return cls(**data)
