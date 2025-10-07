# Milestone Plan: Random Agent Battle System

## Overview

This document breaks down the first major milestone into actionable sub-milestones. The goal is to have a locally hosted Pokémon Showdown server where a human can challenge and battle against a RandomAgent that makes randomized moves.

**First Milestone from PROJECT.md:**
> 1. **Data Sync**: Run scripts to pull latest game data from smogon/pokemon-showdown and convert to JSON ✅
> 2. **Build Simulator**: Implement core battle mechanics with comprehensive tests (foo.py + foo_test.py pattern)
>    - By this step, connect to a locally hosted Showdown server for a human to play against a basic agent with randomized actions.

## Completed Milestones

### Milestone 1.1: Game Data Foundation ✅ **COMPLETE**
- JSON data files in `data/game/` (pokemon, moves, abilities, items, natures, type_chart)
- Python data models in `python/game/data/`
- GameData loader with query methods
- 89 tests passing

### Milestone 1.2: Protocol & Events ✅ **COMPLETE**
- 55+ event types in `python/game/events/battle_event.py`
- MessageParser with full protocol support
- BattleStream for async event batching (live/replay modes)
- ShowdownClient with WebSocket + authentication
- RequestEvent includes JSON payload with available actions
- 106 parser tests + 5 stream tests passing

### Milestone 1.3: Battle State Model ✅ **COMPLETE**
- Immutable frozen dataclasses: PokemonState, TeamState, FieldState, BattleState
- Enums for Status, Weather, Terrain, SideCondition, FieldEffect, Stat
- BattleState includes available_moves, available_switches, can_mega, can_tera flags
- All tests passing for state construction and immutability

---

## Remaining Milestones

### Milestone 1.4a: State Transitions - Core Framework

**Goal**: StateTransition class with basic HP changes

**Deliverables:**
- `python/game/environment/state_transition.py` - `StateTransition` class
- `apply(state: BattleState, event: BattleEvent) -> BattleState` - Main dispatcher
- Handlers for: `DamageEvent`, `HealEvent`, `SetHpEvent`
- Tests for immutability (original state unchanged)
- Tests with simple event sequences

---

### Milestone 1.4b: State Transitions - Pokemon Changes

**Goal**: Switch and faint mechanics

**Deliverables:**
- Handlers for: `SwitchEvent`, `DragEvent` (clear volatile conditions)
- Handler for: `FaintEvent` (mark Pokemon as fainted)
- Handlers for: `ReplaceEvent`, `DetailsChangeEvent`
- Tests for switch scenarios (volatiles cleared, stat boosts preserved)
- Tests for faint handling

---

### Milestone 1.4c: State Transitions - Stats & Status

**Goal**: Stat boosts and status conditions

**Deliverables:**
- Handlers for: `BoostEvent`, `UnboostEvent`, `SetBoostEvent`, `ClearBoostEvent`, `ClearAllBoostEvent`, `ClearNegativeBoostEvent`
- Stat boost clamping to ±6
- Handlers for: `StatusEvent`, `CureStatusEvent`
- Tests for stat modifications
- Tests for status conditions

---

### Milestone 1.4d: State Transitions - Field Effects

**Goal**: Weather, terrain, and side conditions

**Deliverables:**
- Handlers for: `WeatherEvent`, `FieldStartEvent`, `FieldEndEvent`
- Handlers for: `SideStartEvent`, `SideEndEvent`
- Weather/terrain expiration tracking
- Side condition stacking (Spikes layers, etc.)
- Tests for field effect interactions

---

### Milestone 1.4e: State Transitions - Request Parsing

**Goal**: Parse available actions from RequestEvent

**Deliverables:**
- Handler for: `RequestEvent` → parse JSON payload
- Populate `BattleState.available_moves` (list of move indices)
- Populate `BattleState.available_switches` (list of Pokemon indices)
- Populate `BattleState.can_mega`, `can_tera`, `is_forced_switch`, `is_trapped`
- Tests verifying available actions correctly extracted from JSON
- **KEY**: This ensures agents get valid actions directly from Showdown

