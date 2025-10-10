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
{"reasoning": "The opponent doesn't have a Pokemon with typing that can potentially threaten Ting-Lu in one hit. By starting with Ting-Lu, I can attempt to set up hazards, and switch out if necessary.", "action_type": "team_order", "team_order": "163254"}
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
{"reasoning": "Stealth Rock provides chip on switches, and it isn't already set up. The opponent Pokemon doesn't have any move that can deal major damage to Ting-Lu, and likely cannot set up either. Ting-Lu can threaten with an offensive move as well.", "action_type": "move", "move_name": "Stealth Rock", "mega": false, "tera": false}
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
{"reasoning": "Rock weak to Water. Rillaboom resists as a grass type, and pivots safely.", "action_type": "switch", "switch_pokemon_name": "Rillaboom"}
```

## Example 5: Forced Switch After Faint

**Scenario**: My Pokemon just fainted, must choose replacement. The opponent has Zamazenta.

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
{"reasoning": "Forced switch. Gardevoir is Psychic and Fairy, resisting Zamazenta's Fighting type, and it has moves that threaten Zamazenta.", "action_type": "switch", "switch_pokemon_name": "Gardevoir"}
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

**Scenario**: My Pokemon has a type advantage over the opponent. I also want to maintain offensive pressure.

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
{"reasoning": "U-turn for damage and momentum. Opponent might switch, so using a move like Sucker Punch would potentially not be effective, based on its move description.", "action_type": "move", "move_name": "U-turn", "mega": false, "tera": false}
```

## Example 8: Status Move for Disruption

**Scenario**: Facing physical attacker like Rhyperior, burning will cripple their offense.

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
{"reasoning": "Rhyperior has high Attack stat from game data. Will-o-Wisp burns attacker and halves Attack, so I'll take less damage and deal chip damage.", "action_type": "move", "move_name": "Will-o-Wisp", "mega": false, "tera": false}
```

## Example 9: Prediction Switch for Advantage

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
{"reasoning": "Predict Close Combat. Gengar Ghost immunity, and can threaten with Psychic given its moveset.", "action_type": "switch", "switch_pokemon_name": "Slowking-Galar"}
```
