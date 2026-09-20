"""
Asynchronous monotonic counter management for replay protection.

Provides non‑blocking load/store operations for freshness.json and
sync logic for verifying strictly increasing counters in the gateway.
"""

from pathlib import Path
import json
import asyncio
import aiofiles
from typing import Any, Dict

from secure_gateway.exceptions import FreshnessError


# ---------------------------------------------------------
# Async loader: read monotonic counter from freshness.json
# ---------------------------------------------------------
async def _load_counter_async(counter_path: Path) -> int:
    """
    Asynchronously load monotonic counter from JSON file.
    """
    try:
        async with aiofiles.open(counter_path, "r", encoding="utf-8") as f:
            raw = await f.read()
            data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise FreshnessError(f"Failed to load counter from {counter_path}") from exc

    if "counter" not in data:
        raise FreshnessError("Missing 'counter' field in freshness.json")

    try:
        value = int(data["counter"])
    except (TypeError, ValueError) as exc:
        raise FreshnessError("Invalid 'counter' value in freshness.json") from exc

    return value


# ---------------------------------------------------------
# Async store: write updated monotonic counter to disk
# ---------------------------------------------------------
async def _store_counter_async(counter_path: Path, value: int) -> None:
    """
    Asynchronously store updated monotonic counter.
    """
    async with aiofiles.open(counter_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps({"counter": value}))


# ---------------------------------------------------------
# Freshness check (sync logic)
# ---------------------------------------------------------
def verify_freshness(counter: int, last_counter: int) -> None:
    """
    Verify monotonic counter freshness.
    """
    if counter <= last_counter:
        raise FreshnessError(
            f"Replay detected: incoming={counter}, last={last_counter}"
        )


# ---------------------------------------------------------
# Full async freshness pipeline
# ---------------------------------------------------------
async def update_freshness_async(counter_path: Path, incoming_counter: int) -> None:
    """
    Full async freshness pipeline:
    - load last counter (async)
    - verify monotonicity (sync)
    - store updated counter (async)
    """
    last = await _load_counter_async(counter_path)
    verify_freshness(incoming_counter, last)
    await _store_counter_async(counter_path, incoming_counter)
