"""Main script for running multiple parallel Pokemon Showdown battles."""

import asyncio
import time
from queue import Queue
from typing import List

from absl import app, flags, logging

from python.agents.agent_registry import AgentRegistry
from python.battle.battle_coordinator import BattleCoordinator
from python.battle.battle_state_tracker import BattleStateTracker
from python.battle.message_router import MessageRouter
from python.battle.parallel_challenge_handler import ParallelChallengeHandler
from python.game.data.game_data import GameData
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

# Parallel battle settings
flags.DEFINE_integer(
    "battles_per_opponent",
    4,
    "Maximum number of concurrent battles per opponent (default: 4)",
)

flags.DEFINE_integer(
    "max_threads",
    8,
    "Maximum number of worker threads for agent decisions (default: 8)",
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


async def run_parallel_battles() -> None:
    """Main function to run multiple parallel battles with the specified agent."""
    try:
        agent = AgentRegistry.create_agent(FLAGS.agent)
    except ValueError as e:
        logging.error("%s", e)
        return

    username = FLAGS.username or generate_default_username(FLAGS.agent)
    game_data = GameData()
    client = ShowdownClient()

    # Track win/loss statistics per opponent
    from collections import defaultdict
    import threading

    opponent_stats: defaultdict[str, dict[str, int]] = defaultdict(
        lambda: {"wins": 0, "losses": 0, "ties": 0}
    )
    stats_lock = threading.Lock()

    try:
        # Connect to server
        await client.connect(FLAGS.server_url, username, FLAGS.password)
        logging.info(f"Connected successfully as {username} to {FLAGS.server_url}")

        # Load team
        team_loader = TeamLoader(format_name=FLAGS.format)
        team_data = team_loader.load_team(team_index=FLAGS.team_index)
        logging.info(f"Packed team (length {len(team_data)}): {team_data}")

        # Initialize parallel battle infrastructure
        message_router = MessageRouter(client)
        coordinator = BattleCoordinator(
            message_router=message_router,
            max_threads=FLAGS.max_threads,
            battles_per_opponent=FLAGS.battles_per_opponent,
        )
        challenge_handler = ParallelChallengeHandler(
            client=client,
            coordinator=coordinator,
            lobby_queue=message_router.get_lobby_queue(),
            format=FLAGS.format,
            opponent=FLAGS.opponent,
            challenge_timeout=FLAGS.challenge_timeout,
            team_data=team_data,
        )

        # Start message routing in background
        routing_task = asyncio.create_task(message_router.route_messages())

        logging.info(
            f"Starting parallel battle mode: {FLAGS.max_threads} threads, "
            f"{FLAGS.battles_per_opponent} battles per opponent"
        )

        # Main loop
        try:
            while client.is_connected:
                # Process lobby messages and check for new battles
                battle_room = await challenge_handler.process_lobby_messages()

                if battle_room:
                    # Extract opponent from battle room (format: battle-gen9ou-12345)
                    # We'll get the opponent from the first PlayerEvent
                    # For now, use a placeholder and update when we see the opponent
                    opponent = FLAGS.opponent or "unknown"

                    # Create battle tracker
                    logger = None
                    if FLAGS.log_events:
                        logger = BattleEventLogger(
                            FLAGS.agent, int(time.time()), battle_room
                        )

                    message_queue: Queue[str] = Queue()
                    tracker = BattleStateTracker(
                        client=client,
                        battle_room=battle_room,
                        agent=agent,
                        game_data=game_data,
                        username=username,
                        message_queue=message_queue,
                        logger=logger,
                    )

                    # Enable timer if requested
                    if FLAGS.enable_timer:
                        await client.send_message(f"{battle_room}|/timer on")

                    # Initialize battle
                    await tracker.initialize()

                    # Register with coordinator
                    coordinator.start_battle(battle_room, opponent, tracker)

                    challenge_handler.remove_pending_battle(battle_room)

                # Process moves for all active battles
                await coordinator.process_battle_moves()

                # Clean up completed battles
                for battle_room in coordinator.get_all_active_battles():
                    tracker = coordinator.get_battle_tracker(battle_room)
                    if tracker and tracker.is_complete():
                        result = coordinator.complete_battle(battle_room)
                        if result:
                            # Determine opponent and result
                            opponent_name = "Unknown"
                            # Try to extract opponent from battle room or use configured opponent
                            if FLAGS.opponent:
                                opponent_name = FLAGS.opponent
                            elif result.winner and result.winner != username:
                                opponent_name = result.winner

                            # Thread-safe stats update
                            with stats_lock:
                                # Update statistics (defaultdict auto-initializes)
                                if result.winner is None:
                                    opponent_stats[opponent_name]["ties"] += 1
                                    outcome = "Tie"
                                elif result.winner == username:
                                    opponent_stats[opponent_name]["wins"] += 1
                                    outcome = "Victory!"
                                else:
                                    opponent_stats[opponent_name]["losses"] += 1
                                    outcome = f"Defeat - {result.winner} won"

                                # Calculate statistics
                                stats = opponent_stats[opponent_name]
                                total = stats["wins"] + stats["losses"] + stats["ties"]
                                win_rate = (
                                    (stats["wins"] / total * 100) if total > 0 else 0.0
                                )

                            logging.info(
                                f"Battle {battle_room} completed: "
                                f"{outcome} after {result.turn_count} turns ({result.duration:.1f}s)"
                            )
                            logging.info(
                                f"Stats vs {opponent_name}: {stats['wins']}W-{stats['losses']}L-{stats['ties']}T "
                                f"({total} battles, {win_rate:.1f}% win rate)"
                            )

                            if tracker._logger:  # noqa: SLF001
                                tracker._logger.close()  # noqa: SLF001

                # Small delay to prevent tight loop
                await asyncio.sleep(0.1)

        except KeyboardInterrupt:
            logging.info("Interrupted by user")
        finally:
            # Clean shutdown
            message_router.stop()
            routing_task.cancel()
            try:
                await routing_task
            except asyncio.CancelledError:
                pass

            coordinator.shutdown(timeout=30.0)

    except Exception as e:
        logging.error(f"Error during parallel battles: {e}", exc_info=True)
    finally:
        await client.disconnect()
        logging.info("Disconnected from server")


def main(argv: List[str]) -> None:
    """Entry point for the script."""
    logging.set_verbosity(logging.INFO)
    logging.info("Starting parallel battle script")
    logging.info(f"Agent: {FLAGS.agent}")
    logging.info(f"Format: {FLAGS.format}")
    logging.info(f"Max threads: {FLAGS.max_threads}")
    logging.info(f"Battles per opponent: {FLAGS.battles_per_opponent}")

    asyncio.run(run_parallel_battles())


if __name__ == "__main__":
    app.run(main)
