"""Main integration script for running Pokemon Showdown battles with agents.

This script connects to a local Pokemon Showdown server, loads a team,
handles challenges, and runs battles using the specified agent.
"""

import asyncio
import time
from typing import List

from absl import app, flags, logging

from python.agents.agent_registry import AgentRegistry
from python.agents.zero_shot_agent import ZeroShotAgent
from python.battle.opponent_stats_tracker import OpponentStatsTracker
from python.game.environment.battle_environment import BattleEnvironment
from python.game.exceptions import ServerErrorException
from python.game.interface.challenge_handler import ChallengeHandler
from python.game.interface.team_loader import TeamLoader
from python.game.protocol.battle_event_logger import BattleEventLogger
from python.game.protocol.showdown_client import ShowdownClient

FLAGS = flags.FLAGS

# Agent selection
flags.DEFINE_string(
    "agent",
    "random",
    f"Agent type to use. Available: {', '.join(AgentRegistry.get_available_agents())}",
)

# Connection settings
flags.DEFINE_string(
    "server_url",
    "ws://localhost:8000/showdown/websocket",
    "WebSocket URL of the Showdown server",
)

flags.DEFINE_string(
    "username",
    "",
    "Username to connect with (default: auto-generated from agent name and timestamp)",
)

flags.DEFINE_string(
    "password",
    "",
    "Password for the account (leave empty for guest)",
)
flags.DEFINE_string(
    "format",
    "gen9ou",
    "Battle format (e.g., gen9ou, gen1ou)",
)
flags.DEFINE_integer(
    "team_index",
    None,
    "Specific team index to load (default: random team)",
)
flags.DEFINE_string(
    "opponent",
    None,
    "Opponent username to challenge/accept challenges from (default: accept any)",
)
flags.DEFINE_integer(
    "challenge_timeout",
    120,
    "Timeout in seconds before sending proactive challenge to opponent",
)
flags.DEFINE_float(
    "move_delay",
    0.0,
    "Delay in seconds before sending each move to the server (default: 0)",
)
flags.DEFINE_bool(
    "log_events",
    True,
    "Enable logging of all battle events to /tmp/logs/<agent>_<opponent>_<epoch>.txt",
)

flags.DEFINE_bool(
    "enable_timer",
    True,
    "Enable Pokemon Showdown's built-in battle timer (default: True)",
)
flags.DEFINE_integer(
    "server_error_retries",
    5,
    "Maximum number of retries when server returns an error (default: 5)",
)


def generate_default_username(agent_name: str) -> str:
    """Generate a default username based on agent name and timestamp.

    Args:
        agent_name: Name of the agent being used

    Returns:
        Username in format 'PGC <agent_name>_<epoch_timestamp>'
    """
    timestamp = int(time.time())
    return f"PGC {agent_name}_{timestamp}"


