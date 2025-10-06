"""Example script to connect to a Pokemon Showdown server via WebSocket."""

import asyncio
import sys
from typing import List

from absl import app, flags, logging

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


async def run_client() -> None:
    """Connect to the Showdown server and print all received messages."""
    client = ShowdownClient()

    try:
        await client.connect(FLAGS.server_url, FLAGS.username, FLAGS.password)
        logging.info("Connected and authenticated. Listening for messages...")
        logging.info("Press Ctrl+C to disconnect")
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
