from __future__ import annotations

from typing import Callable, Sequence

from google.adk.agents import LlmAgent, LoopAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.planners import BuiltInPlanner
from google.genai import types

from python.agents.turn_predictor.turn_predictor_prompt_builder import (
    TurnPredictorPromptBuilder,
)


class BattleActionLoopAgent(SequentialAgent):
    """Runs the proposal → critique/refinement workflow for battle actions."""

    _PROPOSAL_KEY = "decision_proposal_draft"
    _CRITIQUE_KEY = "decision_critique"

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

        self._proposal_agent = LlmAgent(
            model=LiteLlm(model=model_name),
            name="battle_action_planner",
            instruction=prompt_builder.get_initial_decision_prompt(),
            planner=planner,
            include_contents="none",
            tools=shared_tools,
            output_key=self._PROPOSAL_KEY,
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
            output_key=self._CRITIQUE_KEY,
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
            output_key=self._PROPOSAL_KEY,
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
        )

        self._critique_and_refinement_loop = LoopAgent(
            name="battle_action_review_loop",
            sub_agents=[critique_agent, refinement_agent],
            max_iterations=max_iterations,
        )

        super().__init__(
            name="battle_action_decision_sequence",
            sub_agents=[self._proposal_agent, self._critique_and_refinement_loop],
        )

    @property
    def proposal_output_key(self) -> str:
        return self._PROPOSAL_KEY
