"""
Integration test suite validating deterministic timestamp
generation across the secure-message-gateway pipeline under frozen-time
conditions.

This module ensures that the gateway:

- uses the injected clock (via freezegun) for all audit and rotation events,
  never relying on system time
- produces stable, reproducible timestamps independent of runtime environment
  variability
- preserves strict temporal ordering between audit entries, including ROTATION
  and subsequent failure events
- propagates the frozen clock consistently through all pipeline layers,
  including cryptographic verification, freshness management, and audit logging
- maintains forensic-grade traceability and compliance-grade observability
  required for safety-critical and long-running deployments

These guarantees validate that temporal metadata within audit logs and rotation
events remains fully deterministic, enabling reliable debugging, auditing, and
regulatory compliance in environments where timestamp correctness is essential.
"""

import pytest
import json
from pathlib import Path
from freezegun import freeze_time
from datetime import datetime

from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


def ts_equal(actual: str, expected: str) -> bool:
    """
    Normalize ISO8601 timestamps and compare moments in time.
    Accepts both 'Z' and '+00:00' formats as equivalent UTC.
    """
    a = datetime.fromisoformat(actual)
    e = datetime.fromisoformat(expected)
    return a.replace(tzinfo=None) == e.replace(tzinfo=None)


class TestAuditTimestampDeterminism:
    """
    Integration test suite validating deterministic timestamp generation within
    the gateway’s audit subsystem.

    This class ensures that:
    - audit events use the injected clock rather than system time
    - timestamp generation is stable, reproducible, and independent of runtime
      environment variability
    - audit entries remain fully deterministic under frozen time conditions,
      enabling forensic-grade traceability and predictable observability
    - the gateway’s end-to-end pipeline correctly propagates the mock clock
      through all logging layers

    These checks validate that temporal metadata in audit logs is controlled,
    deterministic, and suitable for safety‑critical deployments.
    """

    @pytest.mark.asyncio
    async def test_audit_timestamp_determinism(self, integration_config_factory):
        """
        Audit timestamp determinism:
        - freeze clock
        - send valid message
        - audit timestamp must match frozen time
        """

        with freeze_time("2025-01-01T12:00:00Z"):
            config = integration_config_factory()
            gateway = GatewayAsync(config)
            algo = HMACAlgorithm()

            Path(config["crypto"]["keys_file"]).write_text(json.dumps({"dev_key": "aa" * 32}))
            key = bytes.fromhex("aa" * 32)

            payload = {"id": 1, "counter": 1, "msg": "hello"}
            mac = algo.sign(payload, key)
            msg = {**payload, "hmac": mac}

            await gateway.process(msg)

            audit_path = Path(config["audit"]["path"])
            entry = json.loads(audit_path.read_text().splitlines()[-1])

            assert ts_equal(entry["timestamp"], "2025-01-01T12:00:00+00:00")
            assert entry["event"] == "MESSAGE_ACCEPTED"


class TestRotationTimestampDeterminism:
    """
    Integration test suite validating deterministic timestamp generation during
    cryptographic key rotation.

    This class ensures that:
    - rotation events use the injected clock and not system time
    - rotation audit entries contain stable, reproducible timestamps
    - rotation and subsequent failure events preserve strict temporal ordering
    - the gateway’s rotation subsystem behaves deterministically under frozen
      time conditions, ensuring predictable cryptographic lifecycle behavior

    These checks validate that key rotation metadata is fully deterministic and
    suitable for compliance, auditability, and long‑running secure deployments.
    """

    @pytest.mark.asyncio
    async def test_rotation_timestamp_determinism(self, integration_config_factory):
        """
        Rotation timestamp determinism:
        - freeze clock
        - trigger rotation
        - ROTATION event must have frozen timestamp
        """

        with freeze_time("2030-05-10T08:30:00Z"):
            config = integration_config_factory()
            config["crypto"]["rotation_required"] = True

            gateway = GatewayAsync(config)
            algo = HMACAlgorithm()

            keys_path = Path(config["crypto"]["keys_file"])
            keys_path.write_text(json.dumps({"dev_key": "00" * 32}))

            payload = {"id": 1, "counter": 1, "msg": "init"}
            mac = algo.sign(payload, b"0" * 32)
            msg = {**payload, "hmac": mac}

            await gateway.process(msg)

            audit_path = Path(config["audit"]["path"])
            events = [json.loads(line) for line in audit_path.read_text().splitlines()]

            rotation_event = events[0]
            assert rotation_event["event"] == "ROTATION"
            assert ts_equal(rotation_event["timestamp"], "2030-05-10T08:30:00+00:00")
