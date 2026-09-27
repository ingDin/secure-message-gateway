"""
Integration test suite validating the full end-to-end message‑processing pipeline
of the secure-message-gateway in scenarios where key rotation is disabled.

@resume
    Ensures deterministic gateway behavior across all pipeline stages when
    operating with a static cryptographic key, validating baseline operational
    guarantees for environments where rotation is deferred or not required.

@scope
    - strict schema validation before cryptographic or freshness logic
    - deterministic key loading from persistent storage
    - successful HMAC verification for authentic messages
    - correct monotonic freshness counter updates and reliable persistence
    - append-only audit logging of acceptance events
    - stable, reproducible GatewayResponse objects

@ensures
    The gateway maintains predictable processing, state consistency, and
    forensic-grade observability under non-rotation conditions.
"""

import pytest
import os
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


VALID_KEY = os.urandom(32).hex()
MSG_ID = 1
MSG_COUNTER = 1
MSG_TEXT = "hello"


"""
Integration test suite validating the full end-to-end message‑processing pipeline
of the secure-message-gateway in scenarios where key rotation is disabled.

@resume
    Ensures deterministic gateway behavior across all pipeline stages when
    operating with a static cryptographic key, validating baseline operational
    guarantees for environments where rotation is deferred or not required.

@scope
    - strict schema validation before cryptographic or freshness logic
    - deterministic key loading from persistent storage
    - successful HMAC verification for authentic messages
    - correct monotonic freshness counter updates and reliable persistence
    - append-only audit logging of acceptance events
    - stable, reproducible GatewayResponse objects

@ensures
    The gateway maintains predictable processing, state consistency, and
    forensic-grade observability under non-rotation conditions.
"""

import pytest
import os
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


VALID_KEY = os.urandom(32).hex()
MSG_ID = 1
MSG_COUNTER = 1
MSG_TEXT = "hello"


class TestGatewayPipelineNoRotation:
    """
    @resume
        Integration test suite validating the full end‑to‑end message‑processing
        pipeline in a non‑rotation scenario.

    @scope
        - schema validation enforces structural integrity
        - deterministic key loading from persistent storage
        - HMAC verification confirms authenticity and integrity
        - freshness subsystem updates monotonic counter state reliably
        - audit subsystem records a single acceptance event
        - GatewayResponse object remains stable and predictable

    @ensures
        The gateway behaves deterministically and safely when rotation is disabled
        or deferred, preserving operational guarantees and forensic traceability.
    """

    @pytest.mark.asyncio
    async def test_gateway_integration(self, integration_config_factory):
        """
        @resume
            Validates the full gateway pipeline under static-key conditions.

        @scope
            - schema validation
            - key loading
            - HMAC verification
            - freshness update
            - audit logging
            - structured GatewayResponse

        @returns
            A GatewayResponse with status="ok" and correct freshness/audit state.

        @ensures
            The gateway processes valid messages deterministically and updates
            freshness and audit subsystems exactly once.
        """
        # --- Arrange ---
        config = integration_config_factory()

        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text(json.dumps({"dev_key": VALID_KEY}))

        gateway = GatewayAsync(config)
        algo = HMACAlgorithm()

        payload = {"id": MSG_ID, "counter": MSG_COUNTER, "msg": MSG_TEXT}
        mac = algo.sign(payload, bytes.fromhex(VALID_KEY))
        msg = {**payload, "hmac": mac}

        # --- Act ---
        response = await gateway.process(msg)

        # --- Assert: response ---
        assert response.status == "ok", "Gateway should accept a valid message"

        # --- Assert: freshness ---
        freshness_path = Path(config["freshness"]["counter_file"])
        freshness_data = json.loads(freshness_path.read_text())
        assert freshness_data["counter"] == MSG_COUNTER, \
            "Freshness counter must be updated to the message counter"

        # --- Assert: audit ---
        audit_path = Path(config["audit"]["path"])
        audit_lines = audit_path.read_text().splitlines()
        assert len(audit_lines) == 1, "Audit log must contain exactly one entry"

        entry = json.loads(audit_lines[0])
        assert entry["event"] == "MESSAGE_ACCEPTED", "Audit must record acceptance"
        assert entry["payload"] == payload, "Audit payload must match the message payload"
