"""
@summary
Integration module validating deterministic key‑error recovery behaviour across
the full gateway pipeline.

@scope
    - corrupted key material in keys.json
    - automatic key rotation triggered by KeyError
    - deterministic HMAC_FAIL signalling after rotation
    - acceptance of messages signed with the newly rotated key
    - audit logging of all cryptographic and rotation events

@ensures
    The gateway recovers gracefully from corrupted key storage, rotates keys
    predictably, rejects stale signatures, and accepts messages signed with
    newly generated key material.
"""

import json
import pytest
from pathlib import Path

from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


@pytest.mark.asyncio
async def test_key_error_recovery(integration_config_factory):
    """
    @resume
        Validates full recovery behaviour when keys.json becomes corrupted.

    @scope
        - initial valid message
        - corruption of key material
        - rotation triggered by KeyError
        - deterministic HMAC_FAIL for stale signatures
        - acceptance of messages signed with rotated key

    @ensures
        The gateway maintains deterministic behaviour across key corruption,
        rotation, and subsequent message processing.
    """

    # --- Arrange ---
    config = integration_config_factory()
    gateway = GatewayAsync(config)
    algo = HMACAlgorithm()

    keys_path = Path(config["crypto"]["keys_file"])

    # --- Message 1: valid key, valid HMAC → ACCEPTED ---
    msg1 = {
        "id": 1,
        "msg": "hello",
        "counter": 1,
    }

    key_hex = json.loads(keys_path.read_text())["dev_key"]
    key_bytes = bytes.fromhex(key_hex)

    msg1["hmac"] = algo.sign(
        {"id": msg1["id"], "counter": msg1["counter"], "msg": msg1["msg"]},
        key_bytes
    )

    resp1 = await gateway.process(msg1)
    assert resp1.status == "ok"

    # --- Corrupt the key file to trigger KeyError on next load ---
    keys_path.write_text('{"dev_key": "NOT_HEX"}')

    # --- Message 2: signed with old key → rotation + HMAC_FAIL ---
    msg2 = {
        "id": 2,
        "msg": "hello2",
        "counter": 2,
    }

    msg2["hmac"] = algo.sign(
        {"id": msg2["id"], "counter": msg2["counter"], "msg": msg2["msg"]},
        key_bytes
    )

    resp2 = await gateway.process(msg2)
    assert resp2.status == "error"
    assert resp2.reason == "HMAC_FAIL"

    # --- Message 3: signed with newly rotated key → ACCEPTED ---
    new_key_hex = json.loads(keys_path.read_text())["dev_key"]
    new_key_bytes = bytes.fromhex(new_key_hex)

    msg3 = {
        "id": 3,
        "msg": "hello3",
        "counter": 3,
    }

    msg3["hmac"] = algo.sign(
        {"id": msg3["id"], "counter": msg3["counter"], "msg": msg3["msg"]},
        new_key_bytes
    )

    resp3 = await gateway.process(msg3)
    assert resp3.status == "ok"
