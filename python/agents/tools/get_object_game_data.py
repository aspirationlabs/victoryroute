"""Tool for looking up game data objects (Pokemon, Move, Ability, Item, Nature)."""

import dataclasses
import json

from python.game.data.game_data import GameData


def get_object_game_data(name: str, game_data: GameData) -> str:
    """Look up detailed game data for a Pokemon, Move, Ability, Item, or Nature.

    WHEN TO USE:
    Call this tool whenever you need detailed information about specific game objects
    to make informed strategic decisions. You can call this multiple times per turn
    as needed to research type matchups, move effects, ability interactions, etc.

    WHAT IT DOES:
    Queries the game database and returns comprehensive information about any game
    object by name. The tool automatically determines the object type (Pokemon, Move,
    Ability, Item, or Nature) and returns all relevant data fields.

    USE THIS TO LOOK UP:
    - Pokemon base stats, types, and capabilities
    - Opponent's revealed Pokemon information
    - Move details (power, accuracy, type, category, PP, effects)
    - Ability effects and descriptions
    - Item effects and descriptions
    - Nature stat modifications

    This is essential for understanding type matchups, calculating damage potential,
    and planning strategic decisions.

    Args:
        name: Name of the object to look up (e.g., "Landorus", "Earthquake",
              "Intimidate", "Choice Scarf", "Adamant")
        game_data: GameData singleton instance

    Returns:
        JSON string containing the object's data, including all relevant fields
        (stats, types, power, effects, etc.)

    Examples:
        Looking up a Pokemon:
        >>> get_object_game_data("Landorus", game_data)
        '{"name": "Landorus", "num": 645, "types": ["Ground", "Flying"], ...}'

        Looking up a move:
        >>> get_object_game_data("Earthquake", game_data)
        '{"name": "Earthquake", "type": "Ground", "base_power": 100, ...}'

        Looking up an ability:
        >>> get_object_game_data("Intimidate", game_data)
        '{"name": "Intimidate", "rating": 4.0, "description": "Lowers foe's Attack..."}'
    """
    try:
        obj = game_data.get_pokemon(name)
        return json.dumps(dataclasses.asdict(obj), indent=2)
    except ValueError:
        pass

    try:
        obj = game_data.get_move(name)
        return json.dumps(dataclasses.asdict(obj), indent=2)
    except ValueError:
        pass

    try:
        obj = game_data.get_ability(name)
        return json.dumps(dataclasses.asdict(obj), indent=2)
    except ValueError:
        pass

    try:
        obj = game_data.get_item(name)
        return json.dumps(dataclasses.asdict(obj), indent=2)
    except ValueError:
        pass

    try:
        obj = game_data.get_nature(name)
        return json.dumps(dataclasses.asdict(obj), indent=2)
    except ValueError:
        pass

    return json.dumps(
        {
            "error": f"Object '{name}' not found in game data",
        },
        indent=2,
    )
