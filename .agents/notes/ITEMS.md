# Item Effects Implementation Plan

## Overview

This document outlines the implementation plan for item effects in the battle simulator. There are 537 items total in Pokemon Showdown, but we'll focus on commonly used items in Gen 9 OU for the initial implementation.

## Item Effect Categories

Based on Pokemon Showdown's implementation patterns, items can be categorized by their effect types:

### 1. Damage Modifiers
Items that modify damage dealt or received:
- **Life Orb**: 1.3x damage, 10% recoil
- **Choice Band/Specs**: 1.5x Atk/SpA, locks into one move
- **Expert Belt**: 1.2x damage on super-effective hits
- **Type Plates/Gems**: Boost specific type moves
- **Assault Vest**: 1.5x SpD, can't use status moves

**State Transition Hooks Needed:**
- `onModifyDamage` - before damage calculation
- `onAfterMoveSecondarySelf` - for recoil effects
- `onModifyAtk/onModifySpA` - for stat modifications

### 2. Speed Modifiers
Items that affect speed:
- **Choice Scarf**: 1.5x Speed, locks into one move
- **Iron Ball**: Halves Speed, removes Ground immunity
- **Quick Claw**: 20% chance to move first

**State Transition Hooks Needed:**
- `onModifySpe` - during speed calculation
- `onStart` - for Choice lock initialization
- Priority modification system for Quick Claw

### 3. Healing/Residual Effects
Items that heal or cause damage over time:
- **Leftovers**: Heal 1/16 HP each turn
- **Black Sludge**: Heal 1/16 HP (Poison-type) or damage (others)
- **Rocky Helmet**: Deal 1/6 HP to contact move users
- **Sticky Barb**: Damage holder, transfers on contact

**State Transition Hooks Needed:**
- `onResidual` - end-of-turn effects via `UpkeepEvent`
- `onDamagingHit` - when holder is hit
- New event type: `ItemDamageEvent` or `ItemHealEvent`

### 4. Berries
Items that activate on specific conditions:
- **Sitrus Berry**: Heal 25% HP at 50% HP or less
- **Oran Berry**: Heal 10 HP when damaged
- **Status Berries**: Cure specific status conditions
- **Stat-boost Berries**: Raise stat when HP low

**State Transition Hooks Needed:**
- `onDamagingHit` - trigger condition check
- `onAfterDamage` - post-damage HP check
- Item consumption tracking
- New event: `ItemConsumedEvent`

### 5. Protective Items
Items that prevent damage or status:
- **Focus Sash**: Survive OHKO at full HP
- **Focus Band**: 10% chance to survive fatal hit
- **Air Balloon**: Ground immunity until hit
- **Safety Goggles**: Powder/weather immunity

**State Transition Hooks Needed:**
- `onDamage` - intercept and modify damage
- `onSetStatus` - prevent status application
- Item breaking/consumption on activation

### 6. Choice Items
Items that lock the user into one move:
- **Choice Band**: 1.5x Atk
- **Choice Scarf**: 1.5x Speed
- **Choice Specs**: 1.5x SpA

**State Transition Hooks Needed:**
- `onStart` - clear previous choice lock
- `onModifyMove` - apply choice lock
- Volatile condition: `choicelock`
- Track last move used

### 7. Weather/Terrain Extenders
Items that extend field conditions:
- **Heat Rock**: Extends sun from 5 to 8 turns
- **Damp Rock**: Extends rain from 5 to 8 turns
- **Smooth Rock**: Extends sandstorm
- **Icy Rock**: Extends snow
- **Terrain Extenders**: Extend terrain duration

**State Transition Hooks Needed:**
- Modify `WeatherEvent` duration
- Modify terrain event duration
- Check item on weather/terrain start

### 8. Ability/Form Change Items
Items that affect abilities or forms:
- **Ability Shield**: Prevents ability changes
- **Booster Energy**: Activates Paradox abilities
- **Rusted Sword/Shield**: Enables Crowned forms

**State Transition Hooks Needed:**
- `onSetAbility` - prevent ability changes
- Form change tracking
- Ability activation conditions

### 9. Z-Crystals and Mega Stones
Items for special mechanics (Gen 6-7):
- **Mega Stones**: Enable Mega Evolution
- **Z-Crystals**: Enable Z-Moves

**State Transition Hooks Needed:**
- Track mega/Z-move availability
- Form change on mega evolution
- Z-move power calculation

