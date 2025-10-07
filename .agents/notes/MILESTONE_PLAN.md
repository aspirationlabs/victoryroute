# Milestone Plan: Human vs. Random Agent

## Overview

This document breaks down the first major milestone from the Development Workflow into actionable sub-milestones. The goal is to have a locally hosted Pokémon Showdown server where a human can play against a basic agent that makes randomized moves.

**First Milestone from PROJECT.md:**
> 1. **Data Sync**: Run scripts to pull latest game data from smogon/pokemon-showdown and convert to JSON
> 2. **Build Simulator**: Implement core battle mechanics with comprehensive tests (foo.py + foo_test.py pattern)
>    - By this step, connect to a locally hosted Showdown server for a human to play against a basic agent with randomized actions.

## Sub-Milestones

### Milestone 1.1: Game Data Foundation

**Goal**: Static game data available in JSON and loadable in Python

**Deliverables:**

**Scripts:**
- `python/scripts/sync_game_data.py`
  - Clone or fetch from smogon/pokemon-showdown repo
  - Extract data files (pokedex.ts, moves.ts, abilities.ts, items.ts, natures.ts, typechart.ts)
  - Handle versioning/updates

- `python/scripts/convert_to_json.py`
  - Parse TypeScript data files
  - Convert to clean JSON format
  - Handle special cases (conditional data, references)

**JSON Data Files:**
- `data/game/pokemon.json` - All Pokémon species (stats, types, abilities, movepool)
- `data/game/moves.json` - All moves (power, accuracy, type, category, effects, priority)
- `data/game/abilities.json` - All abilities (effects, descriptions)
- `data/game/items.json` - All held items (effects, descriptions)
- `data/game/natures.json` - All natures (stat modifiers)
- `data/game/type_chart.json` - Type effectiveness matrix (18x18)

**Python Data Models:**
- `python/game/data/pokemon.py` - `Pokemon` dataclass, load from JSON
- `python/game/data/move.py` - `Move` dataclass, load from JSON
- `python/game/data/ability.py` - `Ability` dataclass, load from JSON
- `python/game/data/item.py` - `Item` dataclass, load from JSON
- `python/game/data/nature.py` - `Nature` dataclass, load from JSON
- `python/game/data/type_chart.py` - Type effectiveness lookup
- `python/game/data/game_data.py` - Central registry/loader
  - `get_pokemon(name: str) -> Pokemon`
  - `get_move(name: str) -> Move`
  - `get_ability(name: str) -> Ability`
  - Etc.

**Tests:**
- Load all JSON files without errors
- Query specific Pokémon, moves, abilities, items
- Verify type effectiveness calculations
- Validate data integrity (e.g., move references valid types)

**Validation Criteria:**
- Can import and query game data: "What's Pikachu's base speed?" → 90
- Type chart lookup works: "Fire vs. Grass" → 2.0x
- Data loading is type-safe (Pyrefly passes)

---

### Milestone 1.2: Protocol & Events ✅ **COMPLETE**

**Goal**: Parse Pokémon Showdown messages into typed events

**Deliverables:**

**Event Type System:** ✅
- `python/game/events/battle_event.py` (1,670 lines, 55+ event types)
  - `BattleEvent` base class (abstract)
  - **Battle lifecycle**: `BattleStartEvent`, `TurnEvent`, `BattleEndEvent`, `UpkeepEvent`
  - **Setup**: `PlayerEvent`, `TeamSizeEvent`, `GenEvent`, `TierEvent`, `GameTypeEvent`
  - **Team preview**: `PokeEvent`, `ClearPokeEvent`, `TeamPreviewEvent`
  - **Pokémon actions**: `MoveEvent`, `SwitchEvent`, `DragEvent`, `FaintEvent`
  - **State changes**: `DamageEvent`, `HealEvent`, `StatusEvent`, `CureStatusEvent`
  - **Move outcomes**: `SuperEffectiveEvent`, `ResistedEvent`, `ImmuneEvent`, `CritEvent`, `MissEvent`, `FailEvent`, `HitCountEvent`
  - **HP manipulation**: `SetHpEvent`
  - **Pokémon changes**: `ReplaceEvent`, `DetailsChangeEvent`
  - **Stat mods**: `BoostEvent`, `UnboostEvent`, `SetBoostEvent`, `ClearBoostEvent`, `ClearAllBoostEvent`, `ClearNegativeBoostEvent`
  - **Volatile conditions**: `StartVolatileEvent`, `EndVolatileEvent`, `SingleTurnEvent`, `SingleMoveEvent`
  - **Field effects**: `WeatherEvent`, `FieldStartEvent`, `FieldEndEvent`
  - **Side conditions**: `SideStartEvent`, `SideEndEvent`
  - **Abilities & items**: `AbilityEvent`, `EndAbilityEvent`, `ItemEvent`, `EndItemEvent`
  - **Form changes**: `TerastallizeEvent`, `FormeChangeEvent`, `TransformEvent`
  - **Special mechanics**: `ActivateEvent`, `PrepareEvent`, `CantEvent`
  - **Decision points**: `RequestEvent` (live battles only, validates agent actions)
  - **Fallback**: `UnknownEvent` (logs unrecognized message types)

