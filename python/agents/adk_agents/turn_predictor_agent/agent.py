"""ADK entrypoint for the turn predictor agent."""

from python.agents.turn_predictor.turn_predictor_agent import TurnPredictorAgent

# TODO: Implement get_adk_agent and all the inputs into this root agent.
root_agent = TurnPredictorAgent().get_adk_agent

__all__ = ["root_agent"]
