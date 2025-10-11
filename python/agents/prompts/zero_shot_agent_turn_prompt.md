# Turn {{TURN_NUMBER}} - Choose Your Action

## Your Player ID: {{OUR_PLAYER_ID}}

## Available Actions
{{AVAILABLE_ACTIONS}}

## Current Battle State
{{BATTLE_STATE}}

## Opponent Potential Actions
Based on known information about the opponent's active Pokemon and team. Consider these when choosing defensive switches or predicting threats.

{{OPPONENT_POTENTIAL_ACTIONS}}

## Past Player Actions (up to {{PAST_ACTIONS_COUNT}})
{{PAST_ACTIONS}}

## Past Server Events (up to {{PAST_SERVER_COUNT}})
{{PAST_RAW_EVENTS}}

## Directive
Based on the battle state and server events, choose your optimal action considering:

**Previous Turn Analysis** (from server events):
- What actually happened: Did your move deal expected damage? Was it resisted/super-effective/missed/failed?
- Opponent's moves: What effectiveness/damage did their moves show?
- Status/stat changes: Were there any burns, stat boosts, item activations?
- If outcomes were unexpected (low damage, resistance, immunity), adjust strategy accordingly

**Current Situation**:
- Opponent threats: What can the opponent do? Should you switch to resist their likely moves or stay in for offensive pressure?
- Lessons from previous turns: Did previous outcomes reveal type resistances, immunities, or damage ranges that should inform this decision?
- Current HP situation: Can you finish low-HP opponents? Are you at risk of being KO'd?
- Setup opportunities: Do you have time to setup, or is immediate action required?
- Information gaps: What crucial details should you verify with tool calls first before committing a battle action?

Return your decision as JSON with **brief reasoning (1-2 sentences max)** focused on the single most important factor driving your choice.
