"""
Integration test suite for audit ordering within the secure-message-gateway pipeline.

@resume
    Validates deterministic audit sequencing under cryptographic failure conditions,
    ensuring that audit events reflect strict pipeline ordering and fail-fast semantics.

@scope
    - strict ordering of audit events
    - deterministic behavior under early-stage cryptographic failures
    - prevention of downstream pipeline execution once failure is detected
    - append-only audit semantics without nondeterministic ordering

@ensures
    The audit subsystem provides forensic-grade traceability, compliance alignment,
    and deterministic observability required for safety-critical message validation.
"""

import pytest
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync


class TestAuditOrdering:
    """
    @resume
        Integration test suite validating deterministic audit sequencing within
        the secure-message-gateway pipeline.

    @scope
        - audit events emitted strictly according to pipeline execution semantics
        - early cryptographic failures produce a single, stable audit entry
        - downstream components (freshness, rotation, persistence) do not execute
          once a failure is detected
        - append-only audit behavior preserved under error conditions

    @ensures
        The gateway maintains deterministic audit ordering, ensuring reliable
        forensic traceability and compliance-grade observability.
    """

    @pytest.mark.asyncio
    async def test_audit_ordering(self, integration_config_factory):
        """
        @resume
            Validates audit ordering when the gateway encounters an invalid HMAC.

        @scope
            - invalid HMAC triggers immediate failure
            - pipeline halts before freshness or persistence logic
            - audit log contains exactly one event: "HMAC_FAIL"

        @returns
            A GatewayResponse with status="error" and reason="HMAC_FAIL".

        @ensures
            The audit subsystem records a single deterministic event reflecting
            the cryptographic failure, preserving strict append-only semantics.
        """

        # --- Arrange ---
        config = integration_config_factory()
        gateway = GatewayAsync(config)

        # Invalid HMAC payload
        payload = {"id": 1, "counter": 1, "msg": "bad", "hmac": "invalid"}

        # --- Act ---
        r = await gateway.process(payload)

        # --- Assert ---
        assert r.status == "error"
        assert r.reason == "HMAC_FAIL"

        audit_path = Path(config["audit"]["path"])
        events = [json.loads(line)["event"] for line in audit_path.read_text().splitlines()]
        assert events == ["HMAC_FAIL"]