### 10. Miscellaneous
Other unique item effects:
- **Eviolite**: 1.5x Def/SpD for unevolved Pokemon
- **Light Clay**: Extend screens from 5 to 8 turns
- **Weakness Policy**: +2 Atk/SpA when hit super-effectively
- **Throat Spray**: +1 SpA when using sound move

**State Transition Hooks Needed:**
- Item-specific condition checks
- Complex trigger conditions
- Multiple effect types per item

## Priority Items for Gen 9 OU

Based on usage statistics, these are the most common items in Gen 9 OU (approximately top 30):

### Tier 1 - Critical (Implement First)
1. **Leftovers** - Residual healing
2. **Choice Scarf** - Speed boost + choice lock
3. **Choice Band** - Attack boost + choice lock
4. **Choice Specs** - Sp. Atk boost + choice lock
5. **Heavy-Duty Boots** - Hazard immunity
6. **Life Orb** - Damage boost + recoil
7. **Focus Sash** - Survive OHKO
8. **Assault Vest** - Sp. Def boost, no status moves

### Tier 2 - Common
9. **Sitrus Berry** - HP restoration
10. **Booster Energy** - Paradox ability activation
11. **Protective Pads** - No contact effects
12. **Eviolite** - Defense boost for NFE
13. **Expert Belt** - Super-effective boost
14. **Weakness Policy** - Stat boost when hit SE
15. **Air Balloon** - Ground immunity

### Tier 3 - Situational
16. **Mental Herb** - Infatuation/Taunt cure
17. **Mirror Herb** - Copy stat boosts
18. **Covert Cloak** - Secondary effect immunity
19. **Clear Amulet** - Stat drop immunity
20. **Rocky Helmet** - Contact damage
21. **Loaded Dice** - Multi-hit move boost
22. **Light Clay** - Screen extension
23. **Type-specific items** (Muscle Band, Wise Glasses, etc.)

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)
**Goal**: Add item effect system to state transitions

**Tasks**:
1. Add item tracking to `PokemonState`:
   - `held_item: Optional[str]`
   - `item_consumed: bool`

2. Create new event types:
   - `ItemActivateEvent` - Item effect triggered
   - `ItemConsumedEvent` - Item used up
   - `ItemDamageEvent` - Item causes damage
   - `ItemHealEvent` - Item heals HP

3. Add item effect hook system to `StateTransition`:
   - `_apply_item_activate()`
   - `_apply_item_consumed()`
   - `_check_item_effects()` - helper to check if item should activate

4. Update `UpkeepEvent` handler to check for residual items (Leftovers, Black Sludge)

**Deliverables**:
- Item effect infrastructure in place
- Tests for item activation/consumption
- No actual item effects yet, just the system

### Phase 2: Tier 1 Items (Weeks 3-4)
**Goal**: Implement the 8 most critical items

**Tasks**:
1. Implement **Leftovers**:
   - Add residual healing in `UpkeepEvent`
   - Test: Pokemon heals 1/16 HP each turn

2. Implement **Choice items** (Band/Scarf/Specs):
   - Add `choicelock` volatile condition
   - Track last move used
   - Apply stat modifiers
   - Test: Stat boost + move lock

3. Implement **Life Orb**:
   - Damage modifier: 1.3x
   - Recoil after damaging moves
   - Test: Damage boost + 10% recoil

4. Implement **Focus Sash**:
   - Survive OHKO at full HP
   - Item consumed after use
   - Test: Survive killing blow

5. Implement **Assault Vest**:
   - 1.5x Sp. Def modifier
   - Prevent status move selection
   - Test: Sp. Def boost, no status moves

6. Implement **Heavy-Duty Boots**:
   - Ignore entry hazard damage
   - Test: Switch in without hazard damage

**Deliverables**:
- 8 Tier 1 items fully functional
- Comprehensive tests for each item
- Battle scenario tests (e.g., Life Orb KO + recoil faints)

### Phase 3: Tier 2 Items (Weeks 5-6)
**Goal**: Implement 7 common items

**Tasks**:
1. **Berries** (Sitrus Berry):
   - HP threshold checking
   - Item consumption
   - Test: Heal when HP drops below 50%

2. **Booster Energy**:
   - Paradox ability activation
   - Stat boost application
   - Test: Activate Protosynthesis/Quark Drive

3. **Protective Pads**:
   - Prevent contact effects
   - Test: No Rocky Helmet damage

