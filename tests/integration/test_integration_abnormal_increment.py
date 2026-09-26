"""
Integration test suite validating strict monotonicity
enforcement and deterministic failure behavior within the gateway’s freshness
pipeline.

This module ensures that the gateway:

- rejects messages whose counters fail to advance relative to persisted
  freshness state
- produces a stable, reproducible `FRESHNESS_FAIL` response for abnormal
  increments such as identical or regressive counter values
- halts pipeline execution immediately upon freshness violation, preventing
  downstream components (cryptographic verification, rotation, audit sequencing)
  from overriding fail-fast semantics
- records the failure as the final append-only audit event, preserving
  forensic-grade traceability and deterministic observability

These guarantees reinforce the architectural requirement that monotonic counter
progression must be strictly enforced to prevent replay-adjacent attacks,
state desynchronization, and ordering violations in distributed or
safety-critical deployments.
"""

import pytest
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


class TestAbnormalIncrement:
    """
    Integration test suite validating strict monotonicity enforcement within the
    gateway’s freshness subsystem.

    This class ensures that:
    - the gateway correctly rejects messages whose counter does not advance
      relative to the persisted freshness state
    - abnormal increments (e.g., identical counter values) trigger a deterministic
      `FRESHNESS_FAIL` response, preventing replay‑adjacent attacks
    - cryptographic verification and schema validation do not override freshness
      violations, preserving the pipeline’s fail‑fast semantics
    - audit logging records the failure as the final event, maintaining
      append‑only behavior and providing reliable forensic traceability
    - the freshness subsystem behaves predictably under stateful conditions,
      ensuring that message ordering guarantees remain intact in distributed or
      safety‑critical environments

    These checks reinforce the architectural requirement that counter progression
    must be strictly monotonic, forming the foundation for replay protection and
    state consistency across long‑running deployments.
    """

    @pytest.mark.asyncio
    async def test_abnormal_increment(self, integration_config_factory):
        """
        Abnormal increment:
        - freshness.json counter=10
        - message counter=10 (no increment)
        - must produce FRESHNESS_FAIL
        """

        config = integration_config_factory()
        gateway = GatewayAsync(config)
        algo = HMACAlgorithm()

        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text(json.dumps({"dev_key": "33" * 32}))
        key = bytes.fromhex("33" * 32)

        freshness_path = Path(config["freshness"]["counter_file"])
        freshness_path.write_text(json.dumps({"counter": 10}))

        payload = {"id": 1, "counter": 10, "msg": "same"}
        mac = algo.sign(payload, key)
        msg = {**payload, "hmac": mac}

        r = await gateway.process(msg)
        assert r.status == "error"
        assert r.reason == "FRESHNESS_FAIL"

        audit_path = Path(config["audit"]["path"])
        assert json.loads(audit_path.read_text().splitlines()[-1])["event"] == "FRESHNESS_FAIL"
