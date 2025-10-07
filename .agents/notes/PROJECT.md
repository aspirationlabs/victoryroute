# VictoryRoute: AI Agents for Competitive Pokémon Battles

## Vision & Goals

Build AI agents capable of winning Pokémon battles through simulation-based training and evaluation. The project focuses on LLM-based agents that can analyze battle states, reason about optimal moves, and make strategic decisions in competitive singles or doubles battles.

**Core Objectives:**
- Implement a complete battle simulator, syncing with Pokemon Showdown via websockets, with full mechanics
- Support multiple LLM providers (GPT-5, Qwen, Llama, custom trained models, Claude Sonnet 4.5) via litellm and Google ADK
- Generate/pull training data from expert battle replays
- Provide tools for agents to reason about game state and possible outcomes

## High-Level Architecture

### Game Simulator
- **Immutable state pattern**: Each turn produces a new environment instance, enabling clean replay generation, rollouts, and debugging
- **Full VGC mechanics**: Type chart, damage calculation, abilities, status conditions, field conditions (weather, terrain, hazards, screens), stat modifications, move effects
- **Simultaneous turn resolution**: Both players submit moves simultaneously, then execution resolves based on priority, speed stats, and RNG (Quick Claw, etc.)
- **Configurable regulations**: Regulations are parameters, not hardcoded - easy to switch between Regulation H, I, or future formats without code changes
- **Initial target**: Gen9OU. Then, Gen1OU and VGC Regulation I.

### Agents
- **Standard interface**: All agents implement a common interface for move selection
- **LLM-based agents**: Primary focus - agents that use language models to reason about battle state and select moves
  - Support for multiple models via litellm and Google ADK
  - Chain-of-thought reasoning for interpretability
  - Customizable prompts per agent type
- **Human passthrough agent**: CLI interface for human players to interact with the simulator for testing and validation

### Tools
Capabilities exposed to agents for reasoning about the game:
- Pokémon lookup (stats, typing, abilities, movepool)
- Move information (power, accuracy, effects, type)
- Damage calculation preview
- Type effectiveness
- Team building and validation
- Game state analysis helpers

### Training Infrastructure
- **Data generation**: Parse and validate Pokémon Showdown battle replays to create training datasets
- **Multiple evaluation methods**:
  - Win rate evaluation (agent vs agent, agent vs baselines)
  - Replay matching (supervised - does agent select same move as expert?)
  - LLM judge (evaluate quality of chain-of-thought reasoning)
- **Model fine-tuning**: Support for training custom models on VGC battle data

