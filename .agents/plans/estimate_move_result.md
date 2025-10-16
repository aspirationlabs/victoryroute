# estimate_move_result Enhancement Plan

## Goal
Add missing damage calculation effects to `estimate_move_result` to match Pokemon Showdown's damage calculator.

## Completed Features

All phases 1-8 have been completed:
- ✅ Stat Override Moves (Body Press, Psyshock)
- ✅ Terrain Effects (Electric/Grassy/Psychic/Misty terrain)
- ✅ Screen Effects (Reflect/Light Screen/Aurora Veil)
- ✅ Critical Hit Stat Boost Handling
- ✅ Common Abilities (Adaptability, Technician, Huge Power, etc.)
- ✅ Common Items (Choice Band/Specs, Life Orb, type boosters, etc.)
- ✅ Weather Edge Cases (Sandstorm Rock SpD, Snow Ice Def)
- ✅ Multi-Hit Moves (Double Kick, Bullet Seed, Rock Blast)

## Implementation Order

### Phase 1: Multi-Hit Moves
**Status:** ✅ Completed
**Complexity:** Easy
**Value:** High (common in competitive)

**Research findings from Pokemon Showdown:**
- Moves can have fixed hits (e.g., `multihit: 2` for Double Kick, Twineedle, Bonemerang)
- Or variable hits (e.g., `multihit: [2, 5]` for Fury Attack, Bullet Seed, Rock Blast)
- Distribution for [2,5]: 35% 2 hits, 35% 3 hits, 15% 4 hits, 15% 5 hits
- Loaded Dice item changes distribution to favor higher hit counts

**Implementation plan:**
- Add `multihit` field to Move dataclass (Union[int, Tuple[int, int]])
- Implement hit count logic in `estimate_move_result()`
- Calculate damage per hit and total damage ranges
- For variable hits, return average expected damage or damage ranges for each hit count
- Add `hit_count` field to MoveResult to indicate number of hits

**Test cases:**
- Double Kick: 2 fixed hits
- Fury Attack: 2-5 variable hits
- Bullet Seed: 2-5 variable hits with Technician ability

### Phase 2: Variable Base Power - HP-Based
**Status:** Planned
**Complexity:** Medium
**Value:** High (includes Water Spout, common in competitive)

**Research findings from Pokemon Showdown:**
- Water Spout/Eruption: `BP = 150 * current_hp / max_hp`
- Crush Grip/Wring Out: Complex formula based on target HP%
  - `BP = floor(floor((120 * (100 * floor(hp * 4096 / maxHP)) + 2048 - 1) / 4096) / 100) || 1`
- These use `basePowerCallback(pokemon, target, move)` function

**Implementation plan:**
- Add `base_power_callback_type` field to Move dataclass (enum: HP_BASED_ATTACKER, HP_BASED_DEFENDER)
- Implement HP-based base power calculation in `estimate_move_result()`
- Handle special cases: Eruption, Water Spout, Crush Grip, Wring Out

**Test cases:**
- Water Spout at 100% HP (150 BP), 50% HP (75 BP), 25% HP (37 BP)
- Eruption at different HP percentages
- Crush Grip against 100% HP target, 50% HP target, 1% HP target

### Phase 3: Variable Base Power - Stat-Based
**Status:** Planned
**Complexity:** Medium
**Value:** High (Electro Ball, Gyro Ball fairly common)

**Research findings from Pokemon Showdown:**
- **Electro Ball**: `ratio = floor(attacker_speed / target_speed)`, BP = [40, 60, 80, 120, 150][min(ratio, 4)]
- **Gyro Ball**: `BP = min(floor(25 * target_speed / attacker_speed) + 1, 150)`
- **Heavy Slam/Heat Crash**: Weight ratio based
  - ≥5×: 120 BP, ≥4×: 100 BP, ≥3×: 80 BP, ≥2×: 60 BP, else: 40 BP
- **Low Kick/Grass Knot**: Target weight based
  - ≥200kg: 120 BP, ≥100kg: 100 BP, ≥50kg: 80 BP, ≥25kg: 60 BP, ≥10kg: 40 BP, else: 20 BP

**Implementation plan:**
- Add `weight` field to Pokemon dataclass or species data
- Add `base_power_callback_type` enum values: SPEED_RATIO, INVERSE_SPEED_RATIO, WEIGHT_RATIO, TARGET_WEIGHT
- Implement stat comparison formulas in `estimate_move_result()`
- Need to calculate effective speeds (with paralysis, item, ability modifiers)

**Test cases:**
- Electro Ball: fast attacker (500 Spe) vs slow target (100 Spe) = 150 BP
- Electro Ball: slow attacker (100 Spe) vs fast target (500 Spe) = 40 BP
- Gyro Ball: slow attacker vs fast target
- Heavy Slam: heavy Pokemon vs light Pokemon
- Low Kick vs heavy Pokemon (Snorlax, Groudon)

### Phase 4: Variable Base Power - Boost-Based
**Status:** Planned
**Complexity:** Easy
**Value:** Medium (niche moves)

**Research findings from Pokemon Showdown:**
- **Stored Power/Power Trip**: `BP = 20 + 20 * pokemon.positiveBoosts()`
- `positiveBoosts()` sums all positive stat stage increases (Atk, Def, SpA, SpD, Spe)

**Implementation plan:**
- Add `base_power_callback_type` enum value: POSITIVE_BOOSTS
- Calculate sum of positive stat boosts from attacker's stat_boosts
- Apply formula: 20 + 20 × positive_boost_sum

