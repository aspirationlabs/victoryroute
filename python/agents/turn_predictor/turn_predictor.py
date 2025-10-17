from __future__ import annotations

from typing import Dict, Optional

from google.adk.agents import BaseAgent
from google.adk.sessions import BaseSessionService, InMemorySessionService, Session

from python.agents.agent_interface import Agent
from python.agents.battle_action_generator import BattleActionGenerator
from python.agents.tools.get_object_game_data import get_object_game_data
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
        def tool_get_object_game_data(name: str) -> str:
            """Look up game data for Pokemon, Move, Ability, Item, or Nature.
            Returns detailed stats, types, effects, and descriptions. Use to check:
            Pokemon base stats, move power/effects, ability mechanics, item effects, nature effects.
            Args:
                name: Object name (e.g., "Landorus", "Earthquake", "Intimidate", "Choice Scarf")
            """
            return get_object_game_data(name, self._game_data)

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
        primary_agent = LlmAgent(
            model=LiteLlm(model=model_name),
            name="battle_action_planner",
            instruction="",  # TODO: Add the system prompt to the promt_builder, and use it here.
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    include_thoughts=True,
                    thinking_budget=1024,
                )
            ),
            include_contents="none",
            tools=[tool_get_object_game_data],
            output_schema=DecisionProposal,
            output_key="decision_proposal",
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
        )

        critique_agent = LlmAgent(
            model=llm,
            name="risk_analyst",
            instruction="",  # TODO: Add the system prompt to the promt_builder, and use it here.
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    include_thoughts=True,
                    thinking_budget=1024,
                )
            ),
            include_contents="none",
            tools=[tool_get_object_game_data],
            output_schema=DecisionCritique,
            output_key="decision_critique",
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
        )

        final_agent = LlmAgent(
            model=llm,
            name="battle_action_lead",
            instruction="",  # TODO: Add the system prompt to the promt_builder, and use it here.
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    include_thoughts=True,
                    thinking_budget=1024,
                )
            ),
            include_contents="none",
            tools=[tool_get_object_game_data],
            output_schema=DecisionProposal,
            output_key="decision_proposal",
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
        )

        decision_loop = LoopAgent(
            name="battle_action_decision_loop",
            sub_agents=[primary_agent, critique_agent, final_agent],
            max_iterations=2,
        )

        return SequentialAgent(
            name="turn_predictor_workflow",
            sub_agents=[opponent_agent, simulation_agent, decision_loop],
        )

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
        return self.choose_action(state, battle_room, battle_stream_store)

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
