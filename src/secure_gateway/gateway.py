"""
Asynchronous message‑processing gateway.

Coordinates:
- schema validation
- key rotation (based on config.json)
- crypto key loading
- HMAC verification
- freshness rules (delegated to FreshnessManager)
- audit logging
- structured responses
"""

from __future__ import annotations
from typing import Any, Dict
from pathlib import Path
from datetime import datetime, timezone

from secure_gateway.schema import SchemaValidator
from secure_gateway.algorithms import ALGORITHM_REGISTRY
from secure_gateway.freshness import FreshnessManager
from secure_gateway.logger import AuditLogger
from secure_gateway.key_manager import KeyManager
from secure_gateway.key_loader import KeyFileStore
from secure_gateway.models import GatewayResponse

from secure_gateway.exceptions import (
    GatewayError,
    SchemaError,
    HMACError,
    FreshnessError,
)

ERROR_MAP = {
    SchemaError: "SCHEMA_FAIL",
    HMACError: "HMAC_FAIL",
    FreshnessError: "FRESHNESS_FAIL",
    GatewayError: "GATEWAY_ERROR",
}


class GatewayAsync:
    """
    Asynchronous security gateway.

    Pipeline:
        1. Schema validation
        2. Key rotation (if needed)
        3. Load crypto key
        4. HMAC verification
        5. Freshness checks
        6. Audit logging
        7. Structured response
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # Audit logger
        self.audit = AuditLogger(Path(config["audit"]["path"]))

        # Freshness manager
        freshness_path = Path(config["freshness"]["counter_file"])
        self.freshness = FreshnessManager(freshness_path, config)

        # Crypto algorithm
        algo_name = config["crypto"]["algorithm"]
        self.algorithm = ALGORITHM_REGISTRY.get(algo_name)

        # Key manager
        self.key_manager = KeyManager(config)

    # ---------------------------------------------------------
    # Main entry point
    # ---------------------------------------------------------
    async def process(self, raw: Dict[str, Any]) -> GatewayResponse:
        try:
            # 1. Schema validation
            SchemaValidator.validate(raw)

            # 2. Key rotation (if needed)
            await self._check_key_rotation()

            # 3. Load crypto key
            key = await self.algorithm.load_key_async(self.config)

            # 4. HMAC verification
            payload = {
                "id": raw["id"],
                "counter": raw["counter"],
                "msg": raw["msg"],
            }
            await self.algorithm.verify_async(payload, key, raw["hmac"])

            # 5. Freshness checks
            await self.freshness.validate_and_update_async(raw["counter"])

            # 6. Audit logging
            await self.audit.log_event("MESSAGE_ACCEPTED", payload)

            return GatewayResponse(status="ok")

        except Exception as exc:
            # Determine error type
            error_type = next(
                (code for exc_class, code in ERROR_MAP.items() if isinstance(exc, exc_class)),
                "UNKNOWN_ERROR"
            )

            await self.audit.log_event(error_type, {
                "error": str(exc),
                "exception_type": exc.__class__.__name__
            })

            return GatewayResponse(status="error", reason=error_type)

    # ---------------------------------------------------------
    # Key rotation logic
    # ---------------------------------------------------------
    async def _check_key_rotation(self) -> None:
        cfg = self.config["crypto"]
        key_name = f"{self.config['environment']}_key"

        if not cfg["rotation_required"]:
            return

        archive_path = Path(cfg["keys_archive"])
        last_rotation = None

        # Determine last rotation timestamp from archive
        if archive_path.exists():
            archive = await KeyFileStore.load_async(archive_path)
            if archive:
                last_key = list(archive.keys())[-1]
                timestamp = last_key.split("_archived_")[-1]
                last_rotation = datetime.fromisoformat(timestamp)

        rotation_payload = {
            "key_name": key_name,
            "algorithm": self.algorithm.name,
        }

        # First rotation
        if last_rotation is None:
            await self.key_manager.rotate_async()
            rotation_payload["reason"] = "first_rotation"
            await self.audit.log_event("ROTATION", rotation_payload)
            return

        # Interval-based rotation
        if KeyManager.rotation_needed(self.config, last_rotation):
            await self.key_manager.rotate_async()
            rotation_payload["reason"] = "rotation_interval_expired"
            await self.audit.log_event("ROTATION", rotation_payload)