**Test cases:**
- Stored Power with no boosts (20 BP)
- Stored Power with +2 Atk, +1 Spe (20 + 20×3 = 80 BP)
- Stored Power with +6 SpA, +6 SpD (20 + 20×12 = 260 BP)

### Phase 5: Recoil and Drain Effects
**Status:** Planned
**Complexity:** Easy
**Value:** Medium (affects HP management decisions)

**Research findings from Pokemon Showdown:**
- **Recoil moves**: `recoil: [numerator, denominator]`
  - Double-Edge, Brave Bird, Flare Blitz: `recoil: [33, 100]` (1/3 of damage dealt)
  - Take Down, Submission: `recoil: [1, 4]` (1/4 of damage dealt)
  - Head Smash: `recoil: [1, 2]` (1/2 of damage dealt)
- **Drain moves**: `drain: [numerator, denominator]`
  - Absorb, Mega Drain, Giga Drain: `drain: [1, 2]` (50% of damage dealt)
  - Draining Kiss, Parabolic Charge: `drain: [3, 4]` (75% of damage dealt)
- Calculated from actual damage dealt (after all modifiers)

**Implementation plan:**
- Add `recoil` field to Move dataclass (Optional[Tuple[int, int]])
- Add `drain` field to Move dataclass (Optional[Tuple[int, int]])
- Add `recoil_damage` field to MoveResult (damage dealt to attacker)
- Add `drain_heal` field to MoveResult (HP healed to attacker)
- Calculate recoil/drain based on max_damage dealt

**Test cases:**
- Double-Edge: verify recoil = 33% of damage
- Brave Bird: verify recoil = 33% of damage
- Giga Drain: verify drain = 50% of damage
- Head Smash with Rock Head ability (should have no recoil)

### Phase 6: Secondary Effects - Status Infliction
**Status:** Planned
**Complexity:** Medium
**Value:** Medium (affects strategic decisions)

**Research findings from Pokemon Showdown:**
- **Secondary effects** defined as:
  ```typescript
  secondary: {
    chance: 10,  // 10% chance
    status: 'par'  // inflict paralysis
  }
  ```
- Examples:
  - Thunderbolt: 10% paralysis
  - Ice Beam: 10% freeze
  - Flamethrower: 10% burn
  - Bolt Strike: 20% paralysis
- **Serene Grace ability**: Doubles secondary effect chances
- **Sheer Force ability**: Removes secondary effects but adds 30% damage boost
- **Shield Dust ability** (defender): Prevents secondary effects

**Implementation plan:**
- Add `secondary_effect` field to Move dataclass with `chance` and `status` subfields
- Add `status_infliction_chances` field to MoveResult (Dict[str, float])
- Calculate effective chance based on abilities (Serene Grace, Sheer Force, Shield Dust)
- Sheer Force: remove secondary, add 1.3× damage multiplier (already handled in items phase)

**Test cases:**
- Thunderbolt: 10% paralysis chance
- Thunderbolt with Serene Grace: 20% paralysis chance
- Thunderbolt with Sheer Force: 0% paralysis, increased damage
- Thunderbolt vs Shield Dust: 0% paralysis

### Phase 7: Secondary Effects - Stat Changes
**Status:** Planned
**Complexity:** Medium
**Value:** Low (less common, less impactful for damage estimation)

**Research findings from Pokemon Showdown:**
- **Stat-changing secondaries**:
  ```typescript
  secondary: {
    chance: 10,
    boosts: { spd: -1 }  // 10% chance to lower SpD by 1
  }
  ```
- Examples:
  - Acid: 10% chance -1 SpD (all adjacent foes)
  - Shadow Ball: 20% chance -1 SpD
  - Earth Power: 10% chance -1 SpD
  - Crunch: 20% chance -1 Def

**Implementation plan:**
- Extend `secondary_effect` field to support `boosts` (Dict[Stat, int])
- Add `stat_change_chances` field to MoveResult (Dict[str, Tuple[Stat, int, float]])
- Calculate effective chance with Serene Grace/Shield Dust

**Test cases:**
- Acid: 10% chance to lower SpD
- Shadow Ball: 20% chance to lower SpD
- Crunch with Serene Grace: 40% chance to lower Def

### Phase 8: More Complex Abilities
**Status:** Planned
**Complexity:** High
**Value:** Medium (some competitive relevance)

**Research findings from Pokemon Showdown:**
- **Flag-based abilities** require move flags:
  - Iron Fist: 1.2× for punch moves (flag: `punch`)
  - Strong Jaw: 1.5× for bite moves (flag: `bite`)
  - Mega Launcher: 1.5× for pulse/aura moves (flag: `pulse`)
  - Sharpness: 1.5× for slicing moves (flag: `slicing`)
- Requires extending Move dataclass with flags

**Implementation plan:**
- Add `flags` field to Move dataclass (Set[str])
- Implement flag-based ability damage modifiers in `_modify_attack_for_ability()`
- Add support for Iron Fist, Strong Jaw, Mega Launcher, Sharpness

**Test cases:**
- Mach Punch with Iron Fist (1.2× modifier)
- Crunch with Strong Jaw (1.5× modifier)
- Aura Sphere with Mega Launcher (1.5× modifier)

## Testing Strategy
- TDD approach: write tests first for each feature
- Use parameterized tests with expected MoveResult objects
- Test edge cases (e.g., immunity, 0 damage, max damage, ability interactions)
- Verify calculations match Pokemon Showdown damage calculator

## Notes
- Each phase builds on Move dataclass incrementally
- Priority is on high-value, commonly-used mechanics first
- Complex variable BP moves and secondary effects deferred to later phases
- Some features (like Loaded Dice for multi-hit) can be added in future iterations
