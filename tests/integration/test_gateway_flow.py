"""
Integration tests for secure_gateway.gateway.

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

These tests ensure that the gateway enforces message integrity,
freshness monotonicity, and strict schema validation before
processing incoming messages.
"""

import json
from pathlib import Path
import pytest

from secure_gateway.gateway import Gateway
from secure_gateway.crypto import sign_message, get_hmac_key


# ---------------------------------------------------------
# Fixtures
# ---------------------------------------------------------

@pytest.fixture
def config_dir(tmp_path):
    """Temporary config directory with valid HMAC key and freshness counter."""
    (tmp_path / "keys.json").write_text(json.dumps({
        "hmac_key": "a" * 64
    }))
    (tmp_path / "freshness.json").write_text(json.dumps({
        "counter": 0
    }))
    return tmp_path


@pytest.fixture
def gateway(config_dir, tmp_path):
    """Gateway instance used in all tests."""
    return Gateway(config_dir=config_dir, log_path=tmp_path / "audit.log")


@pytest.fixture
def build_message():
    """Factory for IncomingMessage dicts."""
    def _build(id=1, msg="hello", counter=1, hmac=""):
        return {"id": id, "msg": msg, "counter": counter, "hmac": hmac}
    return _build


@pytest.fixture
def compute_hmac(config_dir):
    """Factory for computing valid HMAC for a message."""
    def _compute(message):
        key = get_hmac_key(config_dir)
        payload = {
            "id": message["id"],
            "msg": message["msg"],
            "counter": message["counter"],
        }
        return sign_message(payload, key)
    return _compute


# ---------------------------------------------------------
# Test Class
# ---------------------------------------------------------

class TestGatewayFlow:
    """Integration tests for the secure message gateway."""

    def test_valid_message(self, gateway, build_message, compute_hmac):
        """A valid message with correct HMAC should be accepted."""
        msg = build_message(counter=1)
        msg["hmac"] = compute_hmac(msg)

        response = gateway.process(msg)
        assert response.status == "ok"

    def test_invalid_hmac(self, gateway, build_message):
        """A message with an incorrect HMAC should be rejected."""
        msg = build_message(counter=1, hmac="deadbeef")

        response = gateway.process(msg)
        assert response.status == "error"
        assert response.reason == "HMAC_FAIL"

    def test_replay_attack(self, gateway, build_message, compute_hmac):
        """Reusing the same counter should trigger a freshness failure."""
        msg1 = build_message(counter=1)
        msg1["hmac"] = compute_hmac(msg1)
        assert gateway.process(msg1).status == "ok"

        msg2 = build_message(counter=1)
        msg2["hmac"] = compute_hmac(msg2)

        response = gateway.process(msg2)
        assert response.status == "error"
        assert response.reason == "FRESHNESS_FAIL"

    def test_schema_invalid(self, gateway):
        """Missing required fields should fail schema validation."""
        msg = {
            "id": 1,
            "counter": 1,
            "hmac": "1234",
        }

        response = gateway.process(msg)
        assert response.status == "error"
        assert response.reason == "SCHEMA_FAIL"
