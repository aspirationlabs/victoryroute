# Pokemon Battle Agent

I attempted a Pokemon battle agent that relies on raw LLM prompts. My goal was to build an intuition around raw LLM capabilities between different providers, along with how to use open source SDKs to build provider-agnostic agents with minimal per-provider code.

## Getting Started

### Prerequisites

You'll need a Pokemon Showdown server to battle against. You can use either a local server or the online production server.

#### Local Server Setup

```bash
# Clone the Pokemon Showdown repository
git clone https://github.com/smogon/pokemon-showdown.git
cd pokemon-showdown

# Install dependencies and start the server
npm install
node pokemon-showdown start
```

You can connect to the local server via websockets at `ws://localhost:8000/showdown/websocket`.

#### Online Server

The production Pokemon Showdown server is available at `wss://sim3.psim.us/showdown/websocket`.

### Running the Agent

Example commands for running the turn predictor agent in different configurations:

```bash
# Challenge a specific opponent on local server
python python/battle/run_battle.py \
  --agent=turn_predictor \
  --server_url=ws://localhost:8000/showdown/websocket \
  --opponent=OpponentUsername \
  --challenge_timeout=30

# Queue for ladder matches on local server
python python/battle/run_battle.py \
  --agent=turn_predictor \
  --server_url=ws://localhost:8000/showdown/websocket \
  --format=gen9ou

# Challenge a specific opponent on online server
python python/battle/run_battle.py \
  --agent=turn_predictor \
  --server_url=wss://sim3.psim.us/showdown/websocket \
  --opponent=OpponentUsername \
  --challenge_timeout=30

# Queue for ladder matches on online server
python python/battle/run_battle.py \
  --agent=turn_predictor \
  --server_url=wss://sim3.psim.us/showdown/websocket \
  --format=gen9ou
```

## Approach

This project implements two LLM-based battle agents with different levels of sophistication. Both agents use Google's Agent Development Kit (ADK) as the orchestration framework and connect to various LLM providers through LiteLLM.

### Zero Shot Agent

The zero shot agent represents a straightforward approach to LLM-based battle decision-making. On each turn, the agent makes a single LLM call with the current battle state and asks the model to choose the best action.

The agent is equipped with a game data lookup tool that allows it to query Pokemon stats, move details, type matchups, and other game mechanics during its reasoning process. The prompt includes the full battle history, visible Pokemon information, and available actions. The LLM responds with structured output conforming to a Pydantic schema that specifies the chosen action.

In the background, to build the visible battle state, it runs a simulator to update the field and Pokemon health and conditions based on server events.

By default, the zero shot agent uses Gemini 2.5 Flash Lite with a thinking budget of 1024 tokens, allowing the model to reason through the decision before committing to an action. The approach is simple but effective for many battle scenarios, relying entirely on the LLM's ability to understand Pokemon strategy from its training data.

### Turn Predictor Agent

The turn predictor agent is a more sophisticated multi-stage system that combines competitive data analysis, battle simulation, and multi-agent reasoning. Rather than asking an LLM to make decisions based purely on intuition, this approach breaks down the decision-making process into distinct stages, each handled by specialized sub-agents.

#### Stage 1: Team Prediction

The first stage predicts the opponent's unrevealed Pokemon capabilities. Since Pokemon Showdown uses Team Preview, we know which Pokemon the opponent has, but we don't know their specific movesets, items, abilities, or Tera types until they're revealed in battle.

The team predictor agent analyzes the current battle state and uses competitive usage statistics from high-level play to make informed predictions. It has access to two tools: one for querying game data and another for retrieving usage statistics that show what movesets, items, and abilities are most commonly used on each Pokemon in the current format.

For each unrevealed Pokemon on the opponent's team, the agent predicts the most likely moveset, held item, ability, and Tera type. These predictions are based on the combination of usage statistics and contextual information from the battle. The agent outputs structured predictions that are used in the next stage.

#### Stage 2: Action Simulation

With predictions about the opponent's team in hand, the second stage simulates all possible action combinations for the current turn. This includes our Pokemon's available moves and switches crossed with the opponent's possible moves and switches.

