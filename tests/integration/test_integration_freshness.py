"""
@summary
Integration test suite for the secure-message-gateway freshness subsystem.

These tests reflect the REAL behavior of FreshnessManager:

    - If freshness.json exists → bootstrap loads the stored counter.
    - First message NEVER validates freshness rules.
    - Second message validates increment relative to stored counter.
    - Third message validates increment relative to updated counter.

All freshness violations must raise FRESHNESS_FAIL through gateway.process().
"""

import pytest
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


# ---------------------------------------------------------------------------
# Helper: send message
# ---------------------------------------------------------------------------

async def send(gateway, algo, key, counter, msg):
    payload = {"id": counter, "counter": counter, "msg": msg}
    mac = algo.sign(payload, key)
    return await gateway.process({**payload, "hmac": mac})


# ---------------------------------------------------------------------------
# 1. Increment = 0 → FAIL
# ---------------------------------------------------------------------------

class TestIntegrationFreshnessAbnormalIncrement:
    """
    @resume
        Validates abnormal increment (0) after bootstrap and one valid update.
    """

    @pytest.mark.asyncio
    async def test_increment_zero(self, integration_config_factory):
        # --- Arrange ---
        config = integration_config_factory()
        gateway = GatewayAsync(config)
        algo = HMACAlgorithm()

        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text(json.dumps({"dev_key": "11" * 32}))
        key = bytes.fromhex("11" * 32)

        freshness_path = Path(config["freshness"]["counter_file"])
        freshness_path.write_text(json.dumps({"counter": 0}))

        # --- Act ---
        await send(gateway, algo, key, 10, "bootstrap")       # bootstrap only
        await send(gateway, algo, key, 10, "first_update")    # valid increment
        response = await send(gateway, algo, key, 10, "zero_increment")  # increment=0

        # --- Assert ---
        assert response.status == "error"
        assert response.reason == "FRESHNESS_FAIL"


# ---------------------------------------------------------------------------
# 2. Replay (incoming < last) → FAIL
# ---------------------------------------------------------------------------

class TestIntegrationFreshnessReplay:
    """
    @resume
        Validates replay detection (incoming < last).
    """

    @pytest.mark.asyncio
    async def test_replay(self, integration_config_factory):
        # --- Arrange ---
        config = integration_config_factory()
        gateway = GatewayAsync(config)
        algo = HMACAlgorithm()

        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text(json.dumps({"dev_key": "22" * 32}))
        key = bytes.fromhex("22" * 32)

        freshness_path = Path(config["freshness"]["counter_file"])
        freshness_path.write_text(json.dumps({"counter": 0}))

        # --- Act ---
        await send(gateway, algo, key, 10, "bootstrap")
        await send(gateway, algo, key, 10, "first_update")
        response = await send(gateway, algo, key, 9, "replay")  # incoming < last

        # --- Assert ---
        assert response.status == "error"
        assert response.reason == "FRESHNESS_FAIL"


# ---------------------------------------------------------------------------
# 3. Drift (increment > max_drift) → FAIL
# ---------------------------------------------------------------------------

class TestIntegrationFreshnessDrift:
    """
    @resume
        Validates drift rule (increment > max_drift).
    """

    @pytest.mark.asyncio
    async def test_drift(self, integration_config_factory):
        # --- Arrange ---
        config = integration_config_factory()
        gateway = GatewayAsync(config)
        algo = HMACAlgorithm()

        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text(json.dumps({"dev_key": "33" * 32}))
        key = bytes.fromhex("33" * 32)

        freshness_path = Path(config["freshness"]["counter_file"])
        freshness_path.write_text(json.dumps({"counter": 0}))

        # --- Act ---
        await send(gateway, algo, key, 10, "bootstrap")
        await send(gateway, algo, key, 10, "first_update")
        response = await send(gateway, algo, key, 30, "drift")  # increment=20

        # --- Assert ---
        assert response.status == "error"
        assert response.reason == "FRESHNESS_FAIL"


# ---------------------------------------------------------------------------
# 4. Increment too small → FAIL
# ---------------------------------------------------------------------------

class TestIntegrationFreshnessIncrementTooSmall:
    """
    @resume
        Validates minimum increment rule.
    """

    @pytest.mark.asyncio
    async def test_increment_too_small(self, integration_config_factory):
        # --- Arrange ---
        config = integration_config_factory()
        config["freshness"]["min_increment"] = 2

        gateway = GatewayAsync(config)
        algo = HMACAlgorithm()

        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text(json.dumps({"dev_key": "44" * 32}))
        key = bytes.fromhex("44" * 32)

        freshness_path = Path(config["freshness"]["counter_file"])
        freshness_path.write_text(json.dumps({"counter": 0}))

        # --- Act ---
        await send(gateway, algo, key, 10, "bootstrap")
        await send(gateway, algo, key, 10, "first_update")
        response = await send(gateway, algo, key, 11, "too_small")  # increment=1

        # --- Assert ---
        assert response.status == "error"
        assert response.reason == "FRESHNESS_FAIL"


# ---------------------------------------------------------------------------
# 5. Increment too large + reject_out_of_range = true → FAIL
# ---------------------------------------------------------------------------

class TestIntegrationFreshnessIncrementTooLarge:
    """
    @resume
        Validates maximum increment rule when reject_out_of_range = true.
    """

    @pytest.mark.asyncio
    async def test_increment_too_large(self, integration_config_factory):
        # --- Arrange ---
        config = integration_config_factory()
        config["freshness"]["max_increment"] = 5
        config["freshness"]["reject_out_of_range"] = True

        gateway = GatewayAsync(config)
        algo = HMACAlgorithm()

        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text(json.dumps({"dev_key": "55" * 32}))
        key = bytes.fromhex("55" * 32)

        freshness_path = Path(config["freshness"]["counter_file"])
        freshness_path.write_text(json.dumps({"counter": 0}))

        # --- Act ---
        await send(gateway, algo, key, 10, "bootstrap")
        await send(gateway, algo, key, 10, "first_update")
        response = await send(gateway, algo, key, 20, "too_large")  # increment=10

        # --- Assert ---
        assert response.status == "error"
        assert response.reason == "FRESHNESS_FAIL"
