# Battle Environment Design

## Overview

This document describes the architecture for syncing battle state between Pokémon Showdown's WebSocket protocol and our local immutable battle state representation. The design prioritizes immutability, type safety, and clean separation between protocol handling, state management, and agent interaction.

## Core Immutable State Classes

Location: `python/game/schema/`

All state classes are frozen dataclasses with full type hints.

### `PokemonState`

Represents the complete state of a single Pokémon during battle.

**Persistent Attributes:**
- Species name
- Level
- Gender
- Shiny status
- Base stats (reference to game data)

**Current Battle State:**
- Current HP / Max HP
- Status condition (burn, paralysis, poison, sleep, freeze, none)
- Stat boosts (dict mapping stat name → stage -6 to +6)
- Active moves (list of 4 moves with PP)
- Held item
- Ability
- Tera type

**Volatile State:**
- Active effects (Protect counter, Substitute HP, type changes, etc.)
- Volatile conditions (confusion, flinch, taunt, etc.)
- Move preparation state (charging, recharging, two-turn moves)
- Mega evolved / Dynamaxed / Terastallized flags

### `TeamState`

Represents one player's team and their side of the field.

**Team Composition:**
- List of 6 `PokemonState` objects
- Active Pokémon indices (1 for singles, 2 for doubles)
- Fainted Pokémon count

**Side Conditions:**
- Screens (Reflect, Light Screen, Aurora Veil) with turns remaining
- Hazards (Stealth Rock, Spikes layers, Toxic Spikes layers, Sticky Web)
- Field effects (Tailwind, Safeguard, Mist, Lucky Chant, etc.)
- Pledge effects (Fire/Grass/Water Pledge areas)

**Side-Wide State:**
- Wish healing queue
- Future Sight / Doom Desire pending
- Court Change swap state

### `FieldState`

Represents global field conditions affecting both players.

**Environmental Conditions:**
- Weather (Sun, Rain, Sandstorm, Snow, none) with turns remaining
- Terrain (Electric, Grassy, Psychic, Misty, none) with turns remaining

**Global Effects:**
- Trick Room status and turns remaining
- Magic Room status and turns remaining
- Wonder Room status and turns remaining
- Gravity status and turns remaining
- Mud Sport / Water Sport status

**Battle Metadata:**
- Current turn number
- Battle format (singles, doubles, triples)

### `BattleState`

The complete immutable snapshot of an entire battle.

**Components:**
- Player's `TeamState`
- Opponent's `TeamState`
- `FieldState`

**Available Actions:**
- List of available moves (with move index, PP, disabled status)
- List of available switches (with Pokémon index, trapped status)
- Can Mega Evolve flag
- Can Terastallize flag (with available Tera type)
- Can Dynamax flag
- Force switch flag

**Battle Context:**
- Ruleset reference (which regulation is active)
- Battle ID (for tracking multiple simultaneous battles)
- Player role identifier (p1 vs p2)

## Event System

Location: `python/game/events/`

All Showdown protocol messages are parsed into typed event objects. Events are the atomic units of state change.

### `BattleEvent` (Base Class)

Abstract base class for all battle events.

**Attributes:**
- `event_type: str` - Discriminator for event type
- `raw_message: str` - Original protocol message for debugging
- `timestamp: Optional[datetime]` - When event occurred

### Concrete Event Types

Each corresponds to Showdown protocol message types from SIM-PROTOCOL.md.

**Battle Lifecycle:**
- `BattleStartEvent` - Battle initialization, player info
- `TeamSizeEvent` - Number of Pokémon per team
- `TurnEvent` - New turn started (turn number)
- `BattleEndEvent` - Battle concluded (winner)

**Pokémon Actions:**
- `MoveEvent` - Pokémon used a move (pokemon, move, target, miss flag, crit flag)
- `SwitchEvent` - Pokémon switched in (pokemon, position, species/level/gender details, HP)
- `DragEvent` - Forced switch (same structure as SwitchEvent)
- `FaintEvent` - Pokémon fainted (pokemon identifier)