---

### Milestone 1.5a: Battle Environment - Core

**Goal**: BattleEnvironment class with state tracking

**Deliverables:**
- `python/game/environment/battle_environment.py` - `BattleEnvironment` class
- Constructor: accepts `ShowdownClient`, `StateTransition`, optional history tracking
- `reset()` method: initialize battle state
- Apply events sequentially via `StateTransition.apply()`
- `get_state()` accessor (read-only)
- `is_battle_over()` detection
- Basic tests with mock event sequences

---

### Milestone 1.5b: Battle Environment - Action Loop

**Goal**: Full step() cycle

**Deliverables:**
- `step(action: BattleAction) -> BattleState` method:
  1. Send action to ShowdownClient
  2. Collect event batch from BattleStream (until next RequestEvent)
  3. Apply all events via StateTransition
  4. Update internal state
  5. Optionally append to history
  6. Return new state
- Error handling (connection errors, state transition errors)
- Integration tests with mock ShowdownClient

---

### Milestone 1.6a: Battle Actions

**Goal**: Action dataclass and Showdown command generation

**Deliverables:**
- `python/game/interface/battle_action.py` - `BattleAction` dataclass
  - `action_type: ActionType` (MOVE, SWITCH)
  - `move_index: Optional[int]` (0-3 for moves)
  - `switch_index: Optional[int]` (0-5 for switches)
  - `target_index: Optional[int]` (for doubles)
  - `mega: bool`, `tera: bool` flags
- `to_showdown_command() -> str` - Convert to protocol command:
  - MOVE → `/choose move {move_index + 1}`
  - SWITCH → `/choose switch {switch_index + 1}`
  - MEGA → `/choose move {move_index + 1} mega`
  - TERA → `/choose move {move_index + 1} tera`
- Tests for command conversion
- **NO validation needed**: Agent picks from state.available_moves/switches

---

### Milestone 1.6b: Agent Interface

**Goal**: Abstract base class for agents

**Deliverables:**
- `python/agents/agent_interface.py` - `Agent` abstract class
- `async choose_action(state: BattleState, game_data: GameData) -> BattleAction`
- All agents implement this method
- Documentation for agent implementation
- **Note**: Agent receives BattleState and GameData directly (no wrapper class)

---

### Milestone 1.6c: Team Loader

**Goal**: Load and parse team files

