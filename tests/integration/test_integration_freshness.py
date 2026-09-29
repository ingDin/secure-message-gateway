"""
@summary
Integration test suite for the secure-message-gateway freshness subsystem.

These tests validate the REAL operational behaviour of FreshnessManager:

    - If freshness.json exists → bootstrap loads the stored counter.
    - The first message NEVER validates freshness rules.
    - The second message validates increment relative to the stored counter.
    - The third message validates increment relative to the updated counter.

All freshness violations must propagate deterministically as FRESHNESS_FAIL
through gateway.process().
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

    @scope
        - existing freshness.json
        - bootstrap loads stored counter
        - first update accepted
        - second update with increment=0 rejected

    @ensures
        The gateway detects zero-increment progression and raises FRESHNESS_FAIL.
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
        Validates replay detection when incoming < last.

    @scope
        - existing freshness.json
        - bootstrap loads stored counter
        - first update accepted
        - replay attempt rejected

    @ensures
        The gateway rejects stale counters and raises FRESHNESS_FAIL.
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
        Validates drift rule enforcement when increment exceeds max_drift.

    @scope
        - existing freshness.json
        - bootstrap loads stored counter
        - first update accepted
        - drift violation rejected

    @ensures
        The gateway enforces drift constraints and raises FRESHNESS_FAIL.
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
        Validates minimum increment rule enforcement.

    @scope
        - min_increment configured
        - bootstrap loads stored counter
        - first update accepted
        - second update with increment < min_increment rejected

    @ensures
        The gateway enforces minimum increment constraints and raises FRESHNESS_FAIL.
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

    @scope
        - max_increment configured
        - reject_out_of_range enabled
        - bootstrap loads stored counter
        - first update accepted
        - second update exceeding max_increment rejected

    @ensures
        The gateway enforces maximum increment constraints and raises FRESHNESS_FAIL.
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
