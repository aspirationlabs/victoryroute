def normalize_name(name: str) -> str:
    """Normalize Pokemon object names to match Pokemon Showdown's toID function.

    Converts names to lowercase and removes all non-alphanumeric characters.
    This handles species, moves, abilities, items, and natures consistently.

    Matches Pokemon Showdown's toID() implementation:
    text.toLowerCase().replace(/[^a-z0-9]+/g, '')

    Args:
        name: The name to normalize (e.g., "Farfetch'd", "Will-O-Wisp", "Mr. Mime")

    Returns:
        Normalized name with only lowercase alphanumeric characters

    Examples:
        >>> normalize_name("Farfetch'd")
        'farfetchd'
        >>> normalize_name("Will-O-Wisp")
        'willowisp'
        >>> normalize_name("Mr. Mime")
        'mrmime'
        >>> normalize_name("Nidoran♀")
        'nidoran'
    """
    return "".join(c for c in name.lower() if c.isalnum())
