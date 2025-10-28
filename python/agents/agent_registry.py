"""Agent registry for mapping agent names to agent classes."""

from typing import Callable, Dict

from python.agents.agent_interface import Agent
from python.agents.first_available_agent import FirstAvailableAgent
from python.agents.random_agent import RandomAgent
from python.agents.zero_shot.zero_shot_agent import ZeroShotAgent
from python.game.environment.battle_stream_store import BattleStreamStore


class AgentRegistry:
    """Registry for managing available agent types.

    This registry maps agent names (used in CLI) to their corresponding
    agent factory functions. It provides a centralized way to discover and
    instantiate agents.

    Agents are instantiated per-battle with the battle_room and battle_stream_store,
    allowing them to maintain battle-specific state.

    Example Usage:
        ```python
        # Get all available agent names
        agent_names = AgentRegistry.get_available_agents()

        # Create an agent by name for a specific battle
        agent = AgentRegistry.create_agent(
            "random",
            battle_room="battle-gen9ou-12345",
            battle_stream_store=env.get_battle_stream_store(),
        )

        # Check if agent exists
        if AgentRegistry.has_agent("first_move"):
            agent = AgentRegistry.create_agent(
                "first_move",
                battle_room=battle_room,
                battle_stream_store=battle_stream_store,
            )
        ```

    Attributes:
        _AGENT_MAP: Mapping from agent names to agent factory functions
    """

    _AGENT_MAP: Dict[str, Callable[[str, BattleStreamStore], Agent]] = {
        "random": lambda battle_room, battle_stream_store: RandomAgent(
            battle_room, battle_stream_store
        ),
        "first_move": lambda battle_room, battle_stream_store: FirstAvailableAgent(
            battle_room, battle_stream_store
        ),
        "zero_shot": lambda battle_room, battle_stream_store: ZeroShotAgent(
            battle_room, battle_stream_store
        ),
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
    def create_agent(
        cls, agent_name: str, battle_room: str, battle_stream_store: BattleStreamStore
    ) -> Agent:
        """Create an agent instance by name for a specific battle.

        Args:
            agent_name: Name of the agent to create (case insensitive)
            battle_room: The battle room identifier
            battle_stream_store: Store containing all battle events

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
        return agent_factory(battle_room, battle_stream_store)

    @classmethod
    def register_agent(
        cls, agent_name: str, agent_factory: Callable[[str, BattleStreamStore], Agent]
    ) -> None:
        """Register a new agent type.

        This allows extending the registry with custom agents at runtime.

        Args:
            agent_name: Name to register the agent under (will be lowercased)
            agent_factory: Callable that takes battle_room and battle_stream_store
                          and creates an agent instance

        Raises:
            ValueError: If agent_name is already registered
        """
        normalized_name = agent_name.lower()

        if normalized_name in cls._AGENT_MAP:
            raise ValueError(f"Agent '{agent_name}' is already registered")

        cls._AGENT_MAP[normalized_name] = agent_factory