### Data Layer
- **JSON-based storage**: Game data (Pokémon, moves, items, natures, abilities, type chart) stored as JSON
- **Sync from source**: Automated scripts to pull and parse data from [smogon/pokemon-showdown](https://github.com/smogon/pokemon-showdown)
- **Type-safe access**: JSON maps to Python dataclasses/objects for type safety and IDE support

## Directory Structure

### `python/agents/`
Agent implementations with shared interface.
- `schema/` - Standard agent interface that all agents must implement
- `basic/` - Simple baseline agents (random, heuristic)
- `llm/` - LLM-based agents with various models
  - Each agent has its own subdirectory with prompts
  - Example: `llm/gen9ou_agent.py`, `llm/prompts/`
- `human/` - Human passthrough agent for CLI interaction

### `python/game/`
Battle simulator core.
- `schema/` - Static, immutable objects (Pokémon, moves, natures, teams, items)
- `environment/` - Runnable environment that maintains and advances battle state. Will interact with the Pokemon Showdown client via websockets.
- `mechanics/` - Individual battle mechanics (damage calculation, type effectiveness, abilities, status conditions, field effects)
- `calculator/` - Damage calculation and outcome prediction
- `rulesets/` - Regulation definitions and team validation logic

### `python/tools/`
Tools exposed to agents for reasoning and decision-making.
- Pokédex lookup
- Move database queries
- Damage calculation utilities
- Type chart queries
- Team builder/validator

### `python/training/`
Training and evaluation infrastructure.
- `data/` - Scripts to generate training and validation datasets from replays
- `evaluation/` - Multiple evaluation methods (win rate, replay matching, LLM judge)
- `fine_tuning/` - Custom model training on VGC data

### `python/scripts/`
Utility scripts for development workflow.
- Data sync scripts (pull pokemon, items, etc. from smogon/pokemon-showdown, convert to JSON)
- Replay parser and validator

### `data/game/`
Static game database (JSON format).
- `pokemon.json` - All Pokémon stats, types, abilities, base stats
- `moves.json` - Move data (power, accuracy, type, effects, priority)
- `abilities.json` - Ability effects and descriptions
- `items.json` - Held items and their effects
- `natures.json` - Nature stat modifications
- `type_chart.json` - Type effectiveness multipliers
- `rulesets/` - Regulation definitions (eligible Pokémon, banned items/moves/abilities, team rules)

## Key Domain Concepts

### VGC Battle Format
- **Doubles battles**: 2v2 format with 4 Pokémon active simultaneously
- **Team of 6, bring 4**: Players build teams of 6 Pokémon, select 4 for each battle
- **Simultaneous decisions**: Both players choose moves at the same time
- **Turn resolution**: Actions execute in order of priority, then speed (with RNG for speed ties and items like Quick Claw)

### Battle Mechanics
Core mechanics that must be simulated:
- **Type effectiveness**: 18 types with multipliers (0x, 0.25x, 0.5x, 1x, 2x, 4x)
- **Damage calculation**: Complex formula involving attack/defense stats, move power, STAB, type effectiveness, weather, abilities, items, screens, etc.
- **Speed mechanics**: Base speed, stat stages, paralysis, Tailwind, Trick Room, Choice Scarf, priority moves
- **Abilities**: Passive effects that modify battle mechanics (Intimidate, Protosynthesis, Drought, etc.)
- **Status conditions**: Burn, paralysis, poison, sleep, freeze
- **Field conditions**: Weather (sun, rain, sand, snow), terrain (electric, grassy, psychic, misty), Trick Room
- **Hazards**: Stealth Rock, Spikes, Sticky Web (less common in VGC but exist)
- **Screens**: Reflect, Light Screen, Aurora Veil
- **Stat stages**: ±6 stages for each stat (attack, defense, special attack, special defense, speed, accuracy, evasion)
- **Move effects**: Protect, Follow Me, Wide Guard, Fake Out, etc.

### Regulation Configuration
Regulations define legal Pokémon, items, moves, and team restrictions. Must be easily configurable:
- Eligible Pokémon by Pokédex number or species
- Restricted Pokémon limits (e.g., max 2 restricted in Regulation I, 0 in Regulation H)
- Banned abilities, moves, or items
- Team size and battle format rules
- Level caps and stat modifications

## Evaluation Strategy

### 1. Win Rate Evaluation
Measure agent performance by battle outcomes:
- Agent vs agent (self-play)
- Agent vs baseline agents (random, simple heuristics)
- Elo ratings across multiple agents
- Statistical significance testing

### 2. Replay Matching (Supervised)
Evaluate how often the agent selects the same move as an expert player:
- Parse replays from high-level VGC matches
- Present same game state to agent
- Measure accuracy of move selection
- Useful for automated training evaluation

### 3. LLM Judge
Evaluate the quality of the agent's reasoning:
- Extract chain-of-thought from LLM agent
- Use another LLM to judge quality of reasoning
- Assess strategic understanding beyond just move selection

## Development Workflow

1. **Data Sync**: Run scripts to pull latest game data from smogon/pokemon-showdown and convert to JSON
2. **Build Simulator**: Implement core battle mechanics with comprehensive tests (foo.py + foo_test.py pattern)
- By this step, connect to a locally hosted Showdown server for a human to play against a basic agent with randomized actions.
3. **Implement Agents**: Create agents following the standard interface
4. **Generate Evaluation Data**: Parse replays and create evaluation datasets
5. **Run Evaluations**: Test agents using multiple evaluation methods
6. **Iterate**: Refine agents, prompts, and tools based on evaluation results
7. **Running Scripts**: Assume the venv is running. This is not a bazel project. Just run python <script>.

## Testing Philosophy

- **Test files co-located**: Each `foo.py` has corresponding `foo_test.py` in same directory
- **Executing Tests**: Just run `pytest` to run all tests.
- **Immutable state simplifies testing**: Easy to set up specific game states for unit tests
- **Battle scenarios as test cases**: Key battle mechanics verified through scenario tests

## Future Considerations

### Additional Regulations
- Easy addition of new rulesets (Regulation I with 2 restricted Pokémon, Regulation J with Mythicals, etc.)
- Historical regulations for training on past competitive seasons

### Advanced Features
- Team building agents (not just battle agents)
- Meta analysis tools (usage stats, team archetypes, hypothesizing teams)
- Replay database and analysis
- Tournament simulation framework

## Non-Goals

This project explicitly does NOT include:
- Reinforcement learning agents
- Tree search or rollout-based agents (MCTS, minimax, etc.)
- Game rendering or graphical interface
- Mobile or web deployment

The focus is purely on LLM-based agents evaluated through simulation.
