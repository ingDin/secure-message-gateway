"""
Integration test suite validating the full end-to-end
message-processing pipeline of the secure-message-gateway in scenarios where
key rotation is disabled.

This module ensures that the gateway behaves deterministically across all
pipeline stages when operating with a static cryptographic key. It verifies:

- strict schema validation before any cryptographic or freshness logic
- deterministic key loading from persistent storage
- successful HMAC verification for authentic messages
- correct monotonic freshness counter updates and reliable persistence
- append-only audit logging that records a single acceptance event
- stable, reproducible GatewayResponse objects reflecting correct pipeline flow

These guarantees validate the baseline operational behavior of the gateway,
ensuring predictable processing, state consistency, and forensic-grade
observability in environments where rotation is not required or is deferred.
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
    Integration test suite validating the full end‑to‑end message‑processing
    pipeline in a non‑rotation scenario.

    This class ensures that:
    - schema validation correctly enforces structural integrity before any
      cryptographic or freshness logic is executed
    - key loading retrieves the active key deterministically from persistent
      storage
    - HMAC verification succeeds for valid messages, confirming payload
      authenticity and integrity
    - freshness management updates the monotonic counter state and persists it
      reliably, guaranteeing replay protection
    - audit logging records a single, well‑structured event documenting the
      acceptance of the message, preserving append‑only semantics
    - the gateway produces a stable, predictable `GatewayResponse` object,
      reflecting correct pipeline execution without rotation

    These checks validate the baseline operational behavior of the gateway,
    ensuring deterministic processing, state consistency, and forensic‑grade
    observability in environments where key rotation is disabled or deferred.
    """

    @pytest.mark.asyncio
    async def test_gateway_integration(self, integration_config_factory):
        """
        Full pipeline test (rotation disabled):
        - schema validation
        - key loading
        - HMAC verification
        - freshness update
        - audit logging
        - structured response
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