The action simulation agent uses a battle simulator that performs detailed damage calculations accounting for:
- Base stats, EVs, IVs, and natures
- Type effectiveness and STAB (Same Type Attack Bonus)
- Abilities, items, and status conditions
- Weather, terrain, and other field effects
- Critical hit probabilities
- Move priorities and speed calculations

For each action pair, the simulator generates comprehensive outcome data including HP ranges after damage (accounting for damage rolls), knockout probabilities, and move order. This produces a complete picture of what could happen on the turn.

The simulation outputs are structured with unique IDs for each action combination, allowing subsequent agents to reference specific scenarios when reasoning about which action to take.

I'm noting that while the simulator itself has many edge cases which may manifest as bugs, most move simulations are roughly accurate (align with Showdown calculator).

#### Stage 3: Battle Decision Loop

The final stage uses a proposal-critique-refinement loop to select the best action based on the simulation results. This involves three sub-agents working together:

1. **Initial Decision Agent**: Reviews all simulation outcomes and proposes the action that appears strongest based on damage output, knockout potential, risk management, and strategic positioning.

2. **Risk Analyst Agent**: Acts as a critique agent, examining the proposed action for potential weaknesses, risks, and overlooked alternatives. It considers factors like prediction dependence (what if the opponent doesn't have the predicted moveset?), counter-play options, and long-term game state implications.

3. **Refinement Agent**: Takes the original proposal and the critique, then makes a final decision on whether to stick with the initial choice or adjust to a different action. This agent weighs the risks identified against the benefits and chooses the action with the best expected outcome.

Each agent in this loop outputs structured data conforming to specific Pydantic schemas. The final output is a valid battle action that gets sent to the Pokemon Showdown server.

#### JsonLlmAgent

A critical component of the turn predictor agent is the JsonLlmAgent wrapper. This addresses a fundamental challenge when working with LLMs and structured output: even when you specify an output schema, LLMs sometimes return prose, markdown formatting, or imperfect JSON.

The JsonLlmAgent wraps any base agent in a sequential workflow that includes a coercion step. After the primary agent generates its response, a second pass extracts and validates JSON from the output, handling edge cases like:
- JSON wrapped in markdown code fences
- Prose text surrounding the actual JSON
- Minor formatting issues that can be cleaned up

This wrapper ensures that every agent in the turn predictor pipeline produces valid structured output that conforms to its schema, making the multi-agent workflow reliable and deterministic. Without this innovation, the pipeline would frequently fail when an LLM decided to explain its reasoning in prose rather than returning pure JSON.

## Learnings

This project involved building LLM agents using Google's Agent Development Kit (ADK), which in turn uses LiteLLM to connect to various model providers (OpenAI, Anthropic, Google, OpenRouter). The following observations are personal learnings from this development process rather than authoritative statements about these libraries.

### LiteLLM Configuration Limitations

I found LiteLLM's configuration model to be at odds with object-oriented design principles. The library advertises many configurables like retry behavior, fallback models, and timeout settings, but the interface relies heavily on global configuration rather than object-level encapsulation.

For example, settings like `litellm.num_retries` are global variables that affect all LLM calls across the entire application, rather than being parameters you can specify when instantiating an LLM model object. This makes it difficult to have different retry policies for different use cases, or to inject custom interceptors for specific model instances.

I would have preferred an interface where you instantiate an LLM client object with specific configuration, and that configuration is scoped to that object's lifetime. Something like being able to pass retry handlers, fallback chains, and timeout policies as constructor parameters would make the library feel more properly object-oriented and testable.

### Google ADK Failures

Google's ADK provides many useful configuration options for building agents, such as specifying output schemas, providing tools, setting thinking budgets, and more. However, I encountered frequent issues where these configuration options would silently fail when the underlying model provider didn't support the feature.

The most frustrating example was with tool calling. I was writing an eval that required the agent to use tools, but observed that no tool calls were being made. After significant debugging, I discovered that not all OpenRouter models that claim to support function calling actually have the `support_function_calling` flag set in LiteLLM's provider configuration. As a result, passing the `tools` parameter to the ADK agent had no effect - it was simply ignored.

Similarly, when specifying an `output_schema` parameter, ADK would still throw errors when the LLM returned non-JSON output, without providing good retry mechanisms or fallbacks. This is what led me to build the JsonLlmAgent wrapper - I needed deterministic structured output and neither ADK nor LiteLLM provided reliable mechanisms for coercing LLM responses into valid JSON.

My preference would be for these libraries to fail loudly when you specify a configuration parameter that isn't supported by the underlying model. Throw an exception at initialization time if I'm requesting tool calling from a model that doesn't support it. There could be a "dangerous mode" where you explicitly opt into warnings instead of errors, but the default should be to catch configuration mismatches early rather than silently ignoring parameters.

### ADK Web UI and Eval Tooling Issues

I experienced several issues with ADK's development tooling that made debugging more difficult than it should have been.

The ADK web UI seems buggy. When stepping into Pass/Fail test cases, the UI would sometimes show nothing at all, leaving a blank screen. The execution history would still get written to the appropriate `eval_history/` folder for the exposed agent, so I could examine the data manually, but the UI itself was unreliable for debugging.

The ADK eval CLI also has limitations that hampered debugging. The CLI doesn't allow you to update the logging level, so it only logs warnings by default. When errors occur during eval runs, the stack traces are obfuscated, making it very difficult to identify exactly where in the code the error originated. This was especially frustrating when debugging issues like LLM output not conforming to the specified `output_schema` parameter - I would see that something failed, but not get clear information about which agent in the pipeline failed or what the actual LLM output was.

Another issue is that ADK evals fail completely when individual test cases throw errors. Ideally, a test framework should isolate failures - if one test case errors, it should fail that specific test case while continuing to run others, and still show execution history up to the point of failure (e.g., if several subagents executed successfully but a downstream subagent threw an error). Instead, one failing test case can block visibility into all the other test cases.

### JsonLlmAgent as a Solution

The JsonLlmAgent I built turned out to be essential for making the turn predictor agent reliable. As mentioned earlier, LLMs don't always return perfect JSON even when you specify an output schema, and neither ADK nor LiteLLM provided satisfactory mechanisms for handling this.

JsonLlmAgent is a SequentialAgent wrapper that takes any base agent and adds a coercion step. After the base agent generates its response, a second LLM call extracts valid JSON from the output, handling markdown code fences, surrounding prose, and minor formatting issues. The extracted JSON is then validated against the Pydantic schema.

This two-step approach dramatically improved JSON output determinism. Instead of failing 20-30% of the time when an LLM decided to explain its reasoning in prose, the success rate jumped to near 100% because the coercion step could extract the structured data even from messier outputs.

I wish this kind of functionality was built into ADK or LiteLLM as a configurable option. Structured output is a common need, and requiring every developer to build their own coercion layer seems like a gap in the framework. You could also turn the SequentialAgent into a LoopAgent, using max_retries as a parameter for how many cycles before the agent gives up outputting a well-formed JSON and throws.

### Model Performance and Latency

I tested several model providers and found significant differences in latency that have practical implications for real-time Pokemon battles.

OpenAI models had very high latency. A single call to GPT-4o-mini could take multiple seconds, and a full turn with the zero shot agent could take 10+ seconds. For the turn predictor agent with its multi-stage workflow, OpenAI models were prohibitively slow. Given that Pokemon Showdown battles have turn timers, this latency makes OpenAI models infeasible for ladder play.

Claude Sonnet (Anthropic) was roughly 50% faster than OpenAI models, with typical response times of a few seconds per call. Still too slow for comfortable ladder play, but usable for casual battles.

Gemini Flash models (Google) had the best cost-to-performance ratio. Most LLM calls completed in a few hundred milliseconds, making even the complex turn predictor agent fast enough for ladder battles. The quality of responses was also good - not quite as sophisticated as Claude Sonnet in some cases, but more than adequate for Pokemon battle decisions.

Based on these findings, I defaulted the agents to use Gemini Flash models. For live battles, latency is not just a convenience factor - it's a hard requirement due to battle timeouts.
