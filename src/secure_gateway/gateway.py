# src/secure_gateway/gateway.py

from typing import Any, Dict
from pathlib import Path

from secure_gateway.schema import validate_schema
from secure_gateway.crypto import get_hmac_key, verify_message
from secure_gateway.freshness import update_freshness
from secure_gateway.logger import AuditLogger
from secure_gateway.models import IncomingMessage, GatewayResponse
from secure_gateway.exceptions import GatewayError, SchemaError, HMACError, FreshnessError


# ---------------------------------------------------------
# Gateway
# Orchestrates the full message-processing pipeline:
# 1. schema validation
# 2. HMAC verification
# 3. freshness check
# 4. audit logging
# 5. structured response
#
# Each step delegates to its own module, keeping gateway thin
# and focused on control flow rather than implementation details.
# ---------------------------------------------------------
class Gateway:
    def __init__(self, config_dir: Path, log_path: Path):
        self.config_dir = config_dir
        self.logger = AuditLogger(log_path)

    # ---------------------------------------------------------
    # Main entry point for processing a message.
    # Converts raw dict → DTO → pipeline → response.
    # ---------------------------------------------------------
    def process(self, raw: Dict[str, Any]) -> GatewayResponse:
        try:
            # 1. Schema validation
            validate_schema(raw)
            msg = IncomingMessage(**raw)

            # 2. HMAC verification
            key = get_hmac_key(self.config_dir)
            payload = {
                "id": msg.id,
                "counter": msg.counter,
                "msg": msg.msg,
            }
            verify_message(payload, key, msg.hmac)

            # 3. Freshness check
            counter_path = self.config_dir / "freshness.json"
            update_freshness(counter_path, msg.counter)

            # 4. Audit logging
            self.logger.log_event("MESSAGE_ACCEPTED", payload)

            # 5. Structured response
            return GatewayResponse(status="ok")

        except SchemaError as exc:
            self.logger.log_event("SCHEMA_FAIL", {"error": str(exc)})
            return GatewayResponse(status="error", reason="SCHEMA_FAIL")

        except HMACError as exc:
            self.logger.log_event("HMAC_FAIL", {"error": str(exc)})
            return GatewayResponse(status="error", reason="HMAC_FAIL")

        except FreshnessError as exc:
            self.logger.log_event("FRESHNESS_FAIL", {"error": str(exc)})
            return GatewayResponse(status="error", reason="FRESHNESS_FAIL")

        except GatewayError as exc:
            # Catch-all for unexpected gateway-level issues
            self.logger.log_event("GATEWAY_ERROR", {"error": str(exc)})
            return GatewayResponse(status="error", reason="GATEWAY_ERROR")
