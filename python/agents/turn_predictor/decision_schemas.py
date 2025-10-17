from typing import List, Optional

from pydantic import BaseModel, Field


class DecisionProposal(BaseModel):
    reason: str = Field(description="Comprehensive rationale (2-4 sentences)")
    action_type: str = Field(description="Type of action: move, switch, or team_order")
    move_name: Optional[str] = Field(
        default=None, description="Name of the move (required for move actions)"
    )
    switch_pokemon_name: Optional[str] = Field(
        default=None, description="Pokemon to switch to (required for switch actions)"
    )
    team_order: Optional[str] = Field(
        default=None,
        description="Team order as 6 digits, e.g. '123456' (required for team_order actions)",
    )
    mega: bool = Field(default=False, description="Whether to Mega Evolve")
    tera: bool = Field(default=False, description="Whether to Terastallize")
    upside: List[str] = Field(
        description="Benefits of this action (max 4 bullets)", default_factory=list
    )
    risks: List[str] = Field(
        description="Risks of this action (max 4 bullets)", default_factory=list
    )
    simulation_actions_considered: List[str] = Field(
        description="Simulation IDs or descriptions that informed this decision",
        default_factory=list,
    )


class DecisionCritique(BaseModel):
    issues_found: List[str] = Field(
        description="Match-losing risks not addressed by the proposal",
        default_factory=list,
    )
    overlooked_simulations: Optional[List[str]] = Field(
        default=None,
        description="Alternative simulations that suggest a different action",
    )
