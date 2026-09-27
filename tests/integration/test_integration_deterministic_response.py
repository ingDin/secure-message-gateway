"""
Integration test suite validating deterministic response behavior within the
secure-message-gateway pipeline.

@resume
    Ensures that the gateway produces stable, reproducible outcomes for
    structurally identical messages under normal operating conditions.

@scope
    - sequential messages with identical structure and valid HMAC signatures
      yield consistent status/reason fields
    - monotonic counter progression does not alter semantic validation outcomes
    - stateful subsystems (freshness manager, audit logger, key loader) behave
      deterministically when exercised in sequence
    - predictable end-to-end behavior required for safety-critical, audit-driven,
      and industrial message-processing workflows

@ensures
    The gateway remains fully deterministic for valid message flows, enabling
    reliable integration with upstream and downstream systems.
"""

import pytest
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


class TestDeterministicResponse:
    """
    @resume
        Integration test suite validating deterministic behavior of the gateway’s
        end‑to‑end message‑processing pipeline under normal operating conditions.

    @scope
        - stable response patterns for structurally identical messages
        - consistent status/reason fields across equivalent validation paths
        - deterministic behavior even when stateful components are exercised
          sequentially (freshness manager, audit logger, key loader)
        - predictable semantics required for safety‑critical and audit‑driven systems

    @ensures
        The gateway behaves predictably for valid message flows, reinforcing
        architectural guarantees for industrial and embedded deployments.
    """

    @pytest.mark.asyncio
    async def test_deterministic_response(self, integration_config_factory):
        """
        @resume
            Validates deterministic response behavior for two structurally identical
            messages whose counters differ only to avoid freshness replay.

        @scope
            - identical message structure
            - valid HMAC signatures
            - monotonic counter progression
            - consistent status/reason fields across sequential processing

        @returns
            Two GatewayResponse objects with identical status/reason fields.

        @ensures
            The gateway produces stable, reproducible outcomes for equivalent
            message flows, preserving deterministic behavior across stateful
            components.
        """
        config = integration_config_factory()
        gateway = GatewayAsync(config)
        algo = HMACAlgorithm()

        # --- Arrange ---
        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text(json.dumps({"dev_key": "66" * 32}))
        key = bytes.fromhex("66" * 32)

        # First message
        payload1 = {"id": 1, "counter": 1, "msg": "hello"}
        mac1 = algo.sign(payload1, key)
        msg1 = {**payload1, "hmac": mac1}

        # Second message (same structure, counter incremented)
        payload2 = {"id": 1, "counter": 2, "msg": "hello"}
        mac2 = algo.sign(payload2, key)
        msg2 = {**payload2, "hmac": mac2}

        # --- Act ---
        r1 = await gateway.process(msg1)
        r2 = await gateway.process(msg2)

        # --- Assert ---
        assert r1.status == "ok"
        assert r2.status == "ok"

        # Deterministic behavior: same type of message → same status pattern
        assert r1.status == r2.status
        assert r1.reason == r2.reason
