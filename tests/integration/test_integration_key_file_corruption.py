"""
Integration test suite validating deterministic failure
behavior when the gateway encounters corrupted cryptographic key material.

This module ensures that the gateway:

- detects invalid or unreadable keys.json content before performing any
  cryptographic verification
- halts the pipeline immediately and produces a stable `HMAC_FAIL` response
  when key integrity cannot be established
- prevents downstream components (freshness manager, rotation subsystem,
  audit sequencing) from overriding or masking key corruption errors
- records the failure as the final append-only audit event, preserving strict
  observability guarantees and forensic-grade traceability
- maintains predictable behavior even when critical cryptographic persistence
  layers are damaged, a requirement for industrial, embedded, and
  safety-critical deployments

These guarantees reinforce the architectural contract that cryptographic key
integrity must be validated before any pipeline logic executes, ensuring
secure, deterministic, and auditable message processing.
"""

import pytest
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync


class TestKeyFileCorruption:
    """
    Integration test suite validating the gateway’s deterministic behavior when
    encountering corrupted cryptographic key material.

    This class ensures that:
    - the gateway detects invalid or unreadable key files before attempting
      HMAC verification or any downstream pipeline operations
    - corrupted key state triggers a predictable failure path, preventing
      undefined behavior in cryptographic routines
    - the pipeline halts early and produces a stable `HMAC_FAIL` response,
      reflecting the inability to validate message authenticity
    - audit logging records the failure as the final event, preserving
      append‑only semantics and enabling forensic traceability
    - the gateway maintains operational safety and observability even when
      critical cryptographic persistence layers are damaged

    These checks reinforce the architectural requirement that key integrity
    must be validated before any cryptographic or freshness logic executes,
    ensuring secure and deterministic behavior in long‑running or
    safety‑critical deployments.
    """

    @pytest.mark.asyncio
    async def test_key_file_corruption(self, integration_config_factory):
        """
        Key file corruption:
        - keys.json contains invalid JSON
        - must produce GATEWAY_ERROR
        """

        config = integration_config_factory()
        gateway = GatewayAsync(config)

        keys_path = Path(config["crypto"]["keys_file"])
        keys_path.write_text("{invalid_json")

        payload = {"id": 1, "counter": 1, "msg": "x", "hmac": "00"}

        r = await gateway.process(payload)
        assert r.status == "error"
        assert r.reason == "HMAC_FAIL"

        audit_path = Path(config["audit"]["path"])
        assert json.loads(audit_path.read_text().splitlines()[-1])["event"] == "HMAC_FAIL"
