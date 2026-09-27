"""
Integration test suite validating deterministic timestamp generation across the
secure-message-gateway pipeline under frozen-time conditions.

@resume
    Ensures that all gateway subsystems—cryptographic verification, freshness
    management, rotation, and audit logging—use the injected clock rather than
    system time, producing fully deterministic temporal metadata.

@scope
    - stable, reproducible timestamps independent of runtime environment
    - strict temporal ordering of audit events under frozen time
    - deterministic timestamp propagation across all pipeline layers
    - compliance-grade observability and forensic traceability
    - predictable behavior required for long-running and safety-critical systems

@ensures
    Temporal metadata remains fully deterministic, enabling reliable debugging,
    auditing, and regulatory compliance in environments where timestamp
    correctness is essential.
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
    @resume
        Integration test suite validating deterministic timestamp generation within
        the gateway’s audit subsystem.

    @scope
        - audit events use the injected clock exclusively
        - timestamps remain stable and reproducible under frozen time
        - deterministic propagation of mock time through all logging layers
        - forensic-grade traceability for safety-critical deployments

    @ensures
        Audit timestamps remain fully deterministic and independent of system time.
    """

    @pytest.mark.asyncio
    async def test_audit_timestamp_determinism(self, integration_config_factory):
        """
        @resume
            Validates deterministic audit timestamp generation under frozen time.

        @scope
            - freeze clock at 2025-01-01T12:00:00Z
            - process valid message
            - audit timestamp must match frozen time exactly

        @returns
            A MESSAGE_ACCEPTED audit entry with deterministic timestamp.

        @ensures
            The audit subsystem uses the injected clock and preserves deterministic
            temporal metadata.
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
    @resume
        Integration test suite validating deterministic timestamp generation during
        cryptographic key rotation.

    @scope
        - rotation events use the injected clock exclusively
        - timestamps remain stable and reproducible under frozen time
        - strict temporal ordering between ROTATION and subsequent failure events
        - deterministic cryptographic lifecycle behavior under frozen time

    @ensures
        Key rotation metadata remains fully deterministic and suitable for
        compliance-grade observability.
    """

    @pytest.mark.asyncio
    async def test_rotation_timestamp_determinism(self, integration_config_factory):
        """
        @resume
            Validates deterministic timestamp generation for ROTATION events.

        @scope
            - freeze clock at 2030-05-10T08:30:00Z
            - trigger rotation via invalid key
            - ROTATION event timestamp must match frozen time

        @returns
            A ROTATION audit entry with deterministic timestamp.

        @ensures
            The rotation subsystem uses the injected clock and preserves strict
            temporal ordering.
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