from google.adk.sessions import BaseSessionService, InMemorySessionService
from python.agents.agent_interface import Agent

from google.adk.agents import SequentialAgent

class TurnPredictorAgent(Agent):
    def __init__(
        self,
        session_service: BaseSessionService = InMemorySessionService(),
        model_name: str = "openrouter/google/gemini-2.5-flash-lite-preview-09-2025",
        mode: str = "gen9ou",
        past_actions_count: int = 5
        max_retries: int = 3
    ):
        self._model_name: str = model_name
        self._app_name: str = "turn_predictor_pokemon_battler_agent"
        self._game_data: GameData = GameData()
        self._max_retries: int = max_retries
        self._battle_room_to_logger: Dict[str, LlmEventLogger] = {}
        self._battle_room_to_session: Dict[str, Session] = {}
        self._battle_room_to_action_generator: Dict[str, BattleActionGenerator] = {}

    def _create_agent(self, model_name, app_name, system_instructions) -> BaseAgent:
        def tool_get_object_game_data(name: str) -> str:
            """Look up game data for Pokemon, Move, Ability, Item, or Nature.

            Returns detailed stats, types, effects, and descriptions. Use to check:
            Pokemon base stats, move power/effects, ability mechanics, item effects, nature effects.

            Args:
                name: Object name (e.g., "Landorus", "Earthquake", "Intimidate", "Choice Scarf")
            """
            return get_object_game_data(name, self._game_data)

        # User query will provide:
        # state['turn_number'] -> str (input)
        # state['our_player_id'] -> str (input)
        # state['available_actions'] -> List[str] (input) or List[BattleAction]
        # state['battle_state'] -> BattleState (input)
        # state['opponent_potential_actions'] -> str (input) or List[BattleAction]
        # state['opponent_active_pokemon'] -> PokemonState (input)
        # state['past_battle_event_logs_xml'] -> string (input) or dict[int, str]
        # state['past_player_actions_xml'] -> string (input) or dict[str, List[BattleAction]]

        # TODO: System instructions will be to predict the PokemonState given a known PokemonState.
        # On each query, you'll need to read:
        # - state['our_player_id']
        # - state['opponent_active_pokemon']
        # - state['past_battle_event_logs_xml']
        # - state['past_player_actions_xml']
        # tool call: get_pokemon_usage_stats(mode: str, pokemon_species: str) -> PokemonUsagePriors
        # tool call: get_game_data
        # 
        # Output: state['opponent_predicted_active_pokemon'] -> PokemonState (fill in up to four moves if not known already from input,
        # predict items if not known from input, predict tera_type if not known / not terrastilized yet, predict ability if not known)
        # You can read the past battle actions to determine most likely ability / items, use the percentage appearance stats to guide
        # the decision.
        opponent_pokemon_predictor_agent = LlmAgent(
            model=LiteLlm(model=model_name),
            name=app_name,
            instruction='',
            planner=BuiltInPlanner(
                thinking_config=types.ThinkingConfig(
                    include_thoughts=True,
                    thinking_budget=1024,
                )
            ),
            include_contents="none",
            tools=[tool_get_object_game_data],
            output_schema=PokemonState,
            disallow_transfer_to_parent=True,
            disallow_transfer_to_peers=True,
        )
        # TODO: Create a custom agent now.
        # Read state['opponent_predicted_active_pokemon'] and battle state.
        # Compute for each possible move/switch, a SimulationAction.
        # 1. Move + (tera/no-tera) * Opponent move / switch (4 * 2 + 5 for 13 options) = 52. Pick best option.
        # 2. Switch * Opponent move / switch (4 * 2 + 5 for 13 options) = 65
        # 3. Output: state['simulation_actions'] -> List[SimulationAction].
        # tool call: BattleSimulator.get_move_order
        # tool call: BattleSimulator.estimate_move_result
        # If the pokemon will faint after first move goes, then indicate ko potential, and if not ko'd then return the end hps.

        # TODO: Create a LoopAgent.
        # Based on the simulation actions, choose the best available move/switch we use.
        # Reason based on what the moves do, the opponent potential actions, and potential simulations to guide damage and outcomes.
        # For example, if a simulation includes a setup move and opponent can KO, probably don't want to use the setup move.
        # If the opponent doesn't have a setup move and no real damage moves, it's probably safe to set up. 
        # Protect can scout.
        # Priority moves can move first to try to KO. Opt for damage/KO when possible.
        # - state['battle_state']
        # - state['available_actions']
        # - state['available_opponent_actions'] (?)
        # - state['simulation_actions']
        # tool call: get_object_game_data.
        # Agent 1: Output first action.
        # Agent 2: Critique (what edge cases did you not consider in either the simulation actions or potential opponent actions not in simulation that can be a threat, adn why is it a threat? Do you reconsider or update your rationale? Why? If you update your rationale, what is the new rationale?)
        # Agent 3: Output a new action or update rationale. Reformat and make sure you output a proper BattleAction.
        # Output: BattleAction.
        # ...
        return SequentialAgent(
            name=self._app_name,
            sub_agents=[opponent_pokemon_predictor_agent, simulation_action_agent, loop_agent]
        )