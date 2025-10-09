# Battle Action Examples

These examples demonstrate correct action formatting for various battle scenarios.

## Example 1: Team Preview - Choosing Team Order

**Scenario**: Battle start, choosing which Pokemon to lead with and team order.

**Available Actions**:
```json
{
  "moves": [],
  "switches": [],
  "can_mega": false,
  "can_tera": false,
  "can_dynamax": false,
  "force_switch": false,
  "team_preview": true
}
```

**Correct Response**:
```
{"reasoning": "Lead Ting-Lu for hazards, Corviknight as pivot, Darkrai for late-game.", "action_type": "team_order", "team_order": "163254"}
```

## Example 2: Setting Up Stealth Rock

**Scenario**: Turn 1, opponent has full team, want to set up entry hazards.

**Available Actions**:
```json
{
  "moves": ["Stealth Rock", "Earthquake", "Ruination", "Whirlwind"],
  "switches": [1, 2, 3, 4, 5],
  "can_mega": false,
  "can_tera": true,
  "can_dynamax": false,
  "force_switch": false,
  "team_preview": false
}
```

**Correct Response**:
```
{"reasoning": "Stealth Rock provides chip on switches. Critical setup.", "action_type": "move", "move_name": "Stealth Rock", "mega": false, "tera": false}
```

## Example 3: Attacking with Type Advantage

**Scenario**: Turn 5, opponent has Water-type active, I have Electric-type move.

**Available Actions**:
```json
{
  "moves": ["Thunder", "Ice Beam", "Volt Switch", "Hidden Power"],
  "switches": [0, 2, 4],
  "can_mega": false,
  "can_tera": false,
  "can_dynamax": false,
  "force_switch": false,
  "team_preview": false
}
```

**Correct Response**:
```
{"reasoning": "Thunder super effective vs Water (2x). High power likely KOs.", "action_type": "move", "move_name": "Thunder", "mega": false, "tera": false}
```

## Example 4: Switching on Unfavorable Matchup

**Scenario**: My Rock-type facing opponent's Water-type with strong Water moves.

**Available Actions**:
```json
{
  "moves": ["Stone Edge", "Earthquake", "Fire Blast", "Stealth Rock"],
  "switches": [1, 3, 4],
  "can_mega": false,
  "can_tera": false,
  "can_dynamax": false,
  "force_switch": false,
  "team_preview": false
}
```

**Correct Response**:
```
{"reasoning": "Rock weak to Water. Corviknight resists and pivots safely.", "action_type": "switch", "switch_pokemon_name": "Corviknight"}
```

## Example 5: Forced Switch After Faint

**Scenario**: My Pokemon just fainted, must choose replacement.

**Available Actions**:
```json
{
  "moves": [],
  "switches": [0, 2, 3, 5],
  "can_mega": false,
  "can_tera": false,
  "can_dynamax": false,
  "force_switch": true,
  "team_preview": false
}
```

**Correct Response**:
```
{"reasoning": "Forced switch. Darkrai Choice Scarf for speed.", "action_type": "switch", "switch_pokemon_name": "Darkrai"}
```

## Example 6: Using Terastallization for STAB Boost

**Scenario**: Close battle, need extra power to secure KO with Tera boost.

**Available Actions**:
```json
{
  "moves": ["Pyro Ball", "U-turn", "Court Change", "Will-o-Wisp"],
  "switches": [1, 2, 4, 5],
  "can_mega": false,
  "can_tera": true,
  "can_dynamax": false,
  "force_switch": false,
  "team_preview": false
}
```

**Correct Response**:
```
{"reasoning": "Tera Fire + Pyro Ball for 2x STAB. Secures KO.", "action_type": "move", "move_name": "Pyro Ball", "mega": false, "tera": true}
```

## Example 7: Pivot Move for Momentum

**Scenario**: Opponent likely to switch, want to maintain offensive pressure.

**Available Actions**:
```json
{
  "moves": ["U-turn", "Knock Off", "Sucker Punch", "First Impression"],
  "switches": [1, 2, 3, 4, 5],
  "can_mega": false,
  "can_tera": false,
  "can_dynamax": false,
  "force_switch": false,
  "team_preview": false
}
```

**Correct Response**:
```
{"reasoning": "U-turn for damage and momentum. Opponent likely switching.", "action_type": "move", "move_name": "U-turn", "mega": false, "tera": false}
```

## Example 8: Status Move for Disruption

**Scenario**: Facing physical attacker, burning will cripple their offense.

**Available Actions**:
```json
{
  "moves": ["Will-o-Wisp", "Hex", "Protect", "Shadow Ball"],
  "switches": [0, 1, 3, 4],
  "can_mega": false,
  "can_tera": false,
  "can_dynamax": false,
  "force_switch": false,
  "team_preview": false
}
```

**Correct Response**:
```
{"reasoning": "Will-o-Wisp burns attacker, halves Attack. Long-term value.", "action_type": "move", "move_name": "Will-o-Wisp", "mega": false, "tera": false}
```

## Example 9: Defensive Play When Low HP

**Scenario**: My Pokemon at 15% HP, opponent at 60% HP, need to preserve Pokemon.

**Available Actions**:
```json
{
  "moves": ["Earthquake", "Stone Edge", "Stealth Rock", "Protect"],
  "switches": [1, 3, 4, 5],
  "can_mega": false,
  "can_tera": false,
  "can_dynamax": false,
  "force_switch": false,
  "team_preview": false
}
```

**Correct Response**:
```
{"reasoning": "At 15% HP preserve Pokemon. Corviknight defensive answer.", "action_type": "switch", "switch_pokemon_name": "Corviknight"}
```

## Example 10: Prediction Switch for Advantage

**Scenario**: Opponent likely to use Fighting move, switching to Ghost-type for immunity.

**Available Actions**:
```json
{
  "moves": ["Ice Beam", "Freeze-Dry", "Earth Power", "Blizzard"],
  "switches": [0, 2, 3, 5],
  "can_mega": false,
  "can_tera": true,
  "can_dynamax": false,
  "force_switch": false,
  "team_preview": false
}
```

**Correct Response**:
```
{"reasoning": "Predict Close Combat. Slowking-Galar Ghost immunity, free turn.", "action_type": "switch", "switch_pokemon_name": "Slowking-Galar"}
```
