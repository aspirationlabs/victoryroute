from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class GameDataObject:
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameDataObject":
        return cls(**data)
