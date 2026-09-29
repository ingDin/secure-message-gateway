"""
@summary
Asynchronous message-processing gateway responsible for validating, authenticating,
and auditing incoming messages. The gateway coordinates all security subsystems:

- schema validation
- key rotation (based on config.json)
- cryptographic key loading
- HMAC verification
- freshness enforcement (via FreshnessManager)
- audit logging
- structured response generation

All processing steps are deterministic and produce auditable outcomes.
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
    KeyError,
)

ERROR_MAP = {
    SchemaError: "SCHEMA_FAIL",
    HMACError: "HMAC_FAIL",
    FreshnessError: "FRESHNESS_FAIL",
    GatewayError: "GATEWAY_ERROR",
}


class GatewayAsync:
    """
    @summary
    Asynchronous security gateway implementing the full message-processing pipeline.

    Pipeline stages:
        1. Schema validation
        2. Key rotation (if required)
        3. Crypto key loading (with automatic rotation on key failure)
        4. HMAC verification
        5. Freshness validation
        6. Audit logging
        7. Structured response generation

    @parameters
    config : dict
        Parsed gateway configuration containing crypto, freshness, audit,
        and environment settings.

    @examples
    >>> gateway = GatewayAsync(config)
    >>> response = await gateway.process(message)
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

        # Key name moved here
        self.key_name = f"{config['environment']}_key"

        # Base payload for rotation audit logs
        self.rotation_payload_base = {
            "key_name": self.key_name,
            "algorithm": self.algorithm.name,
        }

    async def process(self, raw: Dict[str, Any]) -> GatewayResponse:
        """
        @summary
        Process an incoming message through the full security pipeline.
        """
        try:
            # 1. Schema validation
            SchemaValidator.validate(raw)

            # 2. Interval-based rotation
            await self._check_key_rotation()

            # 3. Load crypto key with automatic rotation on key failure
            try:
                key = await self.algorithm.load_key_async(self.config)
            except KeyError:
                # rotation triggered by invalid/missing/corrupted key material
                await self.key_manager.rotate_async()

                rotation_payload = {
                    **self.rotation_payload_base,
                    "reason": "invalid_key_rotation",
                }
                await self.audit.log_event("ROTATION", rotation_payload)

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
            error_type = next(
                (code for exc_class, code in ERROR_MAP.items() if isinstance(exc, exc_class)),
                "UNKNOWN_ERROR",
            )

            await self.audit.log_event(error_type, {"error": str(exc)})
            return GatewayResponse(status="error", reason=error_type)

    async def _check_key_rotation(self) -> None:
        """
        @summary
        Determine whether cryptographic key rotation is required and perform
        rotation if necessary, based on the configured rotation interval and
        existing key archive.
        """
        cfg = self.config["crypto"]

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

        # First rotation
        if last_rotation is None:
            await self.key_manager.rotate_async()
            rotation_payload = {
                **self.rotation_payload_base,
                "reason": "first_rotation",
            }
            await self.audit.log_event("ROTATION", rotation_payload)
            return

        # Interval-based rotation
        if KeyManager.rotation_needed(self.config, last_rotation):
            await self.key_manager.rotate_async()
            rotation_payload = {
                **self.rotation_payload_base,
                "reason": "rotation_interval_expired",
            }
            await self.audit.log_event("ROTATION", rotation_payload)