**Protocol Parsing:** ✅
- `python/game/protocol/message_parser.py`
  - `parse(raw_message: str) -> BattleEvent` - Main entry point with MESSAGE_TYPE_MAP
  - Each event type has `parse_raw_message()` classmethod for self-parsing
  - Handles all protocol message types from real battle logs
  - Gracefully handles unknown message types with logging

**Event Stream:** ✅
- `python/game/protocol/battle_stream.py`
  - Async iterator for batching events between decision points
  - **Live mode**: Batches until `|request|` (agent needs to act)
  - **Replay mode**: Batches until next `|turn|` (for replay analysis)
  - Filters by battle ID for multi-battle support
  - Handles multiline messages and empty messages

**WebSocket Client:** ✅
- `python/game/protocol/showdown_client.py`
  - `async connect(server_url: str, username: str, password: str)` - WebSocket + auth
  - Authentication flow complete:
    1. Receive `|challstr|CHALLENGE_STRING`
    2. POST to action.php with credentials
    3. Extract assertion token from JSON response
    4. Send `/trn USERNAME,0,ASSERTION`
  - `async send_message(message: str)` - Send commands to server
  - `async receive_message() -> str` - Get next raw message
  - `async disconnect()` - Clean shutdown
  - Connection state tracking via `is_connected` property

**Tests:** ✅
- **106 message parser tests** covering all event types with real log samples
- **5 battle stream tests** for live/replay modes, batching, edge cases
- **Total: 200 tests passing** (89 game data + 106 protocol + 5 stream)
- All tests use real protocol messages from 1000+ battles
- Type checking passes (Pyrefly 0 errors)
- Linting passes (Ruff)

**Validation Criteria:** ✅
- ✅ Feed raw protocol message → get typed BattleEvent with correct fields
- ✅ Can connect to Showdown server (tested in `experimental/huangr/connect_server.py`)
- ✅ Authentication flow completes successfully
- ✅ Event batching works for both live and replay modes
- ✅ RequestEvent parses JSON payload for action validation (live only)

**Key Implementation Notes:**
- All events are **immutable frozen dataclasses** for thread safety
- Event types discovered from **real battle logs** (not just protocol docs)
- `|request|` only appears in live battles (not in replays/spectator logs)
- Replay analysis uses `|turn|` as decision point marker
- RequestEvent contains JSON payload with available moves/switches for validation

---

### Milestone 1.3: Battle State Model

**Goal**: Immutable state representation for battle

**Deliverables:**

**Core State Classes (all frozen dataclasses):**

- `python/game/schema/pokemon_state.py` - `PokemonState`
  - Species, level, gender, shiny
  - Current/max HP, status condition
  - Stat boosts (dict: stat → stage)
  - Active moves with PP
  - Item, ability
  - Volatile conditions, active effects
  - Mega/Dynamax/Tera state

- `python/game/schema/team_state.py` - `TeamState`
  - List of 6 `PokemonState` objects
  - Active Pokémon indices
  - Side conditions (screens, hazards, etc.) with counters
  - Fainted count

- `python/game/schema/field_state.py` - `FieldState`
  - Weather (type, turns remaining)
  - Terrain (type, turns remaining)
  - Global effects (Trick Room, Gravity, etc.)
  - Turn number

- `python/game/schema/battle_state.py` - `BattleState`
  - Player's `TeamState`
  - Opponent's `TeamState`
  - `FieldState`
  - Available actions (moves, switches, mega/tera flags)
  - Force switch, trapped flags
  - Battle format (singles/doubles)
  - Ruleset reference

