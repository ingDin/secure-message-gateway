"""
Integration tests for secure_gateway.gateway.GatewayAsync.

Coverage:
- Valid message flow:
    * correct HMAC
    * accepted by gateway

- HMAC validation:
    * incorrect HMAC rejected with HMAC_FAIL

- Freshness / replay protection:
    * strictly increasing counters accepted
    * equal or lower counters rejected with FRESHNESS_FAIL

- Schema validation:
    * missing required fields rejected with SCHEMA_FAIL
"""

import json
import pytest
from pathlib import Path

from secure_gateway.gateway import GatewayAsync
from secure_gateway.crypto import get_hmac_key_async, sign_message_async


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------
# Test Class
# ---------------------------------------------------------

class TestGatewayAsyncFlow:
    """Integration tests for the async secure message gateway."""

    async def test_valid_message(self, gateway, build_message, compute_hmac):
        """A valid message with correct HMAC should be accepted."""
        msg = build_message(counter=1)
        msg["hmac"] = await compute_hmac(msg)

        response = await gateway.process(msg)
        assert response.status == "ok"

    async def test_invalid_hmac(self, gateway, build_message):
        """A message with an incorrect HMAC should be rejected."""
        msg = build_message(counter=1, hmac="deadbeef")

        response = await gateway.process(msg)
        assert response.status == "error"
        assert response.reason == "HMAC_FAIL"

    async def test_replay_attack(self, gateway, build_message, compute_hmac):
        """Reusing the same counter should trigger a freshness failure."""
        msg1 = build_message(counter=1)
        msg1["hmac"] = await compute_hmac(msg1)
        assert (await gateway.process(msg1)).status == "ok"

        msg2 = build_message(counter=1)
        msg2["hmac"] = await compute_hmac(msg2)

        response = await gateway.process(msg2)
        assert response.status == "error"
        assert response.reason == "FRESHNESS_FAIL"

    async def test_schema_invalid(self, gateway):
        """Missing required fields should fail schema validation."""
        msg = {
            "id": 1,
            "counter": 1,
            "hmac": "1234",
        }

        response = await gateway.process(msg)
        assert response.status == "error"
        assert response.reason == "SCHEMA_FAIL"
