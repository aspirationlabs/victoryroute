# Milestone Plan: Random Agent Battle System

## Current Progress Summary

**Overall Progress: ~90% Complete** 🎉

✅ **Completed (13 milestones):**
- 1.1: Game Data Foundation
- 1.2: Protocol & Events
- 1.3: Battle State Model
- 1.4: State Transitions (all event handlers)
- 1.5a: Battle Environment - Core
- 1.5b: Battle Environment - Action Loop
- 1.6a: Battle Actions
- 1.6b: Agent Interface
- 1.6c: Team Loader
- 1.7a: Random Agent
- 1.7b: Team Download Script
- 1.7c-d: Challenge Handler
- **BONUS:** FirstAvailableAgent (deterministic baseline agent)

⏳ **Remaining (1 milestone set):**
- 1.8a-d: Integration script (run_battle.py for end-to-end battles)

**Next Steps:**
1. Create run_battle.py integration script with CLI args
2. Test full end-to-end battle flow with local Showdown server
3. Add logging and error handling polish

---

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

### Milestone 1.4: State Transitions ✅ **COMPLETE**
- StateTransition class with event dispatcher
- All event handlers implemented (HP, Pokemon changes, stats/status, field effects, request parsing)
- Comprehensive tests

### Milestone 1.6a-c: Battle Actions & Agent Interface ✅ **COMPLETE**
- BattleAction dataclass with Showdown command generation
- Agent abstract base class with async choose_action method
- TeamLoader for parsing and loading team files

### Milestone 1.5a-b: Battle Environment ✅ **COMPLETE**
- `python/game/environment/battle_environment.py` - BattleEnvironment class
- `reset()` method: initialize battle state from event stream
- `step(action)` method: execute actions and advance battle
- `get_state()`, `is_battle_over()`, `get_history()` methods
- Comprehensive tests in `battle_environment_test.py`

### Milestone 1.7a: Random Agent ✅ **COMPLETE**
- `python/agents/random_agent.py` - RandomAgent class
- Picks random moves/switches with configurable probability
- Tests in `random_agent_test.py`

### Milestone 1.7b, 1.7c-d: Team Download & Challenge Handler ✅ **COMPLETE**
- Team download script
- Challenge handler with filtering and timeout logic

### BONUS: First Available Agent ✅ **COMPLETE**
- `python/agents/first_available_agent.py` - FirstAvailableAgent class
- Deterministic agent for testing (always picks first move/switch)
- Tests in `first_available_agent_test.py`

---

## Remaining Milestones

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
1.1 ✅ → 1.2 ✅ → 1.3 ✅ → 1.4 ✅
                              ↓
                          1.5a-b ✅
                              ↓
                          1.6a ✅ (BattleAction)
                              ↓
                          1.6b ✅ (Agent Interface)
                              ↓
                          1.6c ✅ (Team Loader)
                              ↓
                          1.7a ✅ (RandomAgent)
                              ↓
                    ┌─→ 1.7b ✅ (Download Teams)
                    │
                    └─→ 1.7c-d ✅ (Challenge Handler)
                              ↓
                      1.8a → 1.8b → 1.8c → 1.8d ⏳
```

**Current Status:**
- ✅ Completed: 1.1, 1.2, 1.3, 1.4, 1.5a-b, 1.6a, 1.6b, 1.6c, 1.7a, 1.7b, 1.7c-d (13 milestones)
- ⏳ Remaining: 1.8a-d (Integration script)

**Critical Path:**
1.1 ✅ → 1.2 ✅ → 1.3 ✅ → 1.4 ✅ → 1.5a-b ✅ → 1.6a-c ✅ → 1.7a ✅ → 1.7b-d ✅ → 1.8a-d ⏳

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
7. ✅ Random agent is implemented (+ FirstAvailableAgent bonus!)
8. ⏳ **A human can play a full battle against a random agent on a local Showdown server** (NEEDS run_battle.py)

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
