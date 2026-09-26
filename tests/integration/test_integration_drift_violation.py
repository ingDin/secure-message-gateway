"""
Integration test suite validating enforcement of monotonic
counter drift constraints within the secure-message-gateway pipeline.

This module ensures that the gateway correctly detects and rejects messages
whose counters exceed configured drift thresholds, preventing:

- replay-adjacent attacks
- out-of-order message injection
- state desynchronization across distributed or safety-critical deployments
- bypassing freshness guarantees through excessive counter jumps

It verifies that:
- freshness validation halts the pipeline deterministically
- cryptographic and schema validation do not override drift violations
- audit logging records the failure as the final append-only event
- the gateway produces a stable, reproducible `FRESHNESS_FAIL` response

These guarantees reinforce the architectural contract that counter drift must
be tightly controlled to maintain system integrity, observability, and
security in industrial-grade message-processing environments.
"""

import pytest
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


class TestDriftViolation:
    """
    Integration test suite validating enforcement of monotonic counter drift
    constraints within the freshness subsystem.

    This class ensures that:
    - the gateway correctly identifies counter values that exceed configured
      drift thresholds (e.g., excessively large jumps between consecutive
      messages)
    - freshness validation halts the pipeline early and produces a deterministic
      `FRESHNESS_FAIL` response
    - cryptographic verification and schema validation do not override or
      suppress freshness violations
    - audit logging records the failure as the final event, preserving strict
      observability guarantees and append-only semantics

    These checks are essential for preventing replay‑adjacent attacks,
    out-of-order message injection, and state desynchronization in
    safety‑critical or distributed environments where counter drift must be
    tightly controlled.
    """

    @pytest.mark.asyncio
    async def test_drift_violation(self, integration_config_factory):
        """
        Drift violation:
        - freshness.json starts at counter=1
        - message counter jumps too far (9999)
        - must produce FRESHNESS_FAIL
        """

        config = integration_config_factory()
        gateway = GatewayAsync(config)
        algo = HMACAlgorithm()

        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text(json.dumps({"dev_key": "22" * 32}))
        key = bytes.fromhex("22" * 32)

        freshness_path = Path(config["freshness"]["counter_file"])
        freshness_path.write_text(json.dumps({"counter": 1}))

        payload = {"id": 1, "counter": 9999, "msg": "drift"}
        mac = algo.sign(payload, key)
        msg = {**payload, "hmac": mac}

        r = await gateway.process(msg)
        assert r.status == "error"
        assert r.reason == "FRESHNESS_FAIL"

        audit_path = Path(config["audit"]["path"])
        assert json.loads(audit_path.read_text().splitlines()[-1])["event"] == "FRESHNESS_FAIL"