**Enums and Constants:**
- `python/game/schema/enums.py`
  - `Status` (burn, paralysis, poison, sleep, freeze, toxic)
  - `Weather` (sun, rain, sandstorm, snow, harsh_sun, heavy_rain)
  - `Terrain` (electric, grassy, psychic, misty)
  - `SideCondition` (reflect, light_screen, aurora_veil, stealth_rock, spikes, etc.)
  - `FieldEffect` (trick_room, magic_room, wonder_room, gravity)
  - `Stat` (hp, atk, def, spa, spd, spe, accuracy, evasion)

**Helper Methods:**
- `get_stat_stage_multiplier(stage: int) -> float` - Convert stage to multiplier
- `get_effective_stat(base_stat: int, stage: int, modifiers: List) -> int`
- Validation: stat boosts clamped to ±6, HP ≥ 0, etc.

**Tests:**
- Construct realistic battle states manually
- Verify frozen/immutable (attempting to modify raises error)
- Test helper methods (stat calculations, etc.)
- Validate constraints (HP in range, stages in ±6, etc.)

**Validation Criteria:**
- Can construct complete battle state for testing
- All fields accessible with correct types
- Immutability enforced (Pyrefly confirms frozen dataclasses)

---

### Milestone 1.4: State Transitions (Core Mechanics)

**Goal**: Apply events to create new battle states with correct game logic

**Deliverables:**

**State Transition Engine:**
- `python/game/environment/state_transition.py` - `StateTransition` class
  - `apply(state: BattleState, event: BattleEvent) -> BattleState` - Main dispatcher
  - Individual handlers for each event type:
    - `_apply_move(state, event: MoveEvent) -> BattleState`
    - `_apply_damage(state, event: DamageEvent) -> BattleState`
    - `_apply_heal(state, event: HealEvent) -> BattleState`
    - `_apply_switch(state, event: SwitchEvent) -> BattleState`
    - `_apply_boost(state, event: BoostEvent) -> BattleState`
    - `_apply_status(state, event: StatusEvent) -> BattleState`
    - `_apply_weather(state, event: WeatherEvent) -> BattleState`
    - `_apply_terrain(state, event: TerrainEvent) -> BattleState`
    - `_apply_side_start(state, event: SideStartEvent) -> BattleState`
    - `_apply_faint(state, event: FaintEvent) -> BattleState`
    - `_apply_request(state, event: RequestEvent) -> BattleState`
    - And all others...

**Game Logic Implementation:**
- HP changes (damage, healing)
- Stat boost updates (with ±6 clamping)
- Status condition application/curing
- Switch mechanics (clear volatile conditions, keep stat boosts unless Baton Pass)
- Weather/terrain setup and expiration
- Side condition stacking (Spikes layers, etc.)
- Faint handling
- Request parsing (available moves/switches, flags)

**Simplified Implementations (for MVP):**
- Basic ability triggers (mark for later: complex abilities like Intimidate)
- Basic item effects (mark for later: complex items like Life Orb)
- Basic move effects (damage moves work, complex effects stubbed)
- No entry hazard damage yet (add after basic flow works)

**Tests:**
- Unit test each handler in isolation
- Given: initial state + event → Expected: new state with specific changes
- Test state immutability (original state unchanged)
- Battle scenario tests:
  - Pokemon takes damage → HP decreases
  - Pokemon faints → HP = 0, marked fainted
  - Stat boost → boosts updated correctly
  - Weather starts → field state updated
  - Switch → active Pokemon changes, volatiles cleared

**Validation Criteria:**
- Apply event sequence → verify final state matches expected
- Use known battle scenarios from replays
- All unit tests pass, Pyrefly type checking passes

**Note:** This is the most complex milestone. Focus on getting basic mechanics working correctly. Advanced interactions can be refined in later milestones.

---

### Milestone 1.5: Battle Environment

**Goal**: Orchestrate state updates via event stream from Showdown

**Deliverables:**

**Event Stream:**
- `python/game/protocol/battle_stream.py` - `BattleStream` class
  - Wraps `ShowdownClient` to provide event batching
  - `async __aiter__()` / `async __anext__()` - Async iterator protocol
  - Buffer events until `RequestEvent` (agent decision point)
  - Return `List[BattleEvent]` for each batch
  - Filter by battle ID (for multi-battle support)

