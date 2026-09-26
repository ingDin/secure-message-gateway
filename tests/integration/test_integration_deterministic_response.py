"""
Integration test suite validating deterministic response
behavior within the secure-message-gateway pipeline.

This module ensures that the gateway produces stable, reproducible outcomes
for structurally identical messages under normal operating conditions. It
verifies that:

- sequential messages with identical structure and valid HMAC signatures
  yield consistent status/reason fields
- monotonic counter progression does not alter semantic validation outcomes
- stateful subsystems (freshness manager, audit logger, key loader) behave
  deterministically when exercised in sequence
- the gateway maintains predictable end-to-end behavior required for
  safety-critical, audit-driven, and industrial message-processing workflows

These guarantees reinforce the architectural contract that the gateway must
remain fully deterministic for valid message flows, enabling reliable
integration with upstream and downstream systems.
"""

import pytest
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


class TestDeterministicResponse:
    """
    Integration test suite validating deterministic behavior of the gateway’s
    end‑to‑end message‑processing pipeline under normal operating conditions.

    This class ensures that:
    - sequential messages with identical structure and valid cryptographic
      signatures produce stable, reproducible response patterns
    - freshness progression (monotonic counter increments) does not alter
      the semantic outcome of message validation
    - the gateway maintains consistent status/reason fields across equivalent
      validation paths, a critical requirement for safety‑critical and
      audit‑driven systems
    - deterministic behavior is preserved even when stateful components
      (freshness manager, audit logger, key loader) are exercised in sequence

    These guarantees reinforce the architectural contract that the gateway
    behaves predictably for valid message flows, enabling reliable integration
    with upstream and downstream systems in industrial or embedded deployments.
    """

    @pytest.mark.asyncio
    async def test_deterministic_response(self, integration_config_factory):
        """
        Deterministic response:
        - same structure → same status pattern
        - counter differs to avoid freshness replay
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
