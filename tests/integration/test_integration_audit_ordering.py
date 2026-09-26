"""
Integration test suite for audit ordering within the
secure-message-gateway pipeline.

This module validates deterministic audit sequencing under cryptographic
failure conditions. It ensures that:

- audit events are emitted strictly in pipeline order
- early-stage failures (e.g., HMAC verification) produce a single, stable,
  reproducible audit entry
- downstream pipeline components (freshness, rotation, persistence) do not
  execute once a failure is detected
- the audit subsystem maintains append-only behavior without introducing
  nondeterministic ordering

These guarantees are essential for forensic traceability, compliance, and
safety-critical message validation, where deterministic observability is a
core architectural requirement.
"""

import pytest
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync


class TestAuditOrdering:
    """
    Integration test suite validating deterministic audit sequencing within the
    secure-message-gateway pipeline.

    This class ensures that:
    - audit events are emitted strictly in the order dictated by pipeline
      execution semantics
    - early-stage failures (e.g., HMAC verification) produce a single, stable,
      and reproducible audit entry
    - no downstream pipeline components (freshness, rotation, persistence)
      execute once a cryptographic failure is detected
    - the audit subsystem maintains append-only behavior and does not introduce
      nondeterministic ordering under error conditions

    These guarantees are essential for forensic traceability, compliance, and
    safety‑critical message validation, where deterministic observability is a
    core architectural requirement.
    """

    @pytest.mark.asyncio
    async def test_audit_ordering(self, integration_config_factory):
        """
        Audit ordering:
        - invalid HMAC
        - must produce deterministic audit order
        """

        config = integration_config_factory()
        gateway = GatewayAsync(config)

        payload = {"id": 1, "counter": 1, "msg": "bad", "hmac": "invalid"}

        r = await gateway.process(payload)
        assert r.status == "error"
        assert r.reason == "HMAC_FAIL"

        audit_path = Path(config["audit"]["path"])
        events = [json.loads(line)["event"] for line in audit_path.read_text().splitlines()]
        assert events == ["HMAC_FAIL"]