**Deliverables:**
- `python/game/interface/team_loader.py` - `TeamLoader` class
- Parse Showdown .team format from data/teams/{format}/*.team
- Convert to /utm protocol command format
- Team selection strategies:
  - Explicit: `--team-index N` → load data/teams/{format}/{N}.team
  - Random: pick random .team file from directory
  - Default format: gen9ou
- Tests with sample team files

---

### Milestone 1.7a: Random Agent

**Goal**: Agent that picks random valid actions

**Deliverables:**
- `python/agents/random_agent.py` - `RandomAgent` class
- `async choose_action(state: BattleState, game_data: GameData) -> BattleAction`:
  - Randomly pick from `state.available_moves` or `state.available_switches`
  - Return valid `BattleAction`
- No validation needed (picks from what RequestEvent provided)
- Tests ensuring always returns valid action from available options

---

### Milestone 1.7b: Team Download Script

**Goal**: Script to download teams into data/teams/{format}/

**Deliverables:**
- `python/scripts/download_teams.py` - Script to download/organize teams
- Support common formats: gen9ou, gen9vgc, gen8ou, etc.
- Save as .team files (Showdown export format)
- Documentation for usage

---

### Milestone 1.7c: Challenge Handler - Basic

**Goal**: Listen for and accept challenges

**Deliverables:**
- `python/game/interface/challenge_handler.py` - `ChallengeHandler` class
- Listen for `|pm|` messages with `/challenge` format
- Parse challenger username from message
- Accept challenge via `/accept USERNAME` command
- Join battle room when challenge accepted
- Tests with mock PM messages

---

### Milestone 1.7d: Challenge Handler - Filtering & Timeout

**Goal**: Filter challenges and send proactive challenges

**Deliverables:**
- `--opponent USERNAME` filter (case insensitive matching)
- `--challenge-timeout SECONDS` (default 120)
- Logic:
  - If opponent specified: only accept matching challenges
  - If timeout expires and opponent specified: send `/challenge USERNAME,{format}`
  - If no opponent: accept all challenges, never send
- Tests for filtering and timeout behavior

---

### Milestone 1.8a: Integration - Connection & Team

**Goal**: Connect to Showdown and load team

**Deliverables:**
- `python/scripts/run_battle.py` - Main entry point
- Command-line args:
  - `--server-url` (default: ws://localhost:8000)
  - `--username` (required)
  - `--password` (optional)
  - `--format` (default: gen9ou)
  - `--team-index` (optional, random if not specified)
- Initialize GameData
- Create ShowdownClient
- Connect and authenticate
- Load team using TeamLoader (random or explicit index)
- Send `/utm TEAM_DATA` command
- Test with local Showdown server

---

### Milestone 1.8b: Integration - Challenge Flow

**Goal**: Handle challenge workflow

**Deliverables:**
- Add command-line args:
  - `--opponent USERNAME` (optional)
  - `--challenge-timeout SECONDS` (default 120)
- Run ChallengeHandler with configured params
- Accept or send challenge based on params
- Join battle room when challenge matched
- Initialize BattleEnvironment when battle room joined
- Test full challenge workflow

---

### Milestone 1.8c: Integration - Battle Loop

**Goal**: Run complete battle with RandomAgent

**Deliverables:**
- Initialize RandomAgent
- Main battle loop:
  1. `state = await env.reset()` - Wait for battle start
  2. While not battle over:
     - `action = await agent.choose_action(state, game_data)`
     - `state = await env.step(action)`
  3. Display battle result
- Handle battle completion (win/loss)
- Disconnect cleanup
- Test complete battle (human challenges RandomAgent, or vice versa)

---

### Milestone 1.8d: Integration - CLI & Polish

**Goal**: Production-ready CLI with logging

**Deliverables:**
- Battle event logging to file
- Error handling and graceful failures
- Helpful error messages for common issues
- Full end-to-end acceptance test
- Documentation:
  - `docs/setup_local_showdown.md` - Local server setup instructions
  - `docs/running_battles.md` - How to run battles with the agent
- Example usage:
  ```bash
  # RandomAgent waits for challenges
  python python/scripts/run_battle.py --username BotPlayer

  # RandomAgent challenges specific opponent
  python python/scripts/run_battle.py --username BotPlayer --opponent HumanPlayer

  # Use specific team
  python python/scripts/run_battle.py --username BotPlayer --team-index 0
  ```

---

## Dependency Tree

```
1.1 ✅ → 1.2 ✅ → 1.3 ✅
                    ↓
                1.4a → 1.4b → 1.4c → 1.4d → 1.4e
                                                ↓
                                            1.5a → 1.5b
                                                      ↓
                                                  1.6a (BattleAction)
                                                      ↓
            1.6b (Agent Interface) ← ─ ─ ─ ─ ─ ─ ─ ─ ┘
                    ↓
            1.6c (Team Loader)
                    ↓
            1.7a (RandomAgent)
                    ↓
        ┌─→ 1.7b (Download Teams)
        │
        └─→ 1.7c → 1.7d (Challenge Handler)
                    ↓
            1.8a → 1.8b → 1.8c → 1.8d
```

**Parallelization Opportunities:**
- 1.4a-1.4e can be developed incrementally but sequentially
- 1.6a-1.6c can overlap with 1.5b completion
- 1.7b (team download) can happen anytime after 1.6c is designed
- 1.7c-1.7d can be developed in parallel with 1.7a

**Critical Path:**
1.1 ✅ → 1.2 ✅ → 1.3 ✅ → 1.4a-e → 1.5a-b → 1.6a-c → 1.7a-d → 1.8a-d

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
