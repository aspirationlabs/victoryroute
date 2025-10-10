# Battle Action Examples

These examples demonstrate correct action formatting for various battle scenarios.

## Example 1: Team Preview - Choosing Team Order

**Scenario**: Battle start, choosing which Pokemon to lead with and team order.

**Correct Response**:
```
{"reasoning": "Lead Ting-Lu for hazards, safe vs opponent's team.", "action_type": "team_order", "team_order": "163254"}
```

## Example 2: Setting Up Stealth Rock

**Scenario**: Turn 1, opponent has full team, want to set up entry hazards.

**Correct Response**:
```
{"reasoning": "Stealth Rock for chip damage on all switches.", "action_type": "move", "move_name": "Stealth Rock", "mega": false, "tera": false}
```

## Example 3: Type Immunity - Electric vs Ground

**Scenario**: Facing Ground/Flying type, considering Electric move.

**Correct Response**:
```
{"reasoning": "Electric immune vs Ground, using Hurricane instead.", "action_type": "move", "move_name": "Hurricane", "mega": false, "tera": false}
```

## Example 4: Attacking with Type Advantage

**Scenario**: Turn 5, opponent has Water-type active, I have Electric-type move.

**Correct Response**:
```
{"reasoning": "Thunder 2x vs Water, likely KO.", "action_type": "move", "move_name": "Thunder", "mega": false, "tera": false}
```

## Example 5: Switching on Unfavorable Matchup

**Scenario**: My Rock-type facing opponent's Water-type with strong Water moves.

**Correct Response**:
```
{"reasoning": "Rock weak to Water, Rillaboom resists.", "action_type": "switch", "switch_pokemon_name": "Rillaboom"}
```

## Example 6: Forced Switch After Faint

**Scenario**: My Pokemon just fainted, must choose replacement. The opponent has Zamazenta.

**Correct Response**:
```
{"reasoning": "Gardevoir resists Fighting, threatens Zamazenta.", "action_type": "switch", "switch_pokemon_name": "Gardevoir"}
```

## Example 7: Using Terastallization for STAB Boost

**Scenario**: Close battle, need extra power to secure KO with Tera boost.

**Correct Response**:
```
{"reasoning": "Tera Fire + Pyro Ball for 2x STAB secures KO.", "action_type": "move", "move_name": "Pyro Ball", "mega": false, "tera": true}
```

## Example 8: Pivot Move for Momentum

**Scenario**: My Pokemon has a type advantage over the opponent. I also want to maintain offensive pressure.

**Correct Response**:
```
{"reasoning": "U-turn deals damage and scouts opponent's next switch.", "action_type": "move", "move_name": "U-turn", "mega": false, "tera": false}
```

## Example 9: Status Move for Disruption

**Scenario**: Facing physical attacker like Rhyperior, burning will cripple their offense.

**Correct Response**:
```
{"reasoning": "Will-o-Wisp halves Rhyperior's Attack stat.", "action_type": "move", "move_name": "Will-o-Wisp", "mega": false, "tera": false}
```

## Example 10: Prediction Switch for Advantage

**Scenario**: Opponent likely to use Fighting move, switching to Ghost-type for immunity.

**Correct Response**:
```
{"reasoning": "Slowking-Galar immune to predicted Fighting move.", "action_type": "switch", "switch_pokemon_name": "Slowking-Galar"}
```
