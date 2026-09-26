"""
Integration test suite validating deterministic failure
handling when the gateway encounters corrupted freshness state.

This module ensures that the gateway:

- detects invalid or unreadable freshness.json content before executing any
  freshness validation logic
- halts the pipeline deterministically and produces a stable `FRESHNESS_FAIL`
  response when persistence state is corrupted
- prevents downstream components (cryptographic verification, rotation,
  audit sequencing) from overriding or masking freshness corruption errors
- records the failure as the final append-only audit event, preserving strict
  observability guarantees and forensic traceability

These guarantees are essential for industrial, embedded, and safety-critical
deployments where persistent state integrity must be enforced rigorously and
gateway behavior must remain predictable even under external corruption
conditions.
"""

import pytest
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


class TestFreshnessFileCorruption:
    """
    Integration test suite validating the gateway’s resilience and deterministic
    failure handling when encountering corrupted freshness state.

    This class ensures that:
    - the gateway detects invalid or unreadable freshness.json content before
      executing freshness validation logic
    - corrupted state triggers a deterministic failure path, preventing
      undefined behavior in downstream pipeline stages
    - cryptographic verification does not override state corruption errors,
      preserving the integrity of the validation pipeline
    - audit logging records the failure as the final event, maintaining
      append‑only semantics and providing reliable forensic traceability
    - the system behaves predictably under state corruption conditions, a
      requirement for industrial, embedded, and safety‑critical deployments
      where persistent state integrity is essential

    These checks reinforce the architectural guarantee that the gateway
    responds deterministically to invalid persistence layers, ensuring
    operational safety and observability even when external state is damaged.
    """

    @pytest.mark.asyncio
    async def test_freshness_file_corruption(self, integration_config_factory):
        """
        Freshness file corruption:
        - freshness.json contains invalid JSON
        - must produce GATEWAY_ERROR
        """

        config = integration_config_factory()
        gateway = GatewayAsync(config)
        algo = HMACAlgorithm()

        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text(json.dumps({"dev_key": "55" * 32}))
        key = bytes.fromhex("55" * 32)

        freshness_path = Path(config["freshness"]["counter_file"])
        freshness_path.write_text("{invalid_json")

        payload = {"id": 1, "counter": 1, "msg": "x"}
        mac = algo.sign(payload, key)
        msg = {**payload, "hmac": mac}

        r = await gateway.process(msg)
        assert r.status == "error"
        assert r.reason == "FRESHNESS_FAIL"

        audit_path = Path(config["audit"]["path"])
        assert json.loads(audit_path.read_text().splitlines()[-1])["event"] == "FRESHNESS_FAIL"
