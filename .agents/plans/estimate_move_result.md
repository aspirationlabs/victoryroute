# estimate_move_result Enhancement Plan

## Goal
Add missing damage calculation effects to `estimate_move_result` to match Pokemon Showdown's damage calculator.

## Implementation Order

### 1. Stat Override Moves (Body Press, Psyshock)
**Status:** Not started
**Complexity:** Easy
**Value:** High (commonly used moves)

- Add `override_offensive_stat` and `override_defensive_stat` to Move dataclass
- Update sync script to include these fields
- Modify stat selection in `estimate_move_result()` to check overrides first
- Test with Body Press (uses Defense for attack) and Psyshock (uses Defense for defense against Special moves)

### 2. Terrain Effects
**Status:** Not started
**Complexity:** Moderate
**Value:** High (common in competitive)

- Add terrain damage modifier (1.3x) in `_apply_modifiers()`
- Check if attacker is "grounded" (not Flying-type, no Levitate ability)
- Apply 1.3x multiplier for:
  - Electric Terrain + Electric moves
  - Grassy Terrain + Grass moves
  - Psychic Terrain + Psychic moves
- Test with each terrain type

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
**Status:** Not started
**Complexity:** Moderate
**Value:** Medium (improves accuracy)

- When is_crit=True, ignore negative attack boosts
- When is_crit=True, ignore positive defense boosts
- Calculate both crit and non-crit damage ranges
- Update MoveResult to include crit damage range
- Test with boosted/dropped stats + crit

### 5. Common Abilities
**Status:** Deferred (Phase 2)
**Complexity:** High
**Value:** High (affects many calculations)

Priority abilities to implement:
- Adaptability (2x STAB instead of 1.5x)
- Technician (1.5x for moves ≤60 BP)
- Levitate (Ground immunity + affects terrain grounding)
- Huge Power/Pure Power (doubles Attack)
- Thick Fat (halves Fire/Ice damage)

### 6. Common Items
**Status:** Deferred (Phase 2)
**Complexity:** Moderate
**Value:** High (very common in competitive)

Priority items to implement:
- Choice Band/Specs (1.5x Attack/Sp.Atk)
- Life Orb (1.3x damage)
- Expert Belt (1.2x on super-effective)
- Type-boosting items (1.2x for specific type)

### 7. Weather Edge Cases
**Status:** Deferred (Phase 2)
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
