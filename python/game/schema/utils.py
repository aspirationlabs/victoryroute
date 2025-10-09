"""Utility functions for schema operations."""


def normalize_move_name(move_name: str) -> str:
    """Normalize a move name for matching.

    Converts move names to lowercase and removes spaces and hyphens
    to handle different formatting from events vs requests.
    (e.g., "Swords Dance" → "swordsdance", "Will-O-Wisp" → "willowisp")

    Args:
        move_name: Move name to normalize

    Returns:
        Normalized move name for matching
    """
    return move_name.lower().replace(" ", "").replace("-", "")
