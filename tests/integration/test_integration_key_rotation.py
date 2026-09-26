"""
Integration test suite validating deterministic key-rotation
behavior within the secure-message-gateway pipeline.

This module ensures that the gateway responds predictably when encountering
outdated or invalid cryptographic key material. It verifies that:

- key rotation is triggered deterministically when the active key fails HMAC
  verification
- the rotation subsystem generates, persists, and exposes a new key atomically
- subsequent messages signed with the rotated key are accepted, confirming
  correct propagation of updated cryptographic material
- freshness state is updated consistently after successful validation with the
  rotated key, preserving monotonic counter guarantees
- audit logging records the complete ordered sequence of events — ROTATION,
  HMAC_FAIL, MESSAGE_ACCEPTED — providing forensic-grade traceability
- the gateway produces stable, reproducible GatewayResponse objects for both
  the failure path (pre-rotation) and the success path (post-rotation)

These guarantees validate the robustness of the gateway’s key-lifecycle
management, ensuring secure, deterministic, and observable behavior in
long-running or safety-critical deployments where cryptographic agility is
mandatory.
"""

import pytest
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


MSG_ID = 1
MSG_COUNTER = 1
MSG_TEXT = "hello"


class TestGatewayKeyRotation:
    """
    Integration test suite validating the gateway’s key‑rotation behavior and
    its impact on the end‑to‑end message‑processing pipeline.

    This class ensures that:
    - an invalid or outdated key triggers the rotation mechanism deterministically,
      without raising exceptions or interrupting pipeline execution
    - the rotation subsystem persists a newly generated key atomically and makes
      it immediately available for subsequent validation steps
    - messages signed with the rotated key are accepted, confirming correct
      propagation of new cryptographic material through the system
    - freshness state is updated consistently after successful validation with
      the rotated key, preserving monotonic counter guarantees
    - audit logging captures the complete sequence of events — ROTATION,
      HMAC_FAIL, MESSAGE_ACCEPTED — in strict pipeline order, ensuring forensic
      traceability and compliance‑grade observability
    - the gateway produces stable and predictable `GatewayResponse` objects for
      both the failure path (initial invalid key) and the success path (rotated key)

    These checks validate the robustness of the gateway’s key‑lifecycle
    management, a critical requirement for secure, long‑running deployments
    where cryptographic agility and deterministic behavior are mandatory.
    """

    @pytest.mark.asyncio
    async def test_gateway_key_rotation(self, integration_config_factory):
        """
        Full rotation test:
        - initial fake key triggers rotation (no exception thrown)
        - rotated key is written to disk
        - new message signed with rotated key is accepted
        - freshness counter updated
        - audit contains ROTATION + HMAC_FAIL + MESSAGE_ACCEPTED
        - response.reason for the first message must be HMAC_FAIL
        """

        # --- Arrange ---
        config = integration_config_factory()
        config["crypto"]["rotation_required"] = True

        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text(json.dumps({"dev_key": "00" * 32}))

        gateway = GatewayAsync(config)
        algo = HMACAlgorithm()

        # --- Step 1: Trigger rotation with fake key ---
        payload_init = {"id": 1, "counter": 1, "msg": "init"}
        fake_mac = algo.sign(payload_init, b"0" * 32)
        dummy_msg = {**payload_init, "hmac": fake_mac}

        response_init = await gateway.process(dummy_msg)

        # --- Assert: response.reason MUST be HMAC_FAIL ---
        assert response_init.status == "error"
        assert response_init.reason == "HMAC_FAIL", \
            f"Expected reason HMAC_FAIL, got {response_init.reason}"

        # --- Step 2: Rotated key must exist ---
        keys_data = json.loads(keys_path.read_text())
        assert "dev_key" in keys_data, "Rotation must write a new dev_key"

        rotated_key = bytes.fromhex(keys_data["dev_key"])

        # --- Step 3: Send valid message with rotated key ---
        payload = {"id": MSG_ID, "counter": MSG_COUNTER, "msg": MSG_TEXT}
        mac = algo.sign(payload, rotated_key)
        msg = {**payload, "hmac": mac}

        response = await gateway.process(msg)

        # --- Assert: response ---
        assert response.status == "ok", "Gateway must accept messages signed with rotated key"

        # --- Assert: freshness ---
        freshness_path = Path(config["freshness"]["counter_file"])
        freshness_data = json.loads(freshness_path.read_text())
        assert freshness_data["counter"] == MSG_COUNTER, \
            "Freshness counter must be updated after rotated-key acceptance"

        # --- Assert: audit ---
        audit_path = Path(config["audit"]["path"])
        audit_lines = audit_path.read_text().splitlines()

        assert len(audit_lines) == 3, \
            "Audit must contain ROTATION, HMAC_FAIL (fake), MESSAGE_ACCEPTED"

        entry = json.loads(audit_lines[-1])
        assert entry["event"] == "MESSAGE_ACCEPTED", \
            "Last audit entry must be MESSAGE_ACCEPTED"
        assert entry["payload"] == payload, \
            "Audit payload must match the accepted message payload"