async def run_battle() -> None:
    """Main function to continuously run battles with the specified agent."""
    logging.info("Creating agent: %s", FLAGS.agent)
    try:
        agent = AgentRegistry.create_agent(FLAGS.agent)
        logging.info("Agent created successfully: %s", type(agent).__name__)
    except ValueError as e:
        logging.error("%s", e)
        return
    username = FLAGS.username or generate_default_username(FLAGS.agent)
    client = ShowdownClient()
    stats_tracker = OpponentStatsTracker()

    try:
        await client.connect(FLAGS.server_url, username, FLAGS.password)
        logging.info(f"Connected successfully as {username} to {FLAGS.server_url}")

        team_loader = TeamLoader(format_name=FLAGS.format)
        team_data = team_loader.load_team(team_index=FLAGS.team_index)
        logging.info(f"Packed team (length {len(team_data)}): {team_data}")
        challenge_handler = ChallengeHandler(
            client=client,
            format=FLAGS.format,
            opponent=FLAGS.opponent,
            challenge_timeout=FLAGS.challenge_timeout,
            team_data=team_data,
        )

        battle_count = 0
        while True:
            battle_count += 1
            logging.info(f"\n=== Battle #{battle_count} ===")

            if FLAGS.opponent:
                logging.info(
                    f"Waiting for challenges from {FLAGS.opponent} (timeout: {FLAGS.challenge_timeout}s)..."
                )
            else:
                logging.info("Waiting for challenges from any opponent...")

            battle_room = await challenge_handler.listen_for_challenges()
            logging.info(f"Challenge accepted! Battle room: {battle_room}")

            if FLAGS.enable_timer:
                logging.info("Enabling battle timer...")
                await client.send_message(f"{battle_room}|/timer on")

            logger = None
            if FLAGS.log_events:
                logger = BattleEventLogger(
                    FLAGS.username, int(time.time()), battle_room, FLAGS.opponent
                )
                logging.info("Event logging enabled")

            env = BattleEnvironment(
                client, battle_room=battle_room, track_history=False, logger=logger
            )

            state = await env.reset()
            logging.info(
                f"Battle {battle_room} started! Agent is ready to make decisions."
            )

            turn_count = 0
            while not env.is_battle_over():
                # Skip if we're waiting for opponent to choose
                if state.waiting:
                    logging.debug("Waiting for opponent's choice...")
                    state = await env.wait_for_next_state()
                    continue

                if state.team_preview:
                    logging.info("Team preview - agent choosing team order...")
                else:
                    turn_count += 1
                    logging.info(
                        f"Battle {battle_room} - Turn {turn_count} - Agent choosing action..."
                    )

                action = await agent.choose_action(
                    state, battle_room, env.get_battle_stream_store()
                )
                logging.info(f"Action selected: {action}")

                if FLAGS.move_delay > 0:
                    await asyncio.sleep(FLAGS.move_delay)

                server_error_retries = 0
                while server_error_retries < FLAGS.server_error_retries:
                    try:
                        state = await env.step(action)
                        break
                    except ServerErrorException as e:
                        logging.warning(
                            f"Server error on turn {turn_count}: {e.error_text}"
                        )
                        retry_action = await agent.retry_action_on_server_error(
                            error_text=e.error_text,
                            state=state,
                            battle_room=battle_room,
                            battle_stream_store=env.get_battle_stream_store(),
                        )

                        if retry_action is None:
                            logging.error(
                                f"Agent declined to retry after server error: {e.error_text}"
                            )
                            raise

                        action = retry_action
                        server_error_retries += 1
                        logging.info(
                            f"Retrying with new action (attempt {server_error_retries}/{FLAGS.server_error_retries}): {action}"
                        )

                        if server_error_retries >= FLAGS.server_error_retries:
                            logging.error(
                                f"Exhausted all {FLAGS.server_error_retries} retries for server error"
                            )
                            raise

            logging.info(f"Battle {battle_room} ended after {turn_count} turns")
            if isinstance(agent, ZeroShotAgent):
                await agent.cleanup_battle(battle_room)

            opponent_username = None
            if state.our_player_id:
                opponent_id = "p2" if state.our_player_id == "p1" else "p1"
                opponent_username = state.player_usernames.get(opponent_id)

            if state.winner is None:
                logging.info("Result: Tie")
                if opponent_username:
                    stats_tracker.record_battle(opponent_username, won=False, tied=True)
            elif state.winner == username:
                logging.info("Result: Victory!")
                if opponent_username:
                    stats_tracker.record_battle(opponent_username, won=True)
            else:
                logging.info(f"Result: Defeat - {state.winner} won")
                if opponent_username:
                    stats_tracker.record_battle(opponent_username, won=False)

            if opponent_username:
                stats = stats_tracker.get_stats(opponent_username)
                if stats:
                    logging.info(f"Stats vs {opponent_username}:")
                    logging.info(
                        f"  Record: {stats.wins}W-{stats.losses}L-{stats.ties}T ({stats.total_battles} battles)"
                    )
                    logging.info(f"  Win %: {stats.win_percentage:.1f}%")

            if logger:
                logger.close()

            # Reload random team if team_index was not specified
            if FLAGS.team_index is None:
                logging.info("Loading new random team for next battle...")
                team_data = team_loader.load_team(team_index=None)
                challenge_handler.update_team(team_data)
                logging.info(f"New team loaded (length {len(team_data)})")

            logging.info(f"=== End of Battle {battle_room} #{battle_count} ===\n")

    except KeyboardInterrupt:
        logging.info("Interrupted by user")
    except Exception as e:
        logging.error(f"Error during battle: {e}", exc_info=True)
    finally:
        await client.disconnect()
        logging.info("Disconnected from server")


def main(argv: List[str]) -> None:
    """Entry point for the script."""

    logging.set_verbosity(logging.INFO)
    logging.info("Starting run_battle script")
    logging.info(f"Agent: {FLAGS.agent}")
    logging.info(f"Format: {FLAGS.format}")

    asyncio.run(run_battle())


if __name__ == "__main__":
    app.run(main)
