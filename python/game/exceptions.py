"""Custom exceptions for game-related errors."""


class ServerErrorException(Exception):
    """Exception raised when the Pokemon Showdown server returns an error.

    This exception is raised by BattleEnvironment when it receives an ErrorEvent
    from the server. The agent can catch this and decide whether to retry the
    action.

    Attributes:
        error_text: The error message from the server
        battle_room: The battle room where the error occurred
    """

    def __init__(self, error_text: str, battle_room: str):
        """Initialize the ServerErrorException.

        Args:
            error_text: The error message from the server
            battle_room: The battle room identifier
        """
        self.error_text = error_text
        self.battle_room = battle_room
        super().__init__(f"Server error in {battle_room}: {error_text}")
