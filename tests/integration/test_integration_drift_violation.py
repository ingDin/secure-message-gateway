"""
Integration test suite validating enforcement of monotonic counter drift
constraints within the secure-message-gateway pipeline.

@resume
    Ensures that the gateway correctly detects and rejects messages whose
    counters exceed configured drift thresholds, enforcing strict freshness
    guarantees required for replay protection and state consistency.

@scope
    - detection of excessive counter jumps
    - deterministic `FRESHNESS_FAIL` response for drift violations
    - fail-fast semantics preventing downstream pipeline execution
    - append-only audit logging of drift failures
    - predictable behavior required for distributed and safety-critical systems

@ensures
    Counter drift remains tightly controlled, preserving system integrity,
    observability, and security in industrial-grade message-processing
    environments.
"""

import pytest
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


class TestDriftViolation:
    """
    @resume
        Integration test suite validating enforcement of monotonic counter drift
        constraints within the freshness subsystem.

    @scope
        - identification of counter values exceeding configured drift thresholds
        - deterministic halting of the pipeline with `FRESHNESS_FAIL`
        - strict separation between freshness validation and cryptographic logic
        - append-only audit logging of drift violations
        - predictable behavior required for distributed and safety-critical deployments

    @ensures
        The gateway responds deterministically to drift violations, preventing
        replay-adjacent attacks, ordering violations, and state desynchronization.
    """

    @pytest.mark.asyncio
    async def test_drift_violation(self, integration_config_factory):
        """
        @resume
            Validates gateway behavior when incoming counter exceeds configured
            drift thresholds.

        @scope
            - freshness.json counter = 1
            - incoming message counter = 9999 (excessive drift)
            - deterministic `FRESHNESS_FAIL` response
            - correct audit logging of failure event

        @returns
            A GatewayResponse with status="error" and reason="FRESHNESS_FAIL".

        @ensures
            The gateway halts processing immediately upon drift violation and
            records the failure as the final append-only audit event.
        """

        # --- Arrange ---
        config = integration_config_factory()
        gateway = GatewayAsync(config)
        algo = HMACAlgorithm()

        # Valid key material
        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text(json.dumps({"dev_key": "22" * 32}))
        key = bytes.fromhex("22" * 32)

        # Freshness baseline
        freshness_path = Path(config["freshness"]["counter_file"])
        freshness_path.write_text(json.dumps({"counter": 1}))

        # Message with excessive drift
        payload = {"id": 1, "counter": 9999, "msg": "drift"}
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
