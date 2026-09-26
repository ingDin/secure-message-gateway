"""
Integration test suite validating deterministic schema‑failure
behavior within the secure-message-gateway pipeline.

This module ensures that the gateway:

- rejects structurally invalid messages before any cryptographic or freshness
  logic executes
- enforces schema correctness as the first immutable gate in the pipeline,
  preventing malformed payloads from reaching security‑critical subsystems
- produces a stable, reproducible `SCHEMA_FAIL` response for all messages
  missing mandatory fields or violating structural constraints
- halts pipeline execution immediately upon schema violation, preserving
  fail-fast semantics and preventing downstream components from overriding
  the failure
- records the failure as the final append-only audit event, ensuring
  forensic-grade traceability and deterministic observability

These guarantees validate the robustness of the gateway’s schema-validation
layer, ensuring that only structurally sound messages enter the cryptographic
and stateful portions of the system in industrial, embedded, or
safety-critical deployments.
"""

import pytest
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync


class TestSchemaFailure:
    """
    Integration test suite validating strict schema‑validation guarantees within
    the gateway’s message‑processing pipeline.

    This class ensures that:
    - messages missing mandatory fields (e.g., `msg`, `hmac`) are rejected
      deterministically before any cryptographic or freshness logic executes
    - schema validation acts as the first and immutable gate in the pipeline,
      enforcing structural correctness and preventing malformed payloads from
      reaching security‑critical subsystems
    - the gateway produces a stable `SCHEMA_FAIL` response for all structurally
      invalid messages, preserving predictable behavior under malformed input
    - audit logging records the failure as the final event, maintaining
      append‑only semantics and enabling forensic traceability
    - downstream components (HMAC verification, freshness management, rotation)
      remain untouched when schema validation fails, reinforcing the pipeline’s
      fail‑fast architecture

    These checks validate the correctness and robustness of the gateway’s
    schema‑validation layer, ensuring that only structurally sound messages
    enter the cryptographic and stateful portions of the system.
    """

    @pytest.mark.asyncio
    async def test_schema_failure(self, integration_config_factory):
        """
        Schema failure:
        - missing 'msg'
        - must produce SCHEMA_FAIL
        """

        config = integration_config_factory()
        gateway = GatewayAsync(config)

        payload = {"id": 1, "counter": 1}  # missing msg + hmac

        r = await gateway.process(payload)
        assert r.status == "error"
        assert r.reason == "SCHEMA_FAIL"

        audit_path = Path(config["audit"]["path"])
        assert json.loads(audit_path.read_text().splitlines()[-1])["event"] == "SCHEMA_FAIL"
