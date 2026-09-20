"""
Asynchronous message‑processing gateway.

Coordinates schema validation, HMAC verification, monotonic
freshness checks, and audit logging in a fully async pipeline.
"""

from __future__ import annotations
from typing import Any, Dict
from pathlib import Path

from secure_gateway.schema import validate_schema
from secure_gateway.crypto import get_hmac_key_async, verify_message_async
from secure_gateway.freshness import update_freshness_async
from secure_gateway.logger import AuditLoggerAsync
from secure_gateway.models import GatewayResponse
from secure_gateway.exceptions import (
    GatewayError,
    SchemaError,
    HMACError,
    FreshnessError,
)


class GatewayAsync:
    """
    Asynchronous security gateway.

    Pipeline:
        1. Schema validation (sync)
        2. HMAC verification (async)
        3. Freshness check (async)
        4. Audit logging (async)
        5. Structured response
    """

    def __init__(self, config_dir: Path, log_path: Path):
        self.config_dir = config_dir
        self.logger = AuditLoggerAsync(log_path)

    # ---------------------------------------------------------
    # Main entry point for processing a message.
    # ---------------------------------------------------------
    async def process(self, raw: Dict[str, Any]) -> GatewayResponse:
        try:
            # 1. Schema validation (sync)
            validate_schema(raw)

            # 2. HMAC verification (async)
            key = await get_hmac_key_async(self.config_dir)
            payload = {
                "id": raw["id"],
                "counter": raw["counter"],
                "msg": raw["msg"],
            }
            await verify_message_async(payload, key, raw["hmac"])

            # 3. Freshness check (async)
            counter_path = self.config_dir / "freshness.json"
            await update_freshness_async(counter_path, raw["counter"])

            # 4. Audit logging (async)
            await self.logger.log_event("MESSAGE_ACCEPTED", payload)

            # 5. Structured response
            return GatewayResponse(status="ok")

        except SchemaError as exc:
            await self.logger.log_event("SCHEMA_FAIL", {"error": str(exc)})
            return GatewayResponse(status="error", reason="SCHEMA_FAIL")

        except HMACError as exc:
            await self.logger.log_event("HMAC_FAIL", {"error": str(exc)})
            return GatewayResponse(status="error", reason="HMAC_FAIL")

        except FreshnessError as exc:
            await self.logger.log_event("FRESHNESS_FAIL", {"error": str(exc)})
            return GatewayResponse(status="error", reason="FRESHNESS_FAIL")

        except GatewayError as exc:
            await self.logger.log_event("GATEWAY_ERROR", {"error": str(exc)})
            return GatewayResponse(status="error", reason="GATEWAY_ERROR")
