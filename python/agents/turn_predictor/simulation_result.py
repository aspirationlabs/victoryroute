"""Data structures for representing battle simulation outcomes."""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from python.agents.tools.battle_simulator import MoveResult
from python.game.interface.battle_action import BattleAction
from python.game.schema.enums import Stat, Status


@dataclass(frozen=True)
class PokemonOutcome:
    """Represents the outcome for a single Pokemon after an action pair resolves."""

    # Pokemon identity after resolution (accounting for switches)
    active_pokemon: str  # Species of the active Pokemon after resolution

    # HP outcomes (accounting for damage ranges)
    active_pokemon_hp_range: Tuple[int, int]  # (min_hp, max_hp) after all actions
    active_pokemon_max_hp: int  # Maximum HP of the active Pokemon
    critical_hit_received_hp_range: Tuple[int, int]  # HP range if critical hit received

    # Probability outcomes
    active_pokemon_moves_probability: (
        float  # 1.0 if moves first turn, less if may be KO'd
    )
    active_pokemon_fainted_probability: float  # 0.0 to 1.0
    critical_hit_received_probability: float  # Probability of receiving a critical hit

    # Status and stat changes
    active_pokemon_status_probability: Dict[Status, float]  # Probability of each status
    active_pokemon_stat_changes: Dict[Stat, int]  # Net stat changes from this turn


@dataclass(frozen=True)
class SimulationResult:
    """Represents the simulated outcome of an action pair between two players."""

    simulation_id: int

    actions: Dict[str, BattleAction]  # {"p1": BattleAction, "p2": BattleAction}

    # Execution order
    player_move_order: Tuple[
        str, ...
    ]  # ("p1", "p2") or ("p2", "p1") or ("p1",) if one faints

    # Raw simulation results from BattleSimulator
    move_results: Dict[
        str, Optional[MoveResult]
    ]  # {"p1": MoveResult, "p2": None} if p2 fainted

    # Final outcomes for each player
    player_outcomes: Dict[
        str, PokemonOutcome
    ]  # {"p1": PokemonOutcome, "p2": PokemonOutcome}
