from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class TypeChart:
    effectiveness: Dict[str, Dict[str, float]]

    def get_effectiveness(self, attacking_type: str, defending_type: str) -> float:
        attacking_type = attacking_type.lower()
        defending_type = defending_type.lower()

        if attacking_type not in self.effectiveness:
            raise ValueError(f"Unknown attacking type: {attacking_type}")

        if defending_type not in self.effectiveness[attacking_type]:
            raise ValueError(f"Unknown defending type: {defending_type}")

        return self.effectiveness[attacking_type][defending_type]
