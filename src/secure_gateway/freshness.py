# src/secure_gateway/freshness.py

from pathlib import Path
import json
from typing import Any, Dict


# ---------------------------------------------------------
# Exception hierarchy for freshness / replay protection
# ---------------------------------------------------------
class FreshnessError(Exception):
    """Base exception for freshness-related errors."""


class CounterLoadError(FreshnessError):
    """Raised when counter cannot be loaded."""


class CounterReplayError(FreshnessError):
    """Raised when a replay or stale counter is detected."""


# ---------------------------------------------------------
# Internal loader: read monotonic counter from freshness.json
# Ensures file exists, JSON is valid, and counter is an integer
# ---------------------------------------------------------
def _load_counter(counter_path: Path) -> int:
    """
    Load monotonic counter from JSON file.

    :param counter_path: Path to freshness.json
    :return: integer counter
    :raises CounterLoadError: if file missing or invalid
    """
    try:
        with counter_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise CounterLoadError(f"Failed to load counter from {counter_path}") from exc

    if "counter" not in data:
        raise CounterLoadError("Missing 'counter' field in freshness.json")

    try:
        value = int(data["counter"])
    except (TypeError, ValueError) as exc:
        raise CounterLoadError("Invalid 'counter' value in freshness.json") from exc

    return value


# ---------------------------------------------------------
# Internal store: write updated monotonic counter to disk
# Used only after successful freshness verification
# ---------------------------------------------------------
def _store_counter(counter_path: Path, value: int) -> None:
    """
    Store updated monotonic counter.

    :param counter_path: Path to freshness.json
    :param value: new counter value
    """
    counter_path.write_text(
        json.dumps({"counter": value}),
        encoding="utf-8",
    )


# ---------------------------------------------------------
# Freshness check: ensures incoming counter is strictly increasing
# Prevents replay attacks and stale message injection
# ---------------------------------------------------------
def verify_freshness(counter: int, last_counter: int) -> None:
    """
    Verify monotonic counter freshness.

    :param counter: incoming message counter
    :param last_counter: stored monotonic counter
    :raises CounterReplayError: if counter <= last_counter
    """
    if counter <= last_counter:
        raise CounterReplayError(
            f"Replay detected: incoming={counter}, last={last_counter}"
        )


# ---------------------------------------------------------
# Full freshness pipeline:
# - load last counter
# - verify monotonicity
# - store updated counter
#
# This function is the public API used by the gateway.
# ---------------------------------------------------------
def update_freshness(counter_path: Path, incoming_counter: int) -> None:
    """
    Full freshness pipeline:
    - load last counter
    - verify monotonicity
    - store updated counter

    :param counter_path: Path to freshness.json
    :param incoming_counter: counter from message
    """
    last = _load_counter(counter_path)
    verify_freshness(incoming_counter, last)
    _store_counter(counter_path, incoming_counter)
