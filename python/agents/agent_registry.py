"""Agent registry for mapping agent names to agent classes."""

from typing import Callable, Dict

from python.agents.agent_interface import Agent
from python.agents.first_available_agent import FirstAvailableAgent
from python.agents.random_agent import RandomAgent
from python.agents.zero_shot_no_history_agent import ZeroShotNoHistoryAgent


class AgentRegistry:
    """Registry for managing available agent types.

    This registry maps agent names (used in CLI) to their corresponding
    agent factory functions. It provides a centralized way to discover and
    instantiate agents.

    Example Usage:
        ```python
        # Get all available agent names
        agent_names = AgentRegistry.get_available_agents()

        # Create an agent by name
        agent = AgentRegistry.create_agent("random")

        # Check if agent exists
        if AgentRegistry.has_agent("first_move"):
            agent = AgentRegistry.create_agent("first_move")
        ```

    Attributes:
        _AGENT_MAP: Mapping from agent names to agent factory functions
    """

    _AGENT_MAP: Dict[str, Callable[[], Agent]] = {
        "random": lambda: RandomAgent(),
        "first_move": lambda: FirstAvailableAgent(),
        "zero_shot": lambda: ZeroShotNoHistoryAgent(),
    }

    @classmethod
    def get_available_agents(cls) -> list[str]:
        """Get list of all available agent names.

        Returns:
            List of agent names that can be used with create_agent()
        """
        return sorted(cls._AGENT_MAP.keys())

    @classmethod
    def has_agent(cls, agent_name: str) -> bool:
        """Check if an agent with the given name exists.

        Args:
            agent_name: Name of the agent to check

        Returns:
            True if agent exists, False otherwise
        """
        return agent_name.lower() in cls._AGENT_MAP

    @classmethod
    def create_agent(cls, agent_name: str) -> Agent:
        """Create an agent instance by name.

        Args:
            agent_name: Name of the agent to create (case insensitive)

        Returns:
            Instance of the requested agent

        Raises:
            ValueError: If agent_name is not registered
        """
        normalized_name = agent_name.lower()

        if normalized_name not in cls._AGENT_MAP:
            available = ", ".join(cls.get_available_agents())
            raise ValueError(
                f"Unknown agent: '{agent_name}'. Available agents: {available}"
            )

        agent_factory = cls._AGENT_MAP[normalized_name]
        return agent_factory()

    @classmethod
    def register_agent(
        cls, agent_name: str, agent_factory: Callable[[], Agent]
    ) -> None:
        """Register a new agent type.

        This allows extending the registry with custom agents at runtime.

        Args:
            agent_name: Name to register the agent under (will be lowercased)
            agent_factory: Callable that creates an agent instance

        Raises:
            ValueError: If agent_name is already registered
        """
        normalized_name = agent_name.lower()

        if normalized_name in cls._AGENT_MAP:
            raise ValueError(f"Agent '{agent_name}' is already registered")

        cls._AGENT_MAP[normalized_name] = agent_factory
