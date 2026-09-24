"""
Integration tests for GatewayAsync.

Covers full pipeline:
- schema validation
- key rotation
- key loading
- HMAC verification
- freshness update
- audit logging
- structured response
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


# ---------------------------------------------------------------------------
# Test 1: Full pipeline without rotation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gateway_integration(integration_config_factory):
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


# ---------------------------------------------------------------------------
# Test 2: Full rotation pipeline
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gateway_key_rotation(integration_config_factory):
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

    # Gateway SHOULD NOT throw — it returns an error response
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

    # Last entry must be MESSAGE_ACCEPTED
    entry = json.loads(audit_lines[-1])
    assert entry["event"] == "MESSAGE_ACCEPTED", \
        "Last audit entry must be MESSAGE_ACCEPTED"
    assert entry["payload"] == payload, \
        "Audit payload must match the accepted message payload"