**Battle Environment:**
- `python/game/environment/battle_environment.py` - `BattleEnvironment` class
  - Constructor: accepts `ShowdownClient`, `MessageParser`, optional history tracking
  - `async reset() -> BattleState` - Initialize battle, wait for start events
  - `async step(action: BattleAction) -> BattleState` - Main loop:
    1. Validate action against current state
    2. Send action to Showdown via client
    3. Collect events from stream until next `RequestEvent`
    4. Apply all events sequentially via `StateTransition.apply()`
    5. Update internal state reference
    6. Optionally append to history
    7. Return new `BattleState`
  - `get_state() -> BattleState` - Return current state (read-only)
  - `get_history() -> List[BattleState]` - Return state history if enabled
  - `is_battle_over() -> bool` - Check if battle ended

**Error Handling:**
- Invalid actions → raise `InvalidActionError`
- Connection errors → raise `ConnectionError` with context
- Unknown events → log warning, create `UnknownEvent`, continue
- State transition errors → raise with full context for debugging

**Tests:**
- Mock `ShowdownClient` to provide scripted events
- Test full turn cycle: action → events → new state
- Test event batching (multiple events before RequestEvent)
- Test history tracking (enabled/disabled)
- Integration test with realistic event sequences

**Validation Criteria:**
- Mock event stream → environment produces correct state transitions
- State history correctly captures each turn's state
- Handles battle start, turns, and battle end correctly

---

### Milestone 1.6: Agent Interface

**Goal**: High-level API for agents to query state and output actions

**Deliverables:**

**Battle Observer (Read-Only State Wrapper):**
- `python/game/interface/battle_observer.py` - `BattleObserver` class
  - Constructor: wraps `BattleState`, has access to `GameData`

  - **Active Pokémon queries:**
    - `get_active_pokemon() -> List[PokemonState]`
    - `get_opponent_active() -> List[PokemonState]`
    - `get_pokemon(player: Player, position: int) -> PokemonState`

  - **Team information:**
    - `get_team(player: Player) -> List[PokemonState]`
    - `get_fainted_count(player: Player) -> int`
    - `get_alive_pokemon(player: Player) -> List[PokemonState]`

  - **Available actions:**
    - `get_available_moves() -> List[Move]`
    - `get_available_switches() -> List[PokemonState]`
    - `can_mega_evolve() -> bool`
    - `can_terastallize() -> Optional[Type]`
    - `is_forced_switch() -> bool`
    - `is_trapped() -> bool`

  - **Field state:**
    - `get_weather() -> Optional[Weather]`
    - `get_terrain() -> Optional[Terrain]`
    - `get_field_effects() -> List[FieldEffect]`
    - `get_side_conditions(player: Player) -> Dict[SideCondition, int]`

  - **Basic calculations (MVP versions):**
    - `get_type_effectiveness(move: Move, target: PokemonState) -> float`
    - `estimate_damage(move: Move, attacker: PokemonState, target: PokemonState) -> tuple[int, int]` (min, max)
      - Simplified damage calc for MVP (full implementation later)

**Battle Action:**
- `python/game/interface/battle_action.py` - `BattleAction` dataclass
  - `action_type: ActionType` (MOVE, SWITCH)
  - `move_index: Optional[int]` (0-3)
  - `switch_index: Optional[int]` (0-5)
  - `target_index: Optional[int]` (for doubles)
  - `mega: bool`, `tera: bool` flags

  - `validate(state: BattleState) -> bool` - Check if action is legal
  - `to_showdown_command() -> str` - Convert to protocol command
    - MOVE → `/choose move {move_index + 1}`
    - SWITCH → `/choose switch {switch_index + 1}`
    - MEGA → `/choose move {move_index + 1} mega`
    - TERA → `/choose move {move_index + 1} tera`

**Agent Interface (Abstract Base):**
- `python/agents/schema/agent_interface.py` - `Agent` abstract class
  - `async choose_action(observer: BattleObserver) -> BattleAction`
  - All agents must implement this method

**Tests:**
- Test observer queries with various battle states
- Test type effectiveness calculations
- Test damage estimation (basic version)
- Test action validation (legal vs. illegal actions)
- Test action → Showdown command conversion

**Validation Criteria:**
- Query observer for battle info → get correct data
- Create valid and invalid actions → validation works
- Convert actions to Showdown commands → correct format

---

### Milestone 1.7: Basic Agents

**Goal**: Implement random agent and human CLI agent

**Deliverables:**

