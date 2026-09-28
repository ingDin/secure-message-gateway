"""
@resume
    Integration module validating cryptographic integrity enforcement through
    deterministic HMAC verification.

@scope
    - invalid HMAC signatures
    - valid HMAC signatures
    - deterministic HMAC_FAIL and HMAC_OK signalling
    - audit logging of cryptographic events

@ensures
    Only authentic, untampered messages proceed to freshness validation.
"""

import pytest
import json
from pathlib import Path
from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


class TestIntegrationHMACInvalid:
    """
    @resume
        Validates rejection of messages with incorrect HMAC signatures.

    @scope
        - incorrect HMAC
        - deterministic HMAC_FAIL
        - audit logging

    @ensures
        Gateway halts before freshness execution.
    """

    @pytest.mark.asyncio
    async def test_integration_hmac_invalid(self, integration_config_factory):
        # --- Arrange ---
        config = integration_config_factory()
        gateway = GatewayAsync(config)
        algo = HMACAlgorithm()

        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text(json.dumps({"dev_key": "aa" * 32}))
        key = bytes.fromhex("aa" * 32)

        payload = {"id": 1, "counter": 5, "msg": "hello"}
        msg = {**payload, "hmac": "deadbeef"}

        # --- Act ---
        response = await gateway.process(msg)

        # --- Assert ---
        assert response.status == "error"
        assert response.reason == "HMAC_FAIL"

        audit_path = Path(config["audit"]["path"])
        last = json.loads(audit_path.read_text().splitlines()[-1])
        assert last["event"] == "HMAC_FAIL"


class TestIntegrationHMACValid:
    """
    @resume
        Validates acceptance of messages with correct HMAC signatures.

    @scope
        - correct HMAC
        - deterministic HMAC_OK
        - audit logging

    @ensures
        Gateway proceeds to freshness validation.
    """

    @pytest.mark.asyncio
    async def test_integration_hmac_valid(self, integration_config_factory):
        # --- Arrange ---
        config = integration_config_factory()
        gateway = GatewayAsync(config)
        algo = HMACAlgorithm()

        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text(json.dumps({"dev_key": "aa" * 32}))
        key = bytes.fromhex("aa" * 32)

        freshness_path = Path(config["freshness"]["counter_file"])
        freshness_path.write_text(json.dumps({"counter": 10}))

        payload = {"id": 1, "counter": 10, "msg": "valid_hmac"}
        mac = algo.sign(payload, key)
        msg = {**payload, "hmac": mac}

        # --- Act ---
        response = await gateway.process(msg)

        # --- Assert ---
        assert response.status == "ok"
        assert response.reason is None

        audit_path = Path(config["audit"]["path"])
        events = [json.loads(line) for line in audit_path.read_text().splitlines()]

        # Nu trebuie să existe HMAC_FAIL
        assert not any(e["event"] == "HMAC_FAIL" for e in events)

        # Ultimul eveniment trebuie să fie MESSAGE_ACCEPTED
        assert events[-1]["event"] == "MESSAGE_ACCEPTED"