**State Changes:**
- `DamageEvent` - HP reduced (pokemon, new HP, new status, damage source)
- `HealEvent` - HP restored (pokemon, new HP, heal source)
- `StatusEvent` - Status inflicted (pokemon, status type)
- `CureStatusEvent` - Status cured (pokemon, previous status)

**Stat Modifications:**
- `BoostEvent` - Stat stage increased (pokemon, stat name, amount)
- `UnboostEvent` - Stat stage decreased (pokemon, stat name, amount)
- `SetBoostEvent` - Stat set to specific stage (pokemon, stat name, stage)
- `ClearBoostEvent` - All stat changes reset (pokemon)

**Field Effects:**
- `WeatherEvent` - Weather started/changed (weather type, turns, upkeep flag)
- `WeatherEndEvent` - Weather ended (weather type)
- `TerrainEvent` - Terrain started/changed (terrain type, turns)
- `TerrainEndEvent` - Terrain ended (terrain type)
- `FieldStartEvent` - Global field effect started (Trick Room, Gravity, etc.)
- `FieldEndEvent` - Global field effect ended

**Side Effects:**
- `SideStartEvent` - Side condition started (player, condition, layers)
- `SideEndEvent` - Side condition ended (player, condition)

**Abilities & Items:**
- `AbilityEvent` - Ability revealed/activated (pokemon, ability, trigger reason)
- `EndAbilityEvent` - Ability suppressed/changed (pokemon, previous ability)
- `ItemEvent` - Item revealed/activated (pokemon, item, activation reason)
- `EndItemEvent` - Item consumed/removed (pokemon, previous item, removal reason)

**Special Events:**
- `RequestEvent` - Agent decision required (available actions payload)
  - This event triggers agent to make a decision
  - Contains all legal moves and switches
- `MegaEvent` - Pokémon mega evolved (pokemon, mega form)
- `TeraEvent` - Pokémon terastallized (pokemon, tera type)
- `DynamaxEvent` - Pokémon dynamaxed (pokemon)

## Protocol Layer

Location: `python/game/protocol/`

Handles all communication with Pokémon Showdown servers.

### `MessageParser`

Parses raw pipe-delimited Showdown messages into typed `BattleEvent` objects.

**Responsibilities:**
- Parse protocol messages following SIM-PROTOCOL.md specification
- Map Showdown Pokémon identifiers (`p1a: Pikachu`) to battle positions
- Handle message variations (optional tags, different formats)
- Extract relevant data into structured event objects
- Normalize species names, move names, ability names

**Key Methods:**
- `parse(raw_message: str) -> BattleEvent` - Main parsing entry point
- `parse_pokemon_ident(ident: str) -> PokemonIdentifier` - Extract player/position from identifier
- `parse_hp_status(hp_string: str) -> tuple[int, int, Status]` - Parse HP and status
- `parse_details(details: str) -> PokemonDetails` - Extract species/level/gender

**Error Handling:**
- Unknown message types → `UnknownEvent` (preserves raw message)
- Malformed messages → log warning, return `UnknownEvent`
- Missing optional fields → use None/default values

### `ShowdownClient`

Manages WebSocket connection to Pokémon Showdown server.