4. **Eviolite**:
   - Check if Pokemon is NFE
   - 1.5x Def/SpD boost
   - Test: Boost for Chansey, no boost for Blissey

5. **Expert Belt**:
   - Check move effectiveness
   - 1.2x damage on super-effective
   - Test: Damage boost calculation

6. **Weakness Policy**:
   - Trigger on super-effective hit
   - +2 Atk/SpA boost
   - Item consumed
   - Test: Stat boost after SE hit

7. **Air Balloon**:
   - Ground immunity
   - Pop when hit
   - Test: Immune to Ground, then pop

**Deliverables**:
- 7 Tier 2 items implemented
- Complex interaction tests (e.g., Weakness Policy + super-effective hit)

### Phase 4: Tier 3 Items (Week 7-8)
**Goal**: Implement situational items as needed

**Tasks**:
- Implement items based on meta relevance
- Focus on unique mechanics (Mirror Herb, Clear Amulet)
- Add item effects that interact with abilities

**Deliverables**:
- Additional 10-15 items implemented
- Full coverage of common Gen 9 OU items

### Phase 5: Polish & Testing (Week 9-10)
**Goal**: Integration testing and edge cases

**Tasks**:
1. Battle scenario tests:
   - Choice lock + Trick/Switcheroo
   - Focus Sash + multi-hit moves
   - Item consumption + Recycle
   - Knock Off removing items

2. Performance testing:
   - Item effect hooks don't slow down battles
   - Memory usage with item tracking

3. Documentation:
   - Item effect descriptions
   - How to add new items
   - Known limitations

**Deliverables**:
- All Tier 1-3 items fully tested
- Edge case handling
- Documentation

## State Transition Event Mapping

### New Events Needed

```python
@dataclass(frozen=True)
class ItemActivateEvent(BattleEvent):
    """Item effect activated."""
    pokemon: str  # Pokemon identifier
    item: str  # Item name
    effect: str  # Effect description

@dataclass(frozen=True)
class ItemConsumedEvent(BattleEvent):
    """Item was consumed/used up."""
    pokemon: str
    item: str

@dataclass(frozen=True)
class ItemDamageEvent(BattleEvent):
    """Item caused damage (e.g., Rocky Helmet, Life Orb)."""
    pokemon: str
    item: str
    damage: int
    source: Optional[str]  # Source Pokemon if applicable

@dataclass(frozen=True)
class ItemHealEvent(BattleEvent):
    """Item healed HP (e.g., Leftovers, Sitrus Berry)."""
    pokemon: str
    item: str
    hp_healed: int
```

### Event Hook Points

Items need to hook into various points in the battle flow:

1. **onStart** (switch in):
   - Choice items: Clear choice lock
   - Air Balloon: Add immunity
   - Booster Energy: Check activation

2. **onModifyDamage** (before damage calc):
   - Life Orb: 1.3x multiplier
   - Choice Band/Specs: 1.5x multiplier
   - Expert Belt: 1.2x on super-effective

3. **onAfterDamage** (after damage dealt):
   - Berries: Check HP threshold
   - Weakness Policy: Check if hit was super-effective
   - Air Balloon: Pop if hit

4. **onAfterMoveSecondarySelf** (after move completes):
   - Life Orb: Apply recoil
   - Throat Spray: Boost SpA if sound move

5. **onDamagingHit** (when holder is hit):
   - Rocky Helmet: Damage attacker
   - Sticky Barb: Transfer to attacker

6. **onResidual** (end of turn):
   - Leftovers: Heal 1/16 HP
   - Black Sludge: Heal or damage
   - Sticky Barb: Damage holder

7. **onSetAbility** (ability change attempt):
   - Ability Shield: Block ability change

8. **onSetStatus** (status application):
   - Mental Herb: Cure status immediately
   - Covert Cloak: Block secondary effects

## Pokemon Showdown Protocol Integration

When items activate in Pokemon Showdown, specific protocol messages are sent:

### Item Activation Messages
```
|-item|POKEMON|ITEM
|-enditem|POKEMON|ITEM
|-activate|POKEMON|item: ITEM
```

### Example: Leftovers
```
|turn|5
|-heal|p1a: Garchomp|285/358|[from] item: Leftovers
```

### Example: Life Orb
```
|-damage|p1a: Garchomp|200/358|[from] item: Life Orb
```

### Example: Focus Sash
```
|-activate|p1a: Shedinja|item: Focus Sash
|-enditem|p1a: Shedinja|Focus Sash
```

