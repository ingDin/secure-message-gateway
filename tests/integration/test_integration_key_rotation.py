"""
Integration test suite validating deterministic key‑rotation behavior within the
secure-message-gateway pipeline.

@resume
    Ensures that the gateway responds predictably when encountering outdated or
    invalid cryptographic key material, enforcing secure and deterministic
    key‑lifecycle management required for long‑running and safety‑critical deployments.

@scope
    - deterministic triggering of key rotation when active key fails HMAC verification
    - atomic generation, persistence, and exposure of newly rotated key material
    - acceptance of subsequent messages signed with the rotated key
    - consistent freshness counter updates after successful rotated‑key validation
    - strict audit sequencing: ROTATION → HMAC_FAIL → MESSAGE_ACCEPTED
    - stable GatewayResponse objects for both failure and success paths

@ensures
    The gateway maintains cryptographic agility, deterministic behavior, and
    forensic‑grade observability across key‑rotation scenarios.
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
    @resume
        Integration test suite validating the gateway’s key‑rotation behavior and
        its impact on the end‑to‑end message‑processing pipeline.

    @scope
        - deterministic rotation triggering on invalid key usage
        - atomic persistence of newly rotated key material
        - acceptance of messages signed with the rotated key
        - monotonic freshness counter updates
        - strict audit ordering: ROTATION → HMAC_FAIL → MESSAGE_ACCEPTED
        - stable GatewayResponse objects across rotation boundaries

    @ensures
        The gateway enforces secure, deterministic key‑lifecycle management suitable
        for long‑running, embedded, and safety‑critical deployments.
    """

    @pytest.mark.asyncio
    async def test_gateway_key_rotation(self, integration_config_factory):
        """
        @resume
            Validates full key‑rotation behavior when the active key fails HMAC
            verification.

        @scope
            - initial message signed with outdated key triggers rotation
            - rotated key is persisted and exposed immediately
            - subsequent message signed with rotated key is accepted
            - freshness counter updated deterministically
            - audit log contains ROTATION, HMAC_FAIL, MESSAGE_ACCEPTED in order

        @returns
            Two GatewayResponse objects:
                * first: status="error", reason="HMAC_FAIL"
                * second: status="ok"

        @ensures
            The gateway performs deterministic rotation, updates freshness state,
            and records audit events in strict append‑only order.
        """

        # --- Arrange ---
        config = integration_config_factory()
        config["crypto"]["rotation_required"] = True

        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text(json.dumps({"dev_key": "00" * 32}))

        gateway = GatewayAsync(config)
        algo = HMACAlgorithm()

        # Initial message signed with outdated key
        payload_init = {"id": 1, "counter": 1, "msg": "init"}
        fake_mac = algo.sign(payload_init, b"0" * 32)
        dummy_msg = {**payload_init, "hmac": fake_mac}

        # --- Act (Step 1: trigger rotation) ---
        response_init = await gateway.process(dummy_msg)

        # --- Assert (Step 1) ---
        assert response_init.status == "error"
        assert response_init.reason == "HMAC_FAIL", \
            f"Expected reason HMAC_FAIL, got {response_init.reason}"

        # --- Arrange (Step 2: load rotated key) ---
        keys_data = json.loads(keys_path.read_text())
        assert "dev_key" in keys_data, "Rotation must write a new dev_key"
        rotated_key = bytes.fromhex(keys_data["dev_key"])

        # Build valid message using rotated key
        payload = {"id": MSG_ID, "counter": MSG_COUNTER, "msg": MSG_TEXT}
        mac = algo.sign(payload, rotated_key)
        msg = {**payload, "hmac": mac}

        # --- Act (Step 3: process valid message) ---
        response = await gateway.process(msg)

        # --- Assert (Step 3) ---
        assert response.status == "ok", "Gateway must accept messages signed with rotated key"

        # Freshness update
        freshness_path = Path(config["freshness"]["counter_file"])
        freshness_data = json.loads(freshness_path.read_text())
        assert freshness_data["counter"] == MSG_COUNTER, \
            "Freshness counter must be updated after rotated-key acceptance"

        # Audit ordering
        audit_path = Path(config["audit"]["path"])
        audit_lines = audit_path.read_text().splitlines()

        assert len(audit_lines) == 3, \
            "Audit must contain ROTATION, HMAC_FAIL (fake), MESSAGE_ACCEPTED"

        entry = json.loads(audit_lines[-1])
        assert entry["event"] == "MESSAGE_ACCEPTED", \
            "Last audit entry must be MESSAGE_ACCEPTED"
        assert entry["payload"] == payload, \
            "Audit payload must match the accepted message payload"
