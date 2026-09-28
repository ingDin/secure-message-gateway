"""
@summary
Asynchronous freshness enforcement subsystem for the secure-message-gateway.
Manages the monotonic counter used for replay protection and applies all
freshness rules defined in `config.json`.

Supports deterministic config-driven bootstrap:

Bootstrap modes:
- Existing freshness.json → load stored counter
- initial_counter == "auto" → first valid message defines counter
- initial_counter numeric → write initial counter immediately

Optional startup behavior:
- reset_on_start == true → delete freshness.json at startup and force bootstrap

Enforced rules after bootstrap:
- strict monotonic progression
- minimum increment
- maximum increment (optional rejection)
- drift constraints

All violations raise FreshnessError for deterministic, auditable behavior.
"""

import json
from pathlib import Path
import aiofiles

from secure_gateway.exceptions import FreshnessError


class FreshnessManager:
    """
    @summary
    Provides asynchronous loading, bootstrap initialization, validation,
    and updating of the gateway's monotonic freshness counter.

    Startup behavior:
        - If reset_on_start == true → delete freshness.json and force bootstrap
        - Else:
            * If freshness.json exists → load counter lazily
            * If initial_counter == "auto" → first message defines counter
            * If initial_counter numeric → initialize counter immediately

    After bootstrap, all freshness rules are enforced strictly.
    """

    def __init__(self, counter_path: Path, config: dict) -> None:
        self.counter_path = counter_path
        self.cfg = config["freshness"]

        self.initial = self.cfg.get("initial_counter", "auto")
        self.reset_on_start = self.cfg.get("reset_on_start", False)

        self.counter = None

        # Reset mode
        if self.reset_on_start and self.counter_path.exists():
            try:
                self.counter_path.unlink()
            except OSError as exc:
                raise FreshnessError(
                    f"Failed to reset freshness state: {exc}"
                ) from exc

    # ----------------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------------

    async def _load_counter(self) -> int:
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

    async def _write_counter(self, value: int) -> None:
        async with aiofiles.open(self.counter_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps({"counter": value}))

    # ----------------------------------------------------------------------
    # Public API: bootstrap
    # ----------------------------------------------------------------------

    async def bootstrap_async(self, incoming: int) -> None:
        """
        @summary
        Perform deterministic bootstrap initialization.

        Behavior:
        - If freshness.json exists → load counter
        - Else:
            * initial_counter == "auto" → use incoming
            * initial_counter numeric → use configured value
        """
        # File exists → load stored counter
        if self.counter_path.exists():
            self.counter = await self._load_counter()
            return

        # No file → config-driven bootstrap
        if self.initial == "auto":
            self.counter = incoming
        else:
            self.counter = int(self.initial)

        await self._write_counter(self.counter)

    # ----------------------------------------------------------------------
    # Public API: rule validation
    # ----------------------------------------------------------------------

    def validate_rules(self, incoming: int) -> None:
        """
        @summary
        Validate monotonic freshness rules after bootstrap.
        """
        last = self.counter
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

    # ----------------------------------------------------------------------
    # Public API: orchestrator
    # ----------------------------------------------------------------------

    async def validate_and_update_async(self, incoming: int) -> None:
        """
        @summary
        Orchestrate bootstrap + rule validation + persistence.
        """

        # 1. Bootstrap if needed
        if self.counter is None:
            await self.bootstrap_async(incoming)
            return

        # 2. Validate rules
        self.validate_rules(incoming)

        # 3. Persist updated counter
        self.counter = incoming
        await self._write_counter(incoming)