**Responsibilities:**
- Establish WebSocket connection (ws:// or wss://)
- Handle authentication flow (`|challstr|` → POST request → `/trn` command)
- Send battle actions to server (`/choose move 1`, `/choose switch 2`)
- Receive raw battle messages from server
- Emit messages to message queue for parsing
- Handle reconnection on disconnect

**Connection Flow:**
1. Connect to WebSocket endpoint
2. Receive `|challstr|CHALLENGE_STRING`
3. POST authentication to action.php with credentials
4. Extract assertion token from response
5. Send `/trn USERNAME,0,ASSERTION` to authenticate
6. Ready to send/receive battle messages

**Key Methods:**
- `async connect()` - Establish connection and authenticate
- `async send_action(action: BattleAction)` - Send agent decision to server
- `async receive_message() -> str` - Get next raw message from server
- `async disconnect()` - Clean shutdown
- `async reconnect()` - Attempt reconnection on failure

### `BattleStream`

Async iterator that provides `BattleEvent` objects to the environment.

**Responsibilities:**
- Consume raw messages from `ShowdownClient`
- Parse messages via `MessageParser`
- Buffer events between `RequestEvent` occurrences
- Provide async iteration over event batches
- Handle battle-specific message filtering (if multiple battles active)

**Usage Pattern:**
```python
# Conceptual - not actual implementation
async for event_batch in battle_stream:
    # event_batch contains all events until next RequestEvent
    # Apply events to get new state
    # When RequestEvent arrives, yield control to agent
```

**Key Methods:**
- `async __aiter__()` - Async iterator protocol
- `async __anext__() -> List[BattleEvent]` - Return events until next decision point
- `filter_battle(battle_id: str)` - Only emit events for specific battle

## State Transition Engine

Location: `python/game/environment/`

Transforms immutable battle states by applying events.

### `StateTransition`

Pure functions that apply events to create new battle states.

**Design Pattern:**
- All methods are static/pure functions
- Input: current `BattleState` + `BattleEvent`
- Output: new `BattleState` (original unchanged)
- No side effects, no I/O
- Fully deterministic

**Main Entry Point:**
- `apply(state: BattleState, event: BattleEvent) -> BattleState`
  - Pattern match on event type
  - Delegate to specific handler method
  - Return new frozen state

**Event Handlers (examples):**

`_apply_move(state, event: MoveEvent) -> BattleState`
- No state change (damage/effects come in separate events)
- May update "last move used" for move-dependent mechanics

`_apply_damage(state, event: DamageEvent) -> BattleState`
- Create new `PokemonState` with updated HP
- Update status if changed
- Create new `TeamState` with updated Pokémon
- Return new `BattleState`

`_apply_switch(state, event: SwitchEvent) -> BattleState`
- Update active Pokémon index
- Clear volatile conditions from switched-out Pokémon
- Reset stat boosts (unless Baton Pass used - tracked separately)
- Update field state if ability triggers (Drought, Intimidate, etc.)

`_apply_boost(state, event: BoostEvent) -> BattleState`
- Update stat boosts dictionary for target Pokémon
- Clamp to -6 to +6 range
- Create new `PokemonState` → `TeamState` → `BattleState`

`_apply_weather(state, event: WeatherEvent) -> BattleState`
- Update `FieldState` with new weather type and turn count
- Create new `BattleState` with updated field

`_apply_side_start(state, event: SideStartEvent) -> BattleState`
- Add side condition to appropriate `TeamState`
- Handle stacking (Spikes, Toxic Spikes)
- Set turn counters for timed effects

`_apply_faint(state, event: FaintEvent) -> BattleState`
- Mark Pokémon as fainted (HP = 0)
- Update fainted count
- Clear active slot (will be filled by switch)

**Request Event Handling:**

`_apply_request(state, event: RequestEvent) -> BattleState`
- Parse available actions from request payload
- Update `BattleState.available_moves`
- Update `BattleState.available_switches`
- Set flags (can_mega, can_tera, force_switch, trapped)

### `BattleEnvironment`

Main orchestrator that manages battle lifecycle and state updates.

**Responsibilities:**
- Maintain current `BattleState` (immutable reference)
- Own `BattleStream` for receiving events
- Apply events via `StateTransition`
- Send actions to `ShowdownClient`
- Provide state to agents and tools
- Optional: maintain state history for replay/debugging

**Key Methods:**

`async step(action: BattleAction) -> BattleState`
1. Validate action against current state
2. Send action to Showdown via `ShowdownClient`
3. Collect events from `BattleStream` until next `RequestEvent`
4. Apply all events sequentially via `StateTransition.apply()`
5. Update internal state reference
6. Append to history (optional)
7. Return new `BattleState`

`get_state() -> BattleState`
- Return current immutable state
- Used by agents and tools for read-only access

`get_history() -> List[BattleState]`
- Return all historical states (if tracking enabled)
- Useful for replay generation, debugging, visualization

`reset() -> BattleState`
- Wait for battle start events
- Initialize first `BattleState`
- Return initial state

**State History Management:**
- Optional feature controlled by constructor parameter
- If enabled, append each new state to list
- Trade-off: memory vs. debugging/replay capability
- Can be disabled for production/training to save memory

## Agent Interface Layer

Location: `python/game/interface/`

Provides high-level API for agents to interact with battle state.

### `BattleObserver`

Read-only view of `BattleState` with convenience methods for agents.

**Purpose:**
- Hide low-level state structure from agents
- Provide battle-specific queries and calculations
- Power agent tools (Pokédex lookup, damage calc, etc.)
- Prevent agents from accidentally mutating state

**Initialization:**
- Wraps a `BattleState` instance
- Also has access to game data (Pokédex, moves, items, etc.)

**Key Query Methods:**

**Active Pokémon:**
- `get_active_pokemon() -> List[PokemonState]` - Our active Pokémon
- `get_opponent_active() -> List[PokemonState]` - Opponent's active
- `get_pokemon(player: Player, position: int) -> PokemonState` - Specific Pokémon

**Team Information:**
- `get_team(player: Player) -> List[PokemonState]` - All 6 Pokémon
- `get_fainted_count(player: Player) -> int`
- `get_alive_pokemon(player: Player) -> List[PokemonState]`

**Available Actions:**
- `get_available_moves() -> List[Move]` - Legal moves for current Pokémon
- `get_available_switches() -> List[PokemonState]` - Legal switches
- `can_mega_evolve() -> bool`
- `can_terastallize() -> Optional[Type]` - Returns Tera type if available
- `is_forced_switch() -> bool`
- `is_trapped() -> bool`

**Field State:**
- `get_weather() -> Optional[Weather]` - Current weather
- `get_terrain() -> Optional[Terrain]` - Current terrain
- `get_field_effects() -> List[FieldEffect]` - Trick Room, Gravity, etc.
- `get_side_conditions(player: Player) -> Dict[SideCondition, int]` - Screens, hazards, etc.

**Calculations & Predictions:**
- `estimate_damage(move: Move, attacker: Pokemon, target: Pokemon) -> DamageRange`
  - Uses damage calculator
  - Returns (min_damage, max_damage, rolls)
- `get_type_effectiveness(move: Move, target: Pokemon) -> float`
  - Considers move type, target type(s), abilities
  - Returns multiplier (0, 0.25, 0.5, 1, 2, 4)
- `get_speed_order(pokemon1: Pokemon, pokemon2: Pokemon) -> int`
  - Compare effective speeds accounting for all modifiers
  - Returns -1/0/1 for slower/tied/faster
- `predict_ko(move: Move, attacker: Pokemon, target: Pokemon) -> bool`
  - Simple prediction if move will KO target

**Tool Integration:**
- Methods directly power agent tools
- Tools call `BattleObserver` methods to answer queries
- Agent receives tool results as context for decision-making

### `BattleAction`

Represents an agent's decision output.

**Structure (dataclass):**
- `action_type: ActionType` - Enum: MOVE, SWITCH, MEGA, TERA, DYNAMAX
- `move_index: Optional[int]` - Which move slot (0-3)
- `switch_index: Optional[int]` - Which Pokémon to switch to (0-5)
- `target_index: Optional[int]` - Target position in doubles (0-3)
- `mega: bool` - Mega evolve with this action
- `tera: bool` - Terastallize with this action
- `z_move: bool` - Use Z-Move variant

**Validation:**
- Action must be valid for current state
- Validated against `BattleState.available_moves/switches`
- Environment raises error for invalid actions

**Conversion to Protocol:**
- `to_showdown_command() -> str`
  - MOVE → `/choose move {move_index + 1} {target_index}`
  - SWITCH → `/choose switch {switch_index + 1}`
  - Mega → `/choose move {move_index + 1} mega`
  - Tera → `/choose move {move_index + 1} tera`

## Integration Flow

```
┌─────────────────────────┐
│  Pokémon Showdown       │
│  WebSocket Server       │
└────────────┬────────────┘
             │ Raw protocol messages (pipe-delimited)
             ↓
┌─────────────────────────┐
│  ShowdownClient         │
│  - WebSocket handling   │
│  - Authentication       │
│  - Send actions         │
│  - Receive messages     │
└────────────┬────────────┘
             │ Raw message strings
             ↓
┌─────────────────────────┐
│  MessageParser          │
│  - Parse protocol       │
│  - Extract data         │
│  - Create typed events  │
└────────────┬────────────┘
             │ BattleEvent objects
             ↓
┌─────────────────────────┐
│  BattleStream           │
│  - Event buffering      │
│  - Batch until request  │
│  - Async iteration      │
└────────────┬────────────┘
             │ Event batches (List[BattleEvent])
             ↓
┌─────────────────────────┐
│  BattleEnvironment      │
│  - Apply events         │
│  - Update state ref     │
│  - History tracking     │
└────────────┬────────────┘
             │ Immutable BattleState
             ↓
┌─────────────────────────┐
│  BattleObserver         │
│  - High-level queries   │
│  - Damage calculations  │
│  - Power agent tools    │
└────────────┬────────────┘
             │ Battle info & predictions
             ↓
┌─────────────────────────┐
│  Agent                  │
│  - Receive state        │
│  - Call tools           │
│  - Reason with LLM      │
│  - Output action        │
└────────────┬────────────┘
             │ BattleAction
             ↓
    (Back to ShowdownClient to send action)
```

**Turn Cycle:**

1. **Receive Events**: `BattleStream` receives events from `ShowdownClient`
2. **Buffer Events**: Stream buffers all events until `RequestEvent` (agent's turn)
3. **Apply Events**: `BattleEnvironment` applies events via `StateTransition`
4. **Create New State**: Each event produces new `BattleState` (immutable)
5. **Agent Decision**: `BattleObserver` wraps state, agent uses tools to decide
6. **Output Action**: Agent returns `BattleAction`
7. **Send to Showdown**: `ShowdownClient` converts action to protocol command and sends
8. **Repeat**: Cycle continues until battle ends

## Key Design Decisions

### Immutability via Events

**Why:**
- Clean replay generation (just replay events)
- Easy debugging (inspect exact state at any turn)
- Potential for rollouts/tree search (create branches without affecting main state)
- Thread-safe by design
- Functional programming benefits (pure functions, no hidden mutations)

**How:**
- All state classes are frozen dataclasses
- Events are the only source of state change
- `StateTransition.apply()` creates new state, never modifies
- State history is list of immutable snapshots

**Trade-offs:**
- More memory per battle (mitigated: ~7.5KB/turn is negligible)
- Slightly more GC pressure (mitigated: Python handles this well)
- Must copy state for changes (mitigated: dataclasses + structural sharing)

### Separation of Concerns

**Protocol Layer** (`ShowdownClient`, `MessageParser`)
- Only knows about Showdown protocol
- No game logic, no state management
- Pure translation between protocol and events

**State Management** (`StateTransition`, `BattleEnvironment`)
- Only knows about game state and events
- No protocol knowledge, no network I/O
- Pure transformation logic

**Agent Interface** (`BattleObserver`, `BattleAction`)
- Only knows about agent needs
- No protocol, no state internals
- High-level battle queries and actions

**Benefits:**
- Easy to test each layer independently
- Can swap protocol implementation (e.g., local simulator vs. Showdown)
- Can test state transitions without network
- Can mock agent interface for testing

### Type Safety

**Full Type Hints:**
- All dataclasses have explicit field types
- All functions have parameter and return type annotations
- Events are discriminated union (pattern matching on type)
- Pyrefly checks ensure type correctness

**Benefits:**
- Catch bugs at development time, not runtime
- IDE autocomplete and refactoring support
- Self-documenting code (types show intent)
- Safe refactoring (type checker validates changes)

**Enforcement:**
- Pyrefly type checking required before commit
- Frozen dataclasses prevent accidental mutation
- Enums for fixed sets (Weather, Status, etc.)

### Async Event Handling

**Why Async:**
- WebSocket communication is inherently async
- Non-blocking I/O for network operations
- Can handle multiple battles concurrently
- Natural async/await flow for turn-based game

**Event Batching:**
- Events arrive in bursts between agent decisions
- `RequestEvent` signals "agent's turn to act"
- `BattleStream` buffers events into batches
- Each batch applied atomically to create new state

**Benefits:**
- Agent doesn't see intermediate state during opponent's turn
- Clean separation: agent acts, then waits for next batch
- Aligns with Showdown's request/response pattern
- Can optimize batch processing (single state update per turn)

## Testing Strategy

### Unit Tests

**State Transition Tests** (`state_transition_test.py`)
- Test each event handler in isolation
- Given: initial state + event
- Expected: new state with specific changes
- No I/O, no mocking needed (pure functions)

**Message Parser Tests** (`message_parser_test.py`)
- Test each protocol message type
- Given: raw message string
- Expected: specific `BattleEvent` with correct data
- Cover edge cases (optional fields, malformed messages)

**Battle Observer Tests** (`battle_observer_test.py`)
- Test query methods with various states
- Test damage calculations with known scenarios
- Test type effectiveness with all combinations
- Use fake game data for controlled testing

### Integration Tests

**Environment Tests** (`battle_environment_test.py`)
- Test full turn cycle with fake client
- Mock `ShowdownClient` to provide scripted events
- Verify state updates correctly through multiple turns
- Test history tracking and replay functionality

**End-to-End Tests**
- Connect to local Showdown server
- Run full battle with random agent
- Verify all events parsed correctly
- Verify final state matches battle outcome

### Battle Scenario Tests

**Create Specific Game States:**
- Entry hazards scenarios (Stealth Rock damage, etc.)
- Weather interactions (Water Spout in rain, Solar Beam in sun)
- Ability triggers (Intimidate, Protosynthesis, etc.)
- Complex interactions (Trick Room + priority moves, etc.)

**Replay Validation:**
- Parse real battle replays
- Apply all events via `StateTransition`
- Verify final state matches replay outcome
- Catch any missed mechanics or parsing errors

## Future Extensions

### Local Simulator Mode

Instead of `ShowdownClient` for network I/O, implement `LocalSimulator` that:
- Generates events locally based on game mechanics
- No network latency, instant battles
- Useful for training (millions of battles)
- Same `BattleEvent` interface, drop-in replacement

### Rollout Support

Immutable state enables speculative execution:
- Agent considers move A: create branch and apply predicted events
- Agent considers move B: create another branch
- Compare outcomes, choose best move
- Requires prediction of opponent action and RNG

### Replay System

State history enables rich replay features:
- Export to Showdown replay format
- Annotate with agent reasoning (why each move was chosen)
- Visualize state changes over time
- Debug agent decisions in specific situations

### Multi-Battle Support

`BattleEnvironment` can manage multiple battles:
- Each battle has its own state
- `BattleStream` filters events by battle ID
- Agent can play multiple games concurrently
- Useful for parallel training and evaluation