**Random Agent:**
- `python/agents/random/agent.py` - `RandomAgent`
  - Implements `Agent` interface
  - `async choose_action(observer: BattleObserver) -> BattleAction`:
    - Get available moves and switches from observer
    - Randomly pick move OR switch with some probability
    - If picked move: randomly select from available moves
    - If picked switch: randomly select from available switches
    - For doubles: randomly select target if needed
    - Return valid `BattleAction`
  - No complex logic, no strategy
  - Tests: verify always produces valid actions

**Human Agent (CLI):**
- `python/agents/human/agent.py` - `HumanAgent`
  - Implements `Agent` interface
  - `async choose_action(observer: BattleObserver) -> BattleAction`:
    - Display current battle state nicely:
      - Your active Pokemon (HP, status, boosts)
      - Opponent's active Pokemon (HP, status, boosts)
      - Weather, terrain, field effects
      - Side conditions
    - Display available moves:
      ```
      Moves:
      1. Thunderbolt (Electric, 90 BP, 15/15 PP)
      2. Iron Tail (Steel, 100 BP, 12/15 PP)
      3. Quick Attack (Normal, 40 BP, 30/30 PP)
      4. Thunder Wave (Electric, Status, 20/20 PP)
      ```
    - Display available switches:
      ```
      Switches:
      5. Charizard (HP: 78/100, Burned)
      6. Blastoise (HP: 120/120)
      ```
    - Prompt user for input: "Choose action (1-6): "
    - Parse input:
      - 1-4 → move selection
      - 5-6 → switch selection
      - Handle invalid input (re-prompt)
    - Return `BattleAction`
  - Tests: mock input/output, verify parsing works

**Shared Utilities:**
- `python/agents/utils/display.py` - Display helpers
  - Format Pokemon for display
  - Format move for display
  - Format battle state summary

**Tests:**
- RandomAgent always produces valid actions (run 1000 times with various states)
- HumanAgent parsing (mock user input → verify correct action)
- Display functions produce readable output

**Validation Criteria:**
- RandomAgent produces diverse valid actions
- HumanAgent displays state clearly and accepts user input
- Both agents implement the interface correctly

---

### Milestone 1.8: End-to-End Integration

**Goal**: Human plays vs. Random agent on local Showdown server

**Deliverables:**

