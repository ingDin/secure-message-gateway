"""
@resume
    Modul de integrare care validează subsistemele critice de ciclu criptografic
    și flux complet al pipeline‑ului.

@scope
    - rotația cheilor
    - arhivarea cheilor vechi
    - generarea cheilor noi
    - audit logging pentru KEY_ROTATED
    - verificarea HMAC după rotație
    - flux complet de succes (MESSAGE_ACCEPTED)

@ensures
    Gateway-ul menține igiena criptografică și funcționează corect end‑to‑end.
"""

import pytest
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


class TestIntegrationKeyRotation:
    """
    @resume
        Validează rotația cheilor și respingerea mesajelor semnate cu cheia veche.

    @scope
        - rotation_required=True
        - arhivare sub dev_key_archived_<timestamp>
        - generare cheie nouă
        - HMAC_FAIL după rotație
        - audit KEY_ROTATED + HMAC_FAIL

    @ensures
        Gateway-ul rotește corect și respinge semnăturile vechi.
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

        freshness_path = Path(config["freshness"]["counter_file"])
        freshness_path.write_text(json.dumps({"counter": 10}))

        payload = {"id": 1, "counter": 10, "msg": "rotation_test"}
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
        Validează fluxul complet de succes al pipeline‑ului.

    @scope
        - schema validă
        - HMAC valid
        - freshness valid
        - MESSAGE_ACCEPTED
        - audit logging

    @ensures
        Gateway-ul funcționează corect end‑to‑end.
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

        freshness_path = Path(config["freshness"]["counter_file"])
        freshness_path.write_text(json.dumps({"counter": 10}))

        payload1 = {"id": 1, "counter": 10, "msg": "bootstrap"}
        mac1 = algo.sign(payload1, key)
        msg1 = {**payload1, "hmac": mac1}

        payload2 = {"id": 2, "counter": 12, "msg": "valid"}
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
