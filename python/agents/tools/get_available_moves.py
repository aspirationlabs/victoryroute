"""Tool for retrieving available actions (moves and switches)."""

import json
from typing import Any, Dict

from python.game.schema.battle_state import BattleState


def get_available_moves(state: BattleState) -> str:
    """Get available moves, switches, and action flags for the current turn.

    WHEN TO USE:
    Call this tool FIRST at the start of every turn before making any decisions.
    This ensures you only choose from valid, legal actions.

    WHAT IT DOES:
    Returns all legal actions you can take this turn, including available moves,
    switchable Pokemon, and special action flags (Mega/Tera/Dynamax).

    The response includes:
    - moves: List of move names you can use this turn (e.g., ["Earthquake", "U-turn"])
    - switches: List of Pokemon indices you can switch to (e.g., [1, 2, 4])
    - can_mega: Whether you can Mega Evolve with a move this turn
    - can_tera: Whether you can Terastallize with a move this turn
    - can_dynamax: Whether you can Dynamax this turn
    - force_switch: Whether you MUST switch (after your Pokemon fainted)
    - team_preview: Whether this is team preview phase (choose lead order)

    Move indices are 0-3 corresponding to your active Pokemon's moveset.
    Switch indices are 0-5 corresponding to your team positions (excluding active).

    IMPORTANT:
    - If force_switch is true, you MUST choose a switch action
    - If team_preview is true, you must choose team order (e.g., "123456")
    - Move names correspond to your active Pokemon's current moveset
    - Switches list only includes alive, non-trapped Pokemon

    Args:
        state: Current BattleState object

    Returns:
        JSON string with available actions and flags

    Example responses:

        Normal turn with moves and switches available:
        {
          "moves": ["Earthquake", "U-turn", "Stealth Rock"],
          "switches": [1, 2, 4],
          "can_mega": false,
          "can_tera": true,
          "can_dynamax": false,
          "force_switch": false,
          "team_preview": false
        }

        Forced switch after faint:
        {
          "moves": [],
          "switches": [0, 2, 3, 5],
          "can_mega": false,
          "can_tera": false,
          "can_dynamax": false,
          "force_switch": true,
          "team_preview": false
        }

        Team preview at battle start:
        {
          "moves": [],
          "switches": [],
          "can_mega": false,
          "can_tera": false,
          "can_dynamax": false,
          "force_switch": false,
          "team_preview": true
        }
    """
    result: Dict[str, Any] = {
        "moves": state.available_moves,
        "switches": state.available_switches,
        "can_mega": state.can_mega,
        "can_tera": state.can_tera,
        "can_dynamax": state.can_dynamax,
        "force_switch": state.force_switch,
        "team_preview": state.team_preview,
    }
    return json.dumps(result, indent=2)
