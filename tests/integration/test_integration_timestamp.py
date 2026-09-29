"""
@summary
Integration tests validating deterministic timestamp behaviour across the
secure-message-gateway pipeline.

These tests ensure:
    - audit events use the injected clock deterministically
    - rotation events use the same deterministic timestamp source
    - timestamps are normalized (Z == +00:00)

All timestamps must originate exclusively from the injected clock (freezegun).
"""

import pytest
import json
from pathlib import Path
from freezegun import freeze_time
from datetime import datetime, timezone

from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


# ---------------------------------------------------------------------------
# Helper: normalize timestamps (Z == +00:00)
# ---------------------------------------------------------------------------

def normalize(ts: str) -> str:
    return datetime.fromisoformat(ts).astimezone(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# 1. Audit timestamp determinism
# ---------------------------------------------------------------------------

class TestIntegrationAuditTimestamp:
    """
    @resume
        Validates deterministic timestamps produced by audit logging.

    @scope
        - freeze time
        - send valid message
        - audit entry timestamp must match frozen time (normalized)

    @ensures
        Audit logging remains fully deterministic and testable.
    """

    @pytest.mark.asyncio
    async def test_audit_timestamp_determinism(self, integration_config_factory):
        # --- Arrange ---
        frozen = "2035-01-01T12:00:00Z"

        with freeze_time(frozen):
            config = integration_config_factory()
            gateway = GatewayAsync(config)
            algo = HMACAlgorithm()

            keys_path = Path(config["crypto"]["keys_file"])
            keys_path.write_text(json.dumps({"dev_key": "aa" * 32}))
            key = bytes.fromhex("aa" * 32)

            payload = {"id": 1, "counter": 0, "msg": "hello"}
            mac = algo.sign(payload, key)
            msg = {**payload, "hmac": mac}

            # --- Act ---
            await gateway.process(msg)

            # --- Assert ---
            audit_path = Path(config["audit"]["path"])
            last = json.loads(audit_path.read_text().splitlines()[-1])

            assert normalize(last["timestamp"]) == normalize(frozen)


# ---------------------------------------------------------------------------
# 2. Rotation timestamp determinism
# ---------------------------------------------------------------------------

class TestIntegrationRotationTimestamp:
    """
    @resume
        Validates deterministic timestamps for key rotation events.

    @scope
        - freeze time
        - force rotation_required = true
        - first message triggers rotation
        - rotation event timestamp must match frozen time (normalized)

    @ensures
        Key rotation events remain fully deterministic and auditable.
    """

    @pytest.mark.asyncio
    async def test_rotation_timestamp_determinism(self, integration_config_factory):
        # --- Arrange ---
        frozen = "2040-05-10T08:30:00Z"

        with freeze_time(frozen):
            config = integration_config_factory()
            config["crypto"]["rotation_required"] = True

            gateway = GatewayAsync(config)
            algo = HMACAlgorithm()

            keys_path = Path(config["crypto"]["keys_file"])
            keys_path.write_text(json.dumps({"dev_key": "00" * 32}))
            key = bytes.fromhex("00" * 32)

            payload = {"id": 1, "counter": 0, "msg": "init"}
            mac = algo.sign(payload, key)
            msg = {**payload, "hmac": mac}

            # --- Act ---
            await gateway.process(msg)

            # --- Assert ---
            audit_path = Path(config["audit"]["path"])
            events = [json.loads(line) for line in audit_path.read_text().splitlines()]

            rotation_event = events[0]

            assert rotation_event["event"] == "ROTATION"
            assert normalize(rotation_event["timestamp"]) == normalize(frozen)