**Parser Updates Needed:**
- Recognize `[from] item: ITEM_NAME` in damage/heal events
- Parse `-item`, `-enditem`, `-activate` messages
- Create corresponding `ItemActivateEvent`, `ItemConsumedEvent`

## Testing Strategy

### Unit Tests
Each item should have dedicated tests:
- Item activation conditions
- Stat modifications applied correctly
- Item consumption tracked
- Edge cases (e.g., Focus Sash at 1 HP doesn't activate)

### Integration Tests
Test items in battle scenarios:
- Choice lock + switch = unlock
- Life Orb KO + recoil = simultaneous faint
- Weakness Policy + Assault Vest = stat boost but no status moves
- Leftovers + Poison = net healing calculation

### Battle Scenario Tests
Real battle situations:
- Choice Scarf outspeeds base Speed
- Focus Sash saves from OHKO
- Heavy-Duty Boots ignores Stealth Rock
- Booster Energy activates Paradox ability

## Known Limitations & Future Work

### Limitations in Initial Implementation
1. **No item transfer**: Trick, Switcheroo, Knock Off effects deferred
2. **No item restoration**: Recycle, Harvest deferred
3. **No fling mechanics**: Fling, Bestow deferred
4. **Limited berry types**: Focus on HP/status berries only
5. **No gen-specific items**: Z-Crystals, Mega Stones low priority

### Future Extensions
1. **Item transfer mechanics**: Trick, Switcheroo, Knock Off, Thief
2. **Berry mechanics**: All 67 berry types
3. **Z-Moves**: Z-Crystal item activation
4. **Mega Evolution**: Mega Stone item checks
5. **Advanced items**: Eject Button, Red Card, Eject Pack
6. **Item clause**: Track and enforce species clauses

## Dependencies

### Prerequisite Milestones
Before implementing items, ensure these are complete:
- ✅ Milestone 1.1-1.3: State model and event parsing
- ✅ Milestone 1.4: State transitions for HP, status, boosts
- Milestone 1.5: Battle environment (needed for item activation context)

### Concurrent Work
These can be developed in parallel:
- Ability effects (some items interact with abilities)
- Move effects (some items modify move behavior)
- Status conditions (items can cure or prevent)

## Success Criteria

**Milestone 2 is complete when:**
1. ✅ Item descriptions added to items.json
2. ✅ Python Item model includes description field
3. Item effect system implemented in state transitions
4. All Tier 1 items (8 items) fully functional
5. All Tier 2 items (7 items) fully functional
6. Battle with items works correctly against RandomAgent
7. Tests pass for all implemented items
8. Documentation updated

**Acceptance Test:**
- Start battle with teams using items (Leftovers, Choice Scarf, Life Orb)
- Items activate correctly during battle
- Item effects modify stats, damage, healing as expected
- Choice lock prevents move switching
- Battle concludes correctly with items in play

---

## Appendix: Full Item List by Category

### Damage Modifiers (25 items)
Life Orb, Choice Band, Choice Specs, Expert Belt, Muscle Band, Wise Glasses, Type Plates (17), Charcoal, Mystic Water, Spell Tag, etc.

### Speed Modifiers (5 items)
Choice Scarf, Iron Ball, Macho Brace, Power items (6), Lagging Tail, Full Incense

### Healing Items (15 items)
Leftovers, Black Sludge, Shell Bell, Sitrus Berry, Oran Berry, Aguav Berry, Figy Berry, Iapapa Berry, Mago Berry, Wiki Berry

### Berries (67 items)
Status berries, stat-boost berries, type-resist berries, pinch berries, etc.

### Protective Items (12 items)
Focus Sash, Focus Band, Air Balloon, Safety Goggles, Protective Pads, Covert Cloak, Clear Amulet

### Stat Boosters (20 items)
Eviolite, Assault Vest, Weakness Policy, Throat Spray, Room Service, Mirror Herb, Loaded Dice

### Field Extenders (8 items)
Heat Rock, Damp Rock, Smooth Rock, Icy Rock, Terrain Extenders (4)

### Mega Stones (46 items)
All Mega Stones for Mega Evolution (Gen 6-7)

### Z-Crystals (29 items)
Type-specific and Pokemon-specific Z-Crystals (Gen 7)

### Miscellaneous (300+ items)
Fossils, evolution items, form-change items, event items, etc.

**Total**: 537 items
**Target for implementation**: 30-40 most common items in Gen 9 OU
