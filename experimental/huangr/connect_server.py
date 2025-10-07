"""Example script to connect to a Pokemon Showdown server via WebSocket.

This script demonstrates three modes:
1. Raw mode: Print raw protocol messages (original behavior)
2. Event mode: Parse and print individual events with types
3. Batch mode: Use BattleStream to show event batching until decision points
"""

import asyncio
from typing import List

from absl import app, flags, logging

from python.game.events.battle_event import BattleEvent, RequestEvent, TurnEvent
from python.game.protocol.battle_stream import BattleStream
from python.game.protocol.message_parser import MessageParser
from python.game.protocol.showdown_client import ShowdownClient

FLAGS = flags.FLAGS
flags.DEFINE_string(
    "server_url",
    "ws://localhost:8000/showdown/websocket",
    "WebSocket URL of the Showdown server",
)
flags.DEFINE_string(
    "username",
    "PAC ShiningSnow",
    "Username to connect with",
)
flags.DEFINE_string(
    "password",
    "",
    "Password for the account (leave empty for guest)",
)
flags.DEFINE_enum(
    "mode",
    "batch",
    ["raw", "event", "batch"],
    "Display mode: raw (messages), event (parsed), batch (grouped)",
)
flags.DEFINE_enum(
    "batch_mode",
    "live",
    ["live", "replay"],
    "Batch mode: live (until request) or replay (until turn)",
)


def format_event(event: BattleEvent) -> str:
    """Format an event for display.

    Args:
        event: BattleEvent to format

    Returns:
        Formatted string representation
    """
    event_type = type(event).__name__

    if isinstance(event, RequestEvent):
        return f"🎯 {event_type} - DECISION POINT (Request JSON available)"
    elif isinstance(event, TurnEvent):
        return f"🔄 {event_type} - Turn {event.turn_number}"

    details = []
    if hasattr(event, "pokemon_name") and event.pokemon_name:
        details.append(f"pokemon={event.pokemon_name}")
    if hasattr(event, "move_name") and event.move_name:
        details.append(f"move={event.move_name}")
    if hasattr(event, "hp_current") and hasattr(event, "hp_max"):
        details.append(f"hp={event.hp_current}/{event.hp_max}")
    if hasattr(event, "weather") and event.weather:
        details.append(f"weather={event.weather}")

    detail_str = ", ".join(details) if details else ""
    return f"  {event_type}" + (f" ({detail_str})" if detail_str else "")


async def run_raw_mode(client: ShowdownClient) -> None:
    """Run in raw mode - print raw protocol messages."""
    logging.info("Running in RAW mode - showing raw protocol messages")
    while client.is_connected:
        try:
            message = await client.receive_message()
            print(f"\n{'='*80}")
            print(message)
            print(f"{'='*80}\n")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error("Error receiving message: %s", e)
            break


async def run_event_mode(client: ShowdownClient) -> None:
    """Run in event mode - parse and print individual events."""
    logging.info("Running in EVENT mode - showing parsed events")
    parser = MessageParser()

    while client.is_connected:
        try:
            message = await client.receive_message()
            if not message.strip():
                continue

            # Parse each line
            for line in message.split("\n"):
                if not line.strip():
                    continue

                event = parser.parse(line)
                print(format_event(event))

        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error("Error receiving message: %s", e)
            break


async def run_batch_mode(client: ShowdownClient) -> None:
    """Run in batch mode - use BattleStream to batch events."""
    logging.info(
        "Running in BATCH mode (%s) - showing event batches until decision points",
        FLAGS.batch_mode
    )

    stream = BattleStream(client, mode=FLAGS.batch_mode)
    batch_num = 0

    try:
        async for event_batch in stream:
            batch_num += 1
            print(f"\n{'='*80}")
            print(f"📦 BATCH #{batch_num} ({len(event_batch)} events)")
            print(f"{'='*80}")

            for event in event_batch:
                print(format_event(event))

            # Show decision point type
            last_event = event_batch[-1] if event_batch else None
            if isinstance(last_event, RequestEvent):
                print("\n💡 Batch ended at RequestEvent - agent should choose action")
            elif isinstance(last_event, TurnEvent):
                print(f"\n💡 Batch ended at TurnEvent {last_event.turn_number}")

            print()  # Extra line for readability

    except asyncio.CancelledError:
        logging.info("Batch mode cancelled")
    except StopAsyncIteration:
        logging.info("Battle stream ended")


async def run_client() -> None:
    """Connect to the Showdown server and display messages based on mode."""
    client = ShowdownClient()

    try:
        await client.connect(FLAGS.server_url, FLAGS.username, FLAGS.password)
        logging.info("Connected and authenticated. Listening for messages...")
        logging.info("Press Ctrl+C to disconnect")
        logging.info("Mode: %s", FLAGS.mode)

        if FLAGS.mode == "raw":
            await run_raw_mode(client)
        elif FLAGS.mode == "event":
            await run_event_mode(client)
        elif FLAGS.mode == "batch":
            await run_batch_mode(client)

    except KeyboardInterrupt:
        logging.info("Interrupted by user")
    except Exception as e:
        logging.error("Connection error: %s", e)
    finally:
        await client.disconnect()
        logging.info("Connection closed")


def main(argv: List[str]) -> None:
    asyncio.run(run_client())


if __name__ == "__main__":
    app.run(main)
