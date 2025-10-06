"""Script to download and filter the pokechamp dataset from HuggingFace.

This script loads the milkkarten/pokechamp dataset, filters it by gamemode
and elo rating, and saves the filtered battle logs to a text file.
"""

import time
from typing import Any, Dict, List, Optional, cast

from absl import app, flags, logging
from datasets import IterableDataset, load_dataset

FLAGS = flags.FLAGS

flags.DEFINE_integer(
    "min_elo",
    0,
    "Minimum elo rating to filter (e.g., 1600)",
)

flags.DEFINE_string(
    "gamemode",
    "gen9ou",
    "Game mode to filter (e.g., gen9ou)",
)

flags.DEFINE_integer(
    "max_records",
    2000,
    "Maximum number of records to download",
)

flags.DEFINE_string(
    "output",
    f"/tmp/pokechamp_data_logs_{int(time.time())}.txt",
    "Output file path",
)


def parse_elo_range(elo_str: str) -> Optional[int]:
    """Parse elo range string and return the minimum value.

    Args:
        elo_str: Elo range string like "1600-1799", "800-999", or "1800+"

    Returns:
        The minimum elo value, or None if parsing fails
    """
    try:
        if elo_str.endswith("+"):
            return int(elo_str[:-1])
        min_elo_str = elo_str.split("-")[0]
        return int(min_elo_str)
    except (ValueError, IndexError):
        return None


def create_gamemode_filter(gamemode: str) -> Any:
    """Create a filter function for gamemode.

    Args:
        gamemode: The gamemode to filter for

    Returns:
        A filter function that checks if record matches gamemode
    """

    def filter_fn(record: Dict[str, Any]) -> bool:
        return record["gamemode"] == gamemode

    return filter_fn


def create_elo_filter(min_elo: int) -> Any:
    """Create a filter function for minimum elo.

    Args:
        min_elo: The minimum elo rating to filter for

    Returns:
        A filter function that checks if record meets minimum elo
    """

    def filter_fn(record: Dict[str, Any]) -> bool:
        elo_val = parse_elo_range(record["elo"])
        return elo_val is not None and elo_val >= min_elo

    return filter_fn


def create_combined_filter(gamemode: str, min_elo: int) -> Any:
    """Create a combined filter function for gamemode and elo.

    Args:
        gamemode: The gamemode to filter for
        min_elo: The minimum elo rating to filter for (0 = no filter)

    Returns:
        A filter function that checks both conditions
    """

    def filter_fn(record: Dict[str, Any]) -> bool:
        if record["gamemode"] != gamemode:
            return False
        if min_elo > 0:
            elo_val = parse_elo_range(record["elo"])
            return elo_val is not None and elo_val >= min_elo
        return True

    return filter_fn


def main(argv: List[str]) -> None:
    """Main function to download and filter pokechamp dataset."""
    logging.info("Streaming pokechamp dataset from HuggingFace...")
    ds: IterableDataset = cast(
        IterableDataset,
        load_dataset("milkkarten/pokechamp", split="train", streaming=True),
    )

    logging.info(
        "Applying filters: gamemode=%s, min_elo=%d, max_records=%d",
        FLAGS.gamemode,
        FLAGS.min_elo,
        FLAGS.max_records,
    )

    result: IterableDataset = ds.filter(
        create_combined_filter(FLAGS.gamemode, FLAGS.min_elo)
    )

    filtered_result: IterableDataset = result.take(FLAGS.max_records)

    logging.info("Saving to %s...", FLAGS.output)
    count = 0
    with open(FLAGS.output, "w") as f:
        for record in filtered_result:
            record_dict: Dict[str, Any] = record
            f.write(record_dict["text"] + "\n")
            count += 1
            if count % 100 == 0:
                logging.info("Processed %d records...", count)
            if count >= FLAGS.max_records:
                break

    logging.info("Done! Saved %d records to %s", count, FLAGS.output)


if __name__ == "__main__":
    app.run(main)
