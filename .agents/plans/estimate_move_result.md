# estimate_move_result Enhancement Plan

## Goal
Add missing damage calculation effects to `estimate_move_result` to match Pokemon Showdown's damage calculator.

## Implementation Order

### 1. Stat Override Moves (Body Press, Psyshock)
**Status:** ✅ COMPLETED
**Complexity:** Easy
**Value:** High (commonly used moves)

- ✅ `override_offensive_stat` and `override_defensive_stat` added to Move dataclass
- ✅ Stat selection in `estimate_move_result()` checks overrides (lines 445-485)
- ✅ Parameterized test `test_stat_override_moves` with 2 test cases (body_press, psyshock)

### 2. Terrain Effects
**Status:** ✅ COMPLETED
**Complexity:** Moderate
**Value:** High (common in competitive)

- ✅ Terrain damage modifiers implemented in `_apply_modifiers()` (lines 581-590)
- ✅ `_is_grounded()` helper checks for Flying-type and Levitate ability (lines 542-552)
- ✅ Multipliers applied:
  - Electric/Grassy/Psychic Terrain + matching type: 1.3x
  - Misty Terrain + Dragon moves: 0.5x
- ✅ Parameterized test `test_terrain_effects` with 4 test cases (electric, grassy, psychic, misty)

### 3. Screen Effects (Reflect/Light Screen)
**Status:** ✅ COMPLETED
**Complexity:** Easy
**Value:** Medium (common defensive strategy)

- ✅ Added `defender_side_conditions: Optional[List[SideCondition]]` parameter to `estimate_move_result()`
- ✅ Implemented screen logic in `_apply_modifiers()`:
  - Aurora Veil: 0.5x for both physical and special
  - Reflect: 0.5x for physical only
  - Light Screen: 0.5x for special only
- ✅ Parameterized test `test_screen_effects` with 4 test cases (reflect_physical, light_screen_special, aurora_veil_physical, aurora_veil_special)

### 4. Critical Hit Stat Boost Handling
**Status:** ✅ COMPLETED
**Complexity:** Moderate
**Value:** Medium (improves accuracy)

- ✅ Added `crit_min_damage` and `crit_max_damage` fields to MoveResult dataclass
- ✅ `_get_crit_stat_multiplier()` helper method ignores bad boosts:
  - For attackers: `max(boost, 0)` to ignore negative attack boosts
  - For defenders: `min(boost, 0)` to ignore positive defense boosts
- ✅ `estimate_move_result()` calculates both regular and crit damage ranges
- ✅ Parameterized test `test_critical_hit_stat_boosts` with 4 test cases:
  - Negative attack boost ignored on crit
  - Positive defense boost ignored on crit
  - Positive attack boost kept on crit
  - Negative defense boost kept on crit

### 5. Common Abilities
**Status:** Planned
**Complexity:** High
**Value:** High (affects many calculations)

Priority abilities to implement:
- Adaptability (2x STAB instead of 1.5x)
- Technician (1.5x for moves ≤60 BP)
- Levitate (Ground immunity + affects terrain grounding)
- Huge Power/Pure Power (doubles Attack)
- Thick Fat (halves Fire/Ice damage)

### 6. Common Items
**Status:** Planned
**Complexity:** Moderate
**Value:** High (very common in competitive)

Priority items to implement:
- Choice Band/Specs (1.5x Attack/Sp.Atk)
- Life Orb (1.3x damage)
- Expert Belt (1.2x on super-effective)
- Type-boosting items (1.2x for specific type)

### 7. Weather Edge Cases
**Status:** Planned
**Complexity:** Low
**Value:** Low (less common)

- Sandstorm: 1.5x Rock-type Sp.Def
- Snow: 1.5x Ice-type Defense
- Harsh Sun/Heavy Rain: 2.0x boost, complete immunity reduction

## Testing Strategy
- TDD approach: write tests first for each feature
- Use parameterized tests with expected MoveResult objects
- Test edge cases (e.g., immunity, 0 damage, max damage)
- Update test expectations to use MoveResult objects (already done by user)

## Review Phase
- Run code-review agent after implementation
- Address critical issues
- Remove implementation-guiding comments
- Ensure no emojis in code
- Run linters (ruff, pyrefly)

## Follow-up TODOs
- Secondary effects (status infliction chances from move data)
- Multi-hit moves
- Variable base power moves
- Recoil/drain effects
- More complex abilities and items