**Main Battle Script:**
- `python/scripts/run_battle.py` - Entry point
  - Parse command-line arguments:
    - `--server-url` (default: ws://localhost:8000)
    - `--username` (default: "Player")
    - `--password` (optional)
    - `--format` (default: gen9ou)
    - `--team-file` (path to team file)
    - `--opponent` (random, human, or ladder)
  - Initialize `GameData` (load JSON)
  - Create `ShowdownClient`
  - Create `BattleEnvironment`
  - Initialize agents (HumanAgent for player, RandomAgent for opponent if specified)
  - Main loop:
    1. Connect to Showdown server
    2. Start battle (challenge or ladder)
    3. `state = await env.reset()` - Wait for battle start
    4. While battle not over:
       - `observer = BattleObserver(state)`
       - `action = await agent.choose_action(observer)`
       - `state = await env.step(action)`
    5. Display battle result
    6. Disconnect

**Team Files:**
- `data/teams/sample_team.txt` - Example team in Showdown format
  - Include a few sample teams for testing
  - Support Showdown's team import format

**Local Showdown Setup:**
- `docs/setup_local_showdown.md` - Instructions
  - Clone pokemon-showdown repo
  - Install dependencies
  - Start local server
  - Create test account
  - Connect to server

**Battle Flow Handling:**
- Team preview (if applicable)
- Initial switch-in
- Turn-by-turn loop
- Force switches (e.g., after faint)
- Battle end detection
- Disconnect on error or completion

**Logging & Debugging:**
- Log all events received
- Log all actions sent
- Log state transitions (optional, verbose mode)
- Save battle log to file for debugging

**Integration Tests:**
- Full battle with mocked agents (scripted actions)
- Verify battle completes successfully
- Verify final state matches expected result
- Test error scenarios (disconnect, invalid action, etc.)

**Validation Criteria:**
- Successfully complete a battle:
  - Human controls one side via CLI
  - Random agent controls opponent
  - All events parsed correctly
  - State updates correctly
  - Battle reaches conclusion (one side's team faints)
- Battle log captures all events and actions
- Can replay the battle from logs

---

## Dependency Tree

```
1.1 Game Data Foundation
    ↓
    ├─→ 1.2 Protocol & Events
    │   ↓
    └─→ 1.3 Battle State Model
        ↓
        └─→ 1.4 State Transitions ←─────┐
            ↓                            │
            1.5 Battle Environment       │
            ↓                            │
            1.6 Agent Interface ─────────┘
            ↓
            1.7 Basic Agents
            ↓
            1.8 End-to-End Integration
```

**Parallelization Opportunities:**
- 1.2 (Protocol & Events) and 1.3 (Battle State Model) can be developed in parallel
  - Events don't depend on state model structure
  - State model doesn't depend on event parsing
  - Both feed into 1.4
- 1.6 (Agent Interface) can start before 1.5 (Environment) is complete
  - Mock the environment for testing
  - Develop BattleObserver and BattleAction independently

**Critical Path:**
1.1 → 1.4 → 1.5 → 1.8

## What's NOT Included (Deferred to Later Milestones)

To keep the first milestone achievable, the following are explicitly **out of scope**:

### Advanced Game Mechanics
- **Complex abilities**: Intimidate, Protosynthesis, Speed Boost, etc.
  - Stub: acknowledge ability exists, don't apply effects
  - Implement after basic flow works
- **Complex items**: Life Orb, Choice items, berries, etc.
  - Stub: items recognized but effects not applied
- **Complex move effects**: Multi-turn moves, partial trapping, etc.
  - Focus on basic damage moves and simple status moves
- **Entry hazard damage**: Stealth Rock damage on switch
  - Hazards tracked in state, but damage calculation deferred
- **Speed ties and RNG**: Simplified speed order for MVP
  - Implement deterministic speed (higher stat always faster)
  - Add proper RNG and speed ties later

### Advanced Features
- **Full damage calculator**: Use simplified damage formula
  - Approximate: (move power × attack / defense) × type effectiveness
  - Ignore: weather, abilities, items, screens, crits for MVP
- **Team building**: Use hardcoded/file-based teams
  - No team validation against rulesets yet
  - Just load teams and play
- **Replay parsing**: Not needed for live battles
  - Will be needed for training data, but later
- **Advanced evaluation**: Just get battles working
  - Evaluation metrics come in future milestones
- **Multi-battle support**: Single battle at a time
  - Battle ID filtering exists, but not tested
- **LLM agents**: Future milestone
  - First milestone is just random + human

### Polish & Optimization
- **Performance optimization**: Correctness first
  - Immutable state copies might be slow, optimize later
- **Error recovery**: Basic error handling only
  - Advanced reconnection, state recovery, etc. can come later
- **UI/UX**: Minimal CLI is fine
  - Better display formatting, color, etc. is nice-to-have
- **Documentation**: Code comments are enough
  - Full API docs, tutorials, etc. come later

## Success Criteria for Milestone 1

The first milestone is **complete** when:

1. ✅ Game data is synced and loadable in Python
2. ✅ Showdown protocol messages are parsed into typed events
3. ✅ Battle state can be constructed and is immutable
4. ✅ Events are applied to create new states with basic game logic
5. ✅ Environment orchestrates event stream and state updates
6. ✅ Agents can query state and output actions
7. ✅ Random agent and human CLI agent are implemented
8. ✅ **A human can play a full battle against a random agent on a local Showdown server**

**Acceptance Test:**
- Start local Showdown server
- Run `python/scripts/run_battle.py --opponent random`
- Human picks moves via CLI
- Random agent picks random moves
- Battle progresses correctly (state updates, HP changes, switches, faints)
- Battle concludes when one team is fully fainted
- Winner is declared correctly

## Next Milestones (After 1.8)

Once the first milestone is complete, future milestones might include:

**Milestone 2: Advanced Game Mechanics**
- Full damage calculator
- Ability effects
- Item effects
- Complex move effects
- Entry hazard damage
- Proper RNG and speed ties

**Milestone 3: Replay System**
- Parse Showdown replays
- Generate training datasets
- Replay validation against state transitions

**Milestone 4: LLM Agents**
- Implement LLM-based agent
- Tool integration for agents
- Chain-of-thought prompting
- Model comparison (GPT vs Claude vs Llama)

**Milestone 5: Evaluation Framework**
- Win rate evaluation
- Replay matching evaluation
- LLM judge evaluation
- Elo rating system

But those come **after** we have a working human vs. random agent battle!
