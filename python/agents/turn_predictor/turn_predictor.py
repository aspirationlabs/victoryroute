from __future__ import annotations

from typing import Dict, Optional

from google.adk.agents import BaseAgent
from google.adk.sessions import BaseSessionService, InMemorySessionService, Session

from python.agents.agent_interface import Agent
from python.agents.battle_action_generator import BattleActionGenerator
from python.agents.tools.llm_event_logger import LlmEventLogger
from python.agents.turn_predictor.turn_predictor_prompt_builder import (
    TurnPredictorPromptBuilder,
)
from python.game.data.game_data import GameData
from python.game.environment.battle_stream_store import BattleStreamStore
from python.game.interface.battle_action import BattleAction
from python.game.schema.battle_state import BattleState


class TurnPredictorAgent(Agent):
    def __init__(
        self,
        battle_room: str,
        battle_stream_store: BattleStreamStore,
        session_service: BaseSessionService = InMemorySessionService(),
        model_name: str = "openrouter/google/gemini-2.5-flash-lite-preview-09-2025",
        mode: str = "gen9ou",
        past_actions_count: int = 5,
        max_retries: int = 3,
    ):
        super().__init__(battle_room, battle_stream_store)
        self._session_service: BaseSessionService = session_service
        self._model_name: str = model_name
        self._mode: str = mode
        self._app_name: str = "turn_predictor_pokemon_battler_agent"
        self._game_data: GameData = GameData()
        self._max_retries: int = max_retries
        self._battle_room_to_logger: Dict[str, LlmEventLogger] = {}
        self._battle_room_to_session: Dict[str, Session] = {}
        self._battle_room_to_action_generator: Dict[str, BattleActionGenerator] = {}
        self._prompt_builder: TurnPredictorPromptBuilder = TurnPredictorPromptBuilder(
            battle_stream_store, mode=mode
        )

    def _create_agent(self, model_name, app_name, system_instructions) -> BaseAgent:
        # User query will provide:
        # state['turn_number'] -> str (input)
        # state['our_player_id'] -> str (input)
        # state['available_actions'] -> List[str] (input) or List[BattleAction]
        # state['battle_state'] -> BattleState (input)
        # state['opponent_potential_actions'] -> str (input) or List[BattleAction]
        # state['opponent_active_pokemon'] -> PokemonState (input)
        # state['past_battle_event_logs_xml'] -> string (input) or dict[int, str]
        # state['past_player_actions_xml'] -> string (input) or dict[str, List[BattleAction]]

        # TODO: Implement this method properly
        # priors_reader = PokemonStatePriorsReader(mode=self._mode)
        # TODO: Pass battle_stream_store into agent constructors, rather than in choose_action.
        # prompt_builder = TurnPredictorPromptBuilder(
        #     battle_stream_store=None, mode=self._mode
        # )
        # TODO: Use this TeamPredictorAgent in the implementation
        # team_predictor_agent = TeamPredictorAgent(
        #     priors_reader=priors_reader,
        #     prompt_builder=prompt_builder,
        #     model_name=self._model_name,
        #     max_retries=self._max_retries,
        # )
        # TODO: Use this ActionSimulationAgent in the implementation
        # action_simulation_agent = ActionSimulationAgent(
        #     name="action_simulation_agent",
        #     battle_simulator=BattleSimulator(),
        # )

        # TODO: Create a LoopAgent.
        # Based on the simulation actions, choose the best available move/switch we use.
        # Reason based on what the moves do, the opponent potential actions, and potential simulations to guide damage and outcomes.
        # For example, if a simulation includes a setup move and opponent can KO, probably don't want to use the setup move.
        # If the opponent doesn't have a setup move and no real damage moves, it's probably safe to set up.
        # Protect can scout.
        # Priority moves can move first to try to KO. Opt for damage/KO when possible.
        # - state['battle_state']
        # - state['available_actions']
        # - state['available_opponent_actions'] (?)
        # - state['simulation_actions']
        # tool call: get_object_game_data.
        # Agent 1: Output first action.
        # Agent 2: Critique (what edge cases did you not consider in either the simulation actions or potential opponent actions not in simulation that can be a threat, adn why is it a threat? Do you reconsider or update your rationale? Why? If you update your rationale, what is the new rationale?)
        # Agent 3: Output a new action or update rationale. Reformat and make sure you output a proper BattleAction.
        # Output: BattleAction.
        # ...
        # TODO: Implement this method to return a proper BaseAgent
        raise NotImplementedError("_create_agent not yet implemented")

    def _get_action_generator(
        self, battle_room: str, player_name: str
    ) -> BattleActionGenerator:
        raise NotImplementedError("get_action_generator not implemented")

    async def _get_or_create_session(self, battle_room: str) -> Session:
        session = self._battle_room_to_session.get(battle_room)
        if session is None:
            session = await self._session_service.create_session(
                app_name=self._app_name,
                user_id=battle_room,
            )
            self._battle_room_to_session[battle_room] = session
        return session

    async def choose_action(self, state: BattleState) -> BattleAction:
        raise NotImplementedError("choose_action not implemented")

    async def retry_action_on_server_error(
        self, error_text: str, state: BattleState
    ) -> Optional[BattleAction]:
        raise NotImplementedError("retry_action_on_server_error not implemented")

    async def cleanup_battle(self, battle_room: str) -> None:
        if battle_room in self._battle_room_to_logger:
            self._battle_room_to_logger[battle_room].close()
            del self._battle_room_to_logger[battle_room]
        if battle_room in self._battle_room_to_session:
            session = self._battle_room_to_session.pop(battle_room)
            await self._session_service.delete_session(
                app_name=self._app_name,
                user_id=battle_room,
                session_id=session.id,
            )
        if battle_room in self._battle_room_to_action_generator:
            del self._battle_room_to_action_generator[battle_room]
