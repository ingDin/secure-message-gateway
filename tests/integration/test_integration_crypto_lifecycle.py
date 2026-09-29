"""
@resume
    Integration module validating the cryptographic lifecycle subsystems and
    the complete end‑to‑end gateway pipeline.

@scope
    - key rotation
    - archival of previous key material
    - generation of new cryptographic keys
    - audit logging of ROTATION events
    - HMAC verification after rotation
    - full successful pipeline execution (MESSAGE_ACCEPTED)

@ensures
    The gateway maintains cryptographic hygiene and operates correctly
    end‑to‑end under rotation, verification, and normal message flow.
"""

import pytest
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


class TestIntegrationKeyRotation:
    """
    @resume
        Validates deterministic key rotation and rejection of messages signed
        with stale key material.

    @scope
        - rotation_required=True
        - archival under dev_key_archived_<timestamp>
        - generation of a new key
        - HMAC_FAIL after rotation
        - audit events: ROTATION + HMAC_FAIL

    @ensures
        The gateway rotates keys correctly and rejects signatures produced
        with the previous key.
    """

    @pytest.mark.asyncio
    async def test_integration_key_rotation(self, integration_config_factory):
        # --- Arrange ---
        config = integration_config_factory()
        config["crypto"]["rotation_required"] = True

        gateway = GatewayAsync(config)
        algo = HMACAlgorithm()

        old_key_hex = "88" * 32
        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text(json.dumps({"dev_key": old_key_hex}))
        old_key = bytes.fromhex(old_key_hex)

        payload = {"id": 1, "counter": 1, "msg": "rotation_test"}
        mac = algo.sign(payload, old_key)
        msg = {**payload, "hmac": mac}

        # --- Act ---
        response = await gateway.process(msg)

        # --- Assert ---
        assert response.status == "error"
        assert response.reason == "HMAC_FAIL"

        archive_path = Path(config["crypto"]["keys_archive"])
        archive_data = json.loads(archive_path.read_text())

        archived = [
            (name, value)
            for name, value in archive_data.items()
            if name.startswith("dev_key_archived_")
        ]

        assert len(archived) == 1
        _, archived_value = archived[0]
        assert archived_value == old_key_hex

        new_keys = json.loads(keys_path.read_text())
        assert new_keys["dev_key"] != old_key_hex

        audit_path = Path(config["audit"]["path"])
        events = [json.loads(line) for line in audit_path.read_text().splitlines()]
        assert events[-2]["event"] == "ROTATION"
        assert events[-1]["event"] == "HMAC_FAIL"


class TestIntegrationPipelineSuccess:
    """
    @resume
        Validates the complete successful execution of the gateway pipeline.

    @scope
        - valid schema
        - valid HMAC signature
        - valid freshness progression
        - MESSAGE_ACCEPTED signalling
        - audit logging of accepted messages

    @ensures
        The gateway processes authentic, fresh messages correctly and produces
        deterministic audit output.
    """

    @pytest.mark.asyncio
    async def test_integration_pipeline_success(self, integration_config_factory):
        # --- Arrange ---
        config = integration_config_factory()
        gateway = GatewayAsync(config)
        algo = HMACAlgorithm()

        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text(json.dumps({"dev_key": "77" * 32}))
        key = bytes.fromhex("77" * 32)

        payload1 = {"id": 1, "counter": 1, "msg": "bootstrap"}
        mac1 = algo.sign(payload1, key)
        msg1 = {**payload1, "hmac": mac1}

        payload2 = {"id": 2, "counter": 3, "msg": "valid"}
        mac2 = algo.sign(payload2, key)
        msg2 = {**payload2, "hmac": mac2}

        # --- Act ---
        r1 = await gateway.process(msg1)
        r2 = await gateway.process(msg2)

        # --- Assert ---
        assert r1.status == "ok"
        assert r2.status == "ok"

        audit_path = Path(config["audit"]["path"])
        last = json.loads(audit_path.read_text().splitlines()[-1])
        assert last["event"] == "MESSAGE_ACCEPTED"
