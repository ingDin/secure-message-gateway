"""
Integration test suite validating deterministic schema‑failure behavior within
the secure-message-gateway pipeline.

@resume
    Ensures that the gateway rejects structurally invalid messages before any
    cryptographic or freshness logic executes, enforcing strict schema‑validation
    guarantees required for safety‑critical deployments.

@scope
    - detection of missing mandatory fields and structural violations
    - deterministic `SCHEMA_FAIL` response for malformed payloads
    - fail-fast semantics preventing downstream pipeline execution
    - append-only audit logging of schema failures
    - predictable behavior under malformed input conditions

@ensures
    Only structurally valid messages enter cryptographic and stateful subsystems,
    preserving operational safety, observability, and forensic-grade traceability.
"""

import pytest
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync


class TestSchemaFailure:
    """
    @resume
        Integration test suite validating strict schema‑validation guarantees within
        the gateway’s message‑processing pipeline.

    @scope
        - deterministic rejection of messages missing required fields
        - schema validation as the first immutable gate in the pipeline
        - stable `SCHEMA_FAIL` signaling for structural violations
        - append-only audit logging of schema failures
        - strict separation between schema validation and downstream logic

    @ensures
        The gateway enforces structural correctness rigorously, ensuring that only
        valid messages reach cryptographic and freshness subsystems.
    """

    @pytest.mark.asyncio
    async def test_schema_failure(self, integration_config_factory):
        """
        @resume
            Validates gateway behavior when incoming message violates schema rules.

        @scope
            - missing required fields (`msg`, `hmac`)
            - deterministic `SCHEMA_FAIL` response
            - correct audit logging of failure event

        @returns
            A GatewayResponse with status="error" and reason="SCHEMA_FAIL".

        @ensures
            The gateway halts processing immediately upon schema violation and
            records the failure as the final append-only audit event.
        """

        # --- Arrange ---
        config = integration_config_factory()
        gateway = GatewayAsync(config)

        # Structurally invalid payload (missing msg + hmac)
        payload = {"id": 1, "counter": 1}

        # --- Act ---
        r = await gateway.process(payload)

        # --- Assert ---
        assert r.status == "error"
        assert r.reason == "SCHEMA_FAIL"

        audit_path = Path(config["audit"]["path"])
        last_event = json.loads(audit_path.read_text().splitlines()[-1])
        assert last_event["event"] == "SCHEMA_FAIL"
