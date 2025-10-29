"""ADK entrypoint for the opponent pokemon predictor agent."""

from python.agents.tools.pokemon_state_priors_reader import PokemonStatePriorsReader
from python.agents.turn_predictor.team_predictor_agent import TeamPredictorAgent
from python.agents.turn_predictor.turn_predictor_prompt_builder import (
    TurnPredictorPromptBuilder,
)
from python.game.data.game_data import GameData
from python.game.environment.battle_stream_store import BattleStreamStore

_team_predictor = TeamPredictorAgent(
    priors_reader=PokemonStatePriorsReader(),
    prompt_builder=TurnPredictorPromptBuilder(battle_stream_store=BattleStreamStore()),
    game_data=GameData(),
    model_name="openai/gpt-5-nano",
)

root_agent = _team_predictor.get_adk_agent

__all__ = ["root_agent"]
