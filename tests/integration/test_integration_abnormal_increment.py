"""
Integration test suite validating strict monotonicity enforcement and
deterministic failure behavior within the gateway’s freshness pipeline.

@resume
    Ensures that the gateway rejects messages whose counters fail to advance
    relative to persisted freshness state, enforcing strict monotonicity rules
    required for replay protection and ordering guarantees.

@scope
    - rejection of identical or regressive counter values
    - deterministic `FRESHNESS_FAIL` response for abnormal increments
    - fail-fast pipeline semantics preventing downstream overrides
    - append-only audit logging of failure events for forensic traceability
    - predictable behavior under stateful conditions in distributed or
      safety-critical deployments

@ensures
    The gateway enforces monotonic counter progression rigorously, preventing
    replay-adjacent attacks, state desynchronization, and ordering violations.
"""

import pytest
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


class TestAbnormalIncrement:
    """
    @resume
        Integration test suite validating strict monotonicity enforcement within
        the gateway’s freshness subsystem.

    @scope
        - deterministic rejection of non-advancing counters
        - stable `FRESHNESS_FAIL` signaling for abnormal increments
        - strict separation between freshness validation and cryptographic logic
        - append-only audit logging of failure events
        - predictable behavior required for distributed and safety-critical systems

    @ensures
        The freshness subsystem behaves deterministically under stateful conditions,
        preserving ordering guarantees and replay protection.
    """

    @pytest.mark.asyncio
    async def test_abnormal_increment(self, integration_config_factory):
        """
        @resume
            Validates gateway behavior when incoming counter does not advance
            relative to persisted freshness state.

        @scope
            - freshness.json counter = 10
            - incoming message counter = 10 (no increment)
            - deterministic `FRESHNESS_FAIL` response
            - correct audit logging of failure event

        @returns
            A GatewayResponse with status="error" and reason="FRESHNESS_FAIL".

        @ensures
            The gateway halts processing immediately upon freshness violation and
            records the failure as the final append-only audit event.
        """

        # --- Arrange ---
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

        # --- Act ---
        r = await gateway.process(msg)

        # --- Assert ---
        assert r.status == "error"
        assert r.reason == "FRESHNESS_FAIL"

        audit_path = Path(config["audit"]["path"])
        last_event = json.loads(audit_path.read_text().splitlines()[-1])
        assert last_event["event"] == "FRESHNESS_FAIL"
