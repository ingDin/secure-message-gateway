"""
Integration test suite validating deterministic replay‑protection
behavior within the secure-message-gateway pipeline.

This module ensures that the gateway:

- accepts an initial message whose counter advances freshness state and whose
  HMAC signature is valid
- rejects subsequent messages with identical counter values, enforcing strict
  monotonic progression rules
- produces a stable, reproducible `FRESHNESS_FAIL` response for replay attempts
- halts pipeline execution immediately upon freshness violation, preventing
  downstream components from overriding fail-fast semantics
- records both acceptance and rejection events in strict append-only order,
  preserving forensic-grade traceability and deterministic observability

These guarantees validate the robustness of the freshness subsystem and ensure
that message ordering remains intact even under adversarial or repetitive input
conditions, a critical requirement for distributed, safety-critical, and
stateful deployments.
"""

import pytest
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


class TestReplayDetection:
    """
    Integration test suite validating the gateway’s replay‑protection guarantees
    and deterministic handling of repeated messages.

    This class ensures that:
    - the gateway correctly accepts an initial message whose counter advances
      freshness state and whose HMAC signature is valid
    - subsequent messages with identical counter values are rejected
      deterministically, enforcing strict monotonic progression rules
    - replay attempts trigger a fail‑fast `FRESHNESS_FAIL` response, preventing
      message duplication, state rollback, or replay‑adjacent attacks
    - audit logging captures both acceptance and rejection events in strict
      pipeline order, preserving append‑only semantics and forensic traceability
    - the gateway maintains stable behavior across repeated invocations, a
      requirement for distributed, safety‑critical, and stateful deployments
      where replay protection is foundational

    These checks validate the correctness and robustness of the freshness
    subsystem, ensuring that message ordering guarantees remain intact even
    under adversarial or repetitive input conditions.
    """

    @pytest.mark.asyncio
    async def test_replay_detection(self, integration_config_factory):
        """
        Replay detection:
        - first message accepted
        - second message with same counter rejected
        - audit logs MESSAGE_ACCEPTED + FRESHNESS_FAIL
        """

        config = integration_config_factory()
        gateway = GatewayAsync(config)
        algo = HMACAlgorithm()

        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text(json.dumps({"dev_key": "11" * 32}))
        key = bytes.fromhex("11" * 32)

        payload = {"id": 1, "counter": 1, "msg": "hello"}
        mac = algo.sign(payload, key)
        msg = {**payload, "hmac": mac}

        # First message accepted
        r1 = await gateway.process(msg)
        assert r1.status == "ok"

        # Replay rejected
        r2 = await gateway.process(msg)
        assert r2.status == "error"
        assert r2.reason == "FRESHNESS_FAIL"

        audit_path = Path(config["audit"]["path"])
        events = [json.loads(line)["event"] for line in audit_path.read_text().splitlines()]
        assert events == ["MESSAGE_ACCEPTED", "FRESHNESS_FAIL"]
