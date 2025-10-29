from __future__ import annotations

from typing import Callable, Sequence

from google.adk.agents import BaseAgent, LlmAgent, LoopAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.planners import BuiltInPlanner
from google.genai import types

from python.agents.battle_action_generator import BattleActionResponse
from python.agents.turn_predictor.json_llm_agent import JsonLlmAgent
from python.agents.turn_predictor.turn_predictor_prompt_builder import (
    TurnPredictorPromptBuilder,
)


class BattleActionLoopAgent:
    """Runs the proposal → critique/refinement workflow for battle actions."""

    def __init__(
        self,
        *,
        model_name: str,
        prompt_builder: TurnPredictorPromptBuilder,
        tools: Sequence[Callable[..., str]],
        max_iterations: int = 1,
    ) -> None:
        planner = BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=True,
                thinking_budget=1024,
            )
        )

        shared_tools = list(tools)

        proposal_agent = LlmAgent(
            model=LiteLlm(model=model_name),
            name="battle_action_planner",
            instruction=prompt_builder.get_initial_decision_prompt(),
            planner=planner,
            include_contents="none",
            tools=shared_tools,
            output_key="decision_proposal_draft",
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
        )

        critique_agent = LlmAgent(
            model=LiteLlm(model=model_name),
            name="risk_analyst",
            instruction=prompt_builder.get_decision_critique_prompt(),
            planner=planner,
            include_contents="none",
            tools=shared_tools,
            output_key="decision_critique",
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
        )

        refinement_agent = LlmAgent(
            model=LiteLlm(model=model_name),
            name="battle_action_refiner",
            instruction=prompt_builder.get_final_decision_prompt(),
            planner=planner,
            include_contents="none",
            tools=shared_tools,
            output_key="decision_proposal_draft",
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
        )

        loop_agent = LoopAgent(
            name="battle_action_review_loop",
            sub_agents=[critique_agent, refinement_agent],
            max_iterations=max_iterations,
        )

        sequential_agent = SequentialAgent(
            name="battle_action_decision_sequence",
            sub_agents=[proposal_agent, loop_agent],
        )

        self._agent: JsonLlmAgent[BattleActionResponse] = JsonLlmAgent(
            base_agent=sequential_agent,
            output_schema=BattleActionResponse,
            data_input_key="decision_proposal_draft",
            json_output_key="decision_proposal",
            model=LiteLlm(model=model_name),
        )

    @property
    def get_adk_agent(self) -> BaseAgent:
        return self._agent
