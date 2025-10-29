"""ADK entrypoint for the turn predictor agent."""

from google.adk.sessions import InMemorySessionService

from python.agents.turn_predictor.turn_predictor import TurnPredictorAgent
from python.game.environment.battle_stream_store import BattleStreamStore

_turn_predictor_agent = TurnPredictorAgent(
    battle_room="test_battle_room",
    battle_stream_store=BattleStreamStore(),
    session_service=InMemorySessionService(),
    model_name="openai/gpt-5-nano",
    mode="gen9ou",
)
root_agent = _turn_predictor_agent.get_adk_agent
__all__ = ["root_agent"]
