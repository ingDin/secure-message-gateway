"""
@summary
Asynchronous message‑processing gateway responsible for validating, authenticating,
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
    Asynchronous security gateway implementing the full message‑processing pipeline.

    Pipeline stages:
        1. Schema validation
        2. Key rotation (if required)
        3. Crypto key loading
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

    async def process(self, raw: Dict[str, Any]) -> GatewayResponse:
        """
        @summary
        Process an incoming message through the full security pipeline.

        @parameters
        raw : dict
            Incoming message containing:
            - id
            - counter
            - msg
            - hmac

        @returns
        GatewayResponse
            Structured response indicating success or deterministic failure.

        @raises
        SchemaError
            If message structure or required fields are invalid.
        HMACError
            If signature verification fails.
        FreshnessError
            If monotonic counter freshness rules are violated.
        GatewayError
            For any other deterministic gateway-level failure.

        @examples
        >>> response = await gateway.process({
        ...     "id": "abc",
        ...     "counter": 42,
        ...     "msg": "hello",
        ...     "hmac": "deadbeef"
        ... })
        """
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
            error_type = next(
                (code for exc_class, code in ERROR_MAP.items() if isinstance(exc, exc_class)),
                "UNKNOWN_ERROR"
            )

            await self.audit.log_event(error_type, {"error": str(exc)})

            return GatewayResponse(status="error", reason=error_type)

    async def _check_key_rotation(self) -> None:
        """
        @summary
        Determine whether cryptographic key rotation is required and perform
        rotation if necessary.

        @returns
        None

        @raises
        GatewayError
            If rotation fails or key archival cannot be read.

        @examples
        >>> await gateway._check_key_rotation()
        """
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
