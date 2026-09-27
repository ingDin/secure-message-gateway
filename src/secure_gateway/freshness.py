"""
@summary
Asynchronous freshness enforcement for the secure-message-gateway.
Manages the monotonic counter used for replay protection and applies all
freshness rules defined in `config.json`.

Enforced rules:
- monotonic progression
- minimum increment
- maximum increment
- drift constraints
- optional rejection of out-of-range increments

All failures raise `FreshnessError` for deterministic and auditable behavior.
"""

import json
from pathlib import Path
import aiofiles

from secure_gateway.exceptions import FreshnessError


class FreshnessManager:
    """
    @summary
    Provides asynchronous loading, validation, and updating of the gateway's
    monotonic counter stored in `freshness.json`.

    @parameters
    counter_path : Path
        Filesystem path to the freshness state file.
    config : dict
        Parsed gateway configuration containing the `freshness` section.

    @examples
    >>> fm = FreshnessManager(Path("freshness.json"), config)
    >>> await fm.validate_and_update_async(42)
    """

    def __init__(self, counter_path: Path, config: dict) -> None:
        self.counter_path = counter_path
        self.cfg = config["freshness"]

    async def load_async(self) -> int:
        """
        @summary
        Load the persisted monotonic counter from `freshness.json`.

        @returns
        int
            The last stored counter value.

        @raises
        FreshnessError
            If the file is missing, unreadable, corrupted, or contains an
            invalid counter value.

        @examples
        >>> last = await fm.load_async()
        """
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
        """
        @summary
        Persist the updated counter value to `freshness.json`.

        @parameters
        value : int
            The new monotonic counter value.

        @examples
        >>> await fm.store_async(100)
        """
        async with aiofiles.open(self.counter_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps({"counter": value}))

    async def validate_and_update_async(self, incoming: int) -> None:
        """
        @summary
        Validate the incoming counter against all freshness rules and update
        the persisted state if validation succeeds.

        @parameters
        incoming : int
            The counter value extracted from the incoming message.

        @raises
        FreshnessError
            If any freshness rule is violated:
            - replay detection (incoming < last)
            - increment too small
            - increment too large (optional rejection)
            - drift violation

        @examples
        >>> await fm.validate_and_update_async(42)
        """
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
