"""
Integration test suite validating deterministic failure behavior when the gateway
encounters corrupted cryptographic key material.

@resume
    Ensures that the gateway halts immediately and deterministically when
    keys.json contains invalid or unreadable content, enforcing strict
    cryptographic integrity guarantees required for safety‑critical deployments.

@scope
    - detection of corrupted or malformed key files
    - deterministic `HMAC_FAIL` response when key integrity cannot be established
    - fail-fast semantics preventing downstream pipeline execution
    - append-only audit logging of key corruption failures
    - predictable behavior under damaged cryptographic persistence layers

@ensures
    The gateway validates cryptographic key integrity before executing any
    pipeline logic, preserving operational safety, observability, and forensic
    traceability.
"""

import pytest
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync


class TestKeyFileCorruption:
    """
    @resume
        Integration test suite validating the gateway’s deterministic behavior when
        encountering corrupted cryptographic key material.

    @scope
        - early detection of invalid keys.json content
        - deterministic halting of the pipeline with `HMAC_FAIL`
        - strict separation between key validation and downstream logic
        - append-only audit logging of corruption events
        - predictable behavior required for industrial and embedded systems

    @ensures
        The gateway responds deterministically to invalid cryptographic persistence
        layers, preserving safety and forensic-grade observability.
    """

    @pytest.mark.asyncio
    async def test_key_file_corruption(self, integration_config_factory):
        """
        @resume
            Validates gateway behavior when keys.json contains invalid JSON.

        @scope
            - corrupted keys.json detection
            - deterministic `HMAC_FAIL` response
            - correct audit logging of failure event

        @returns
            A GatewayResponse with status="error" and reason="HMAC_FAIL".

        @ensures
            The gateway halts processing immediately upon key corruption and
            records the failure as the final append-only audit event.
        """

        # --- Arrange ---
        config = integration_config_factory()
        gateway = GatewayAsync(config)

        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text("{invalid_json")

        # Minimal message (HMAC irrelevant due to early failure)
        payload = {"id": 1, "counter": 1, "msg": "x", "hmac": "00"}

        # --- Act ---
        r = await gateway.process(payload)

        # --- Assert ---
        assert r.status == "error"
        assert r.reason == "HMAC_FAIL"

        audit_path = Path(config["audit"]["path"])
        last_event = json.loads(audit_path.read_text().splitlines()[-1])
        assert last_event["event"] == "HMAC_FAIL"
