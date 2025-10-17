"""ADK entrypoint for the turn predictor agent."""

from google.adk.sessions import InMemorySessionService

from python.agents.turn_predictor.turn_predictor import TurnPredictorAgent
from python.game.environment.battle_stream_store import BattleStreamStore


def get_root_agent(battle_stream_store: BattleStreamStore):
    """Create and return the root TurnPredictorAgent.

    Args:
        battle_stream_store: Store for tracking battle events and actions

    Returns:
        Configured TurnPredictorAgent instance with ADK agent
    """
    agent = TurnPredictorAgent(
        session_service=InMemorySessionService(),
        model_name="openrouter/google/gemini-2.5-flash-lite-preview-09-2025",
        mode="gen9ou",
        past_actions_count=5,
        max_retries=3,
    )

    from python.agents.turn_predictor.turn_predictor_prompt_builder import (
        TurnPredictorPromptBuilder,
    )

    prompt_builder = TurnPredictorPromptBuilder(
        battle_stream_store=battle_stream_store, mode="gen9ou"
    )

    return agent._create_agent(
        model_name="openrouter/google/gemini-2.5-flash-lite-preview-09-2025",
        prompt_builder=prompt_builder,
    )


__all__ = ["get_root_agent"]
