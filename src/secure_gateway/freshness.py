"""
Asynchronous monotonic counter management for replay protection.

Implements ALL freshness rules from config.json:
- monotonic counter
- min_increment
- max_increment
- max_drift
- reject_out_of_range
"""

import json
from pathlib import Path
import aiofiles

from secure_gateway.exceptions import FreshnessError


class FreshnessManager:
    """
    Manages a monotonic counter stored in freshness.json.

    Responsibilities:
    - async load of the counter
    - async store of updated counter
    - full freshness validation based on config.json
    """

    def __init__(self, counter_path: Path, config: dict) -> None:
        self.counter_path = counter_path
        self.cfg = config["freshness"]

    async def load_async(self) -> int:
        try:
            async with aiofiles.open(self.counter_path, "r", encoding="utf-8") as f:
                raw = await f.read()
                data = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise FreshnessError(f"Failed to load counter from {self.counter_path}") from exc

        if "counter" not in data:
            raise FreshnessError("Missing 'counter' field in freshness.json")

        try:
            return int(data["counter"])
        except (TypeError, ValueError) as exc:
            raise FreshnessError("Invalid 'counter' value in freshness.json") from exc

    async def store_async(self, value: int) -> None:
        async with aiofiles.open(self.counter_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps({"counter": value}))

    async def validate_and_update_async(self, incoming: int) -> None:
        last = await self.load_async()
        increment = incoming - last

        if incoming < last:
            raise FreshnessError(
                f"Replay detected: incoming={incoming}, last={last}"
            )

        if increment < self.cfg["min_increment"]:
            raise FreshnessError(
                f"Counter increment too small: increment={increment}, "
                f"min_increment={self.cfg['min_increment']}"
            )

        if increment > self.cfg["max_increment"]:
            if self.cfg["reject_out_of_range"]:
                raise FreshnessError(
                    f"Counter increment too large: increment={increment}, "
                    f"max_increment={self.cfg['max_increment']}"
                )

        if increment > self.cfg["max_drift"]:
            raise FreshnessError(
                f"Counter drift too large: increment={increment}, "
                f"max_drift={self.cfg['max_drift']}"
            )

        await self.store_async(incoming)
