# Turn {{TURN_NUMBER}} - Choose Your Action

## Your Player ID: {{OUR_PLAYER_ID}}

## Available Actions
{{AVAILABLE_ACTIONS}}

## Current Battle State
{{BATTLE_STATE}}

## Possible Opponent Actions
Note: This list represents potential actions the opponent could take based on known information. It may be inaccurate or incomplete - some moves may be unknown, and the opponent's full team composition may not yet be revealed. Use this as guidance to consider what the opponent might do, but don't rely on it as definitive.

{{OPPONENT_POTENTIAL_ACTIONS}}

## Past Player Actions (up to {{PAST_ACTIONS_COUNT}})
{{PAST_ACTIONS}}

## Past Server Events (up to {{PAST_ACTIONS_COUNT}})
{{PAST_RAW_EVENTS}}

## Directive
Based on the battle state, choose your optimal action considering:
- Current HP situation: Can you finish low-HP opponents? Are you at risk of being KO'd?
- Setup opportunities: Do you have time to setup, or is immediate action required?
- Information gaps: What crucial details should you verify with tool calls first before committing a battle action?

Return your decision as JSON with **brief reasoning (1-2 sentences max)** focused on the single most important factor driving your choice.
