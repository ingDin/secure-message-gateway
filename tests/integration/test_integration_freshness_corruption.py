"""
Integration test suite validating deterministic replay‑protection behavior
within the secure-message-gateway pipeline.

@resume
    Ensures that the gateway enforces strict monotonic counter progression,
    rejecting replay attempts deterministically and preserving state integrity
    across safety‑critical and distributed deployments.

@scope
    - acceptance of initial messages whose counters advance freshness state
    - deterministic rejection of repeated messages with identical counters
    - stable `FRESHNESS_FAIL` signaling for replay attempts
    - fail-fast semantics preventing downstream pipeline execution
    - append-only audit logging of acceptance and rejection events

@ensures
    The freshness subsystem behaves predictably under adversarial or repetitive
    input conditions, maintaining ordering guarantees and preventing replay‑adjacent
    attacks.
"""

import pytest
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


class TestReplayDetection:
    """
    @resume
        Integration test suite validating the gateway’s replay‑protection guarantees
        and deterministic handling of repeated messages.

    @scope
        - correct acceptance of initial monotonic messages
        - deterministic rejection of identical counter values
        - fail-fast freshness violation semantics
        - append-only audit logging of MESSAGE_ACCEPTED and FRESHNESS_FAIL
        - predictable behavior required for distributed, stateful, and safety‑critical
          deployments

    @ensures
        The freshness subsystem enforces strict monotonic progression rules, preserving
        ordering guarantees and preventing replay‑adjacent attacks.
    """

    @pytest.mark.asyncio
    async def test_replay_detection(self, integration_config_factory):
        """
        @resume
            Validates replay detection behavior for two sequential messages with
            identical counters.

        @scope
            - first message accepted (counter advances freshness state)
            - second message rejected deterministically (same counter)
            - audit log contains MESSAGE_ACCEPTED followed by FRESHNESS_FAIL

        @returns
            Two GatewayResponse objects:
                * first: status="ok"
                * second: status="error", reason="FRESHNESS_FAIL"

        @ensures
            The gateway halts processing immediately upon replay detection and
            records acceptance and rejection events in strict append-only order.
        """

        # --- Arrange ---
        config = integration_config_factory()
        gateway = GatewayAsync(config)
        algo = HMACAlgorithm()

        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text(json.dumps({"dev_key": "11" * 32}))
        key = bytes.fromhex("11" * 32)

        payload = {"id": 1, "counter": 1, "msg": "hello"}
        mac = algo.sign(payload, key)
        msg = {**payload, "hmac": mac}

        # --- Act ---
        r1 = await gateway.process(msg)
        r2 = await gateway.process(msg)

        # --- Assert ---
        assert r1.status == "ok"
        assert r2.status == "error"
        assert r2.reason == "FRESHNESS_FAIL"

        audit_path = Path(config["audit"]["path"])
        events = [json.loads(line)["event"] for line in audit_path.read_text().splitlines()]
        assert events == ["MESSAGE_ACCEPTED", "FRESHNESS_FAIL"]
