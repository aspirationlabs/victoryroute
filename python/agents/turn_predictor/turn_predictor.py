from __future__ import annotations

from typing import Dict, Optional

from absl import logging
from google.adk.agents import BaseAgent, LlmAgent, LoopAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.planners import BuiltInPlanner
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, InMemorySessionService, Session
from google.genai import types

from python.agents.agent_interface import Agent
from python.agents.battle_action_generator import BattleActionGenerator
from python.agents.tools.battle_simulator import BattleSimulator
from python.agents.tools.get_object_game_data import get_object_game_data
from python.agents.tools.llm_event_logger import LlmEventLogger
from python.agents.tools.pokemon_state_priors_reader import PokemonStatePriorsReader
from python.agents.turn_predictor.action_simulation_agent import ActionSimulationAgent
from python.agents.turn_predictor.decision_schemas import (
    DecisionCritique,
    DecisionProposal,
)
from python.agents.turn_predictor.team_predictor_agent import TeamPredictorAgent
from python.agents.turn_predictor.turn_predictor_prompt_builder import (
    TurnPredictorPromptBuilder,
)
from python.game.data.game_data import GameData
from python.game.environment.battle_stream_store import BattleStreamStore
from python.game.interface.battle_action import ActionType, BattleAction
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
        self._agent = self._create_agent(model_name)

    def _create_agent(
        self,
        model_name: str,
    ) -> BaseAgent:
        def tool_get_object_game_data(name: str) -> str:
            """Look up game data for Pokemon, Move, Ability, Item, or Nature.
            Returns detailed stats, types, effects, and descriptions. Use to check:
            Pokemon base stats, move power/effects, ability mechanics, item effects, nature effects.
            Args:
                name: Object name (e.g., "Landorus", "Earthquake", "Intimidate", "Choice Scarf")
            """
            return get_object_game_data(name, self._game_data)

        priors_reader = PokemonStatePriorsReader(mode=self._mode)
        opponent_agent = TeamPredictorAgent(
            priors_reader=priors_reader,
            prompt_builder=self._prompt_builder,
            game_data=self._game_data,
            model_name=model_name,
            max_retries=self._max_retries,
        ).get_adk_agent
        simulation_agent = ActionSimulationAgent(
            name="action_simulation_agent",
            battle_simulator=BattleSimulator(game_data=self._game_data),
        )
        initial_decision_prompt = self._prompt_builder.get_initial_decision_prompt()
        critique_prompt = self._prompt_builder.get_decision_critique_prompt()
        final_decision_prompt = self._prompt_builder.get_final_decision_prompt()

        primary_agent = LlmAgent(
            model=LiteLlm(model=model_name),
            name="battle_action_planner",
            instruction=initial_decision_prompt,
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
            model=LiteLlm(model=model_name),
            name="risk_analyst",
            instruction=critique_prompt,
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
            model=LiteLlm(model=model_name),
            name="battle_action_lead",
            instruction=final_decision_prompt,
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

    @property
    def get_adk_agent(self) -> BaseAgent:
        return self._agent

    def _get_action_generator(
        self,
        battle_room: str,
    ) -> BattleActionGenerator:
        if battle_room not in self._battle_room_to_action_generator:
            raise ValueError(
                f"No action generator found for battle_room: {battle_room}"
            )
        return self._battle_room_to_action_generator[battle_room]

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
        session = await self._get_or_create_session(self._battle_room)

        if self._battle_room not in self._battle_room_to_logger:
            self._battle_room_to_logger[self._battle_room] = LlmEventLogger(
                battle_room=self._battle_room,
                player_name=state.our_player_id or "unknown",
                model_name=self._model_name,
            )

        turn_state = self._prompt_builder.get_new_turn_state_prompt(state)
        turn_state.update_session_state(session)
        runner = Runner(agent=self._agent, session_service=self._session_service)

        query_text = "Choose the best battle action for this turn."
        user_query = types.Content(
            parts=[types.Part(text=query_text)],
            role="user",
        )

        events = runner.run(
            user_id=self._battle_room,
            session_id=session.id,
            new_message=user_query,
        )

        final_proposal: Optional[DecisionProposal] = None
        for event in events:
            if event.is_final_response():
                if "decision_proposal" in session.state:
                    proposal_data = session.state["decision_proposal"]
                    if isinstance(proposal_data, dict):
                        final_proposal = DecisionProposal.model_validate(proposal_data)
                    elif isinstance(proposal_data, DecisionProposal):
                        final_proposal = proposal_data
                    break

        if final_proposal is None:
            raise ValueError("No decision proposal returned from agent workflow")

        logging.debug(
            "Final proposal for battle_room=%s: %s",
            self._battle_room,
            final_proposal.model_dump_json(),
        )

        action = self._convert_proposal_to_action(final_proposal)
        return action

    def _convert_proposal_to_action(self, proposal: DecisionProposal) -> BattleAction:
        action_type_str = proposal.action_type.lower()

        if action_type_str == "move":
            return BattleAction(
                action_type=ActionType.MOVE,
                move_name=proposal.move_name,
                mega=proposal.mega,
                tera=proposal.tera,
            )
        elif action_type_str == "switch":
            return BattleAction(
                action_type=ActionType.SWITCH,
                switch_pokemon_name=proposal.switch_pokemon_name,
            )
        elif action_type_str == "team_order":
            return BattleAction(
                action_type=ActionType.TEAM_ORDER,
                team_order=proposal.team_order,
            )
        else:
            raise ValueError(f"Unknown action_type: {action_type_str}")

    async def retry_action_on_server_error(
        self, error_text: str, state: BattleState
    ) -> Optional[BattleAction]:
        return await self.choose_action(state)

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
