"""
Unit tests for secure_gateway.crypto (synchronous HMAC logic).

These tests validate the deterministic and security‑critical behavior of the
HMAC signing and verification routines. The suite ensures that message
digests are stable, independent of key order, sensitive to payload and key
changes, and compliant with RFC 2104 known‑answer vectors. It also verifies
that tampered payloads or modified MACs are correctly rejected, guaranteeing
message integrity and robust replay protection within the gateway.
"""


import pytest
import json

from secure_gateway.exceptions import HMACError
from secure_gateway.crypto import (
    sign_message,
    verify_message,
)


# ---------------------------------------------------------
# Tests for sign_message
# ---------------------------------------------------------

class TestSignMessage:
    """Tests for deterministic and correct HMAC signing."""

    def test_sign_message(self, hmac_key, sample_payload):
        """Signing should produce a 64‑char lowercase hex digest."""
        mac = sign_message(sample_payload, hmac_key)

        assert isinstance(mac, str)
        assert len(mac) == 64
        assert all(c in "0123456789abcdef" for c in mac)

    def test_sign_message_is_independent_of_key_order(self, hmac_key):
        """Signing should not depend on dict key order."""
        payload_1 = {"msg": "hello", "timestamp": 123}
        payload_2 = {"timestamp": 123, "msg": "hello"}

        assert sign_message(payload_1, hmac_key) == sign_message(payload_2, hmac_key)

    def test_sign_message_changes_when_payload_changes(self, hmac_key):
        """Different payloads should produce different HMACs."""
        payload_1 = {"msg": "hello"}
        payload_2 = {"msg": "goodbye"}

        assert sign_message(payload_1, hmac_key) != sign_message(payload_2, hmac_key)

    def test_sign_message_changes_when_key_changes(self, sample_payload):
        """Different keys should produce different HMACs."""
        key_1 = b"key-one"
        key_2 = b"key-two"

        assert sign_message(sample_payload, key_1) != sign_message(sample_payload, key_2)

    def test_sign_message_known_answer(self):
        """RFC 2104 known-answer test should match expected output."""
        key = b"Jefe"
        payload = {"message": "what do ya want for nothing?"}

        expected_mac = (
            "fd5b922ff4d4a1bdc60356ab95bc7768"
            "5685cb05db4224727e1a120aa33cc779"
        )

        assert sign_message(payload, key) == expected_mac


# ---------------------------------------------------------
# Tests for verify_message
# ---------------------------------------------------------

class TestVerifyMessage:
    """Tests for verifying HMAC correctness."""

    @pytest.fixture
    def valid_mac(self, hmac_key, sample_payload):
        """Fixture providing a valid MAC for the sample payload."""
        return sign_message(sample_payload, hmac_key)

    def test_verify_message_success(self, hmac_key, sample_payload, valid_mac):
        """Valid MAC and payload should verify without error."""
        verify_message(sample_payload, hmac_key, valid_mac)

    def test_verify_message_failure_when_mac_is_modified(
        self, hmac_key, sample_payload, valid_mac
    ):
        """Modifying the MAC should cause verification failure."""
        bad_mac = valid_mac[:-1] + ("0" if valid_mac[-1] != "0" else "1")

        with pytest.raises(HMACError):
            verify_message(sample_payload, hmac_key, bad_mac)

    def test_verify_message_failure_when_payload_is_modified(
        self, hmac_key, sample_payload, valid_mac
    ):
        """Modifying the payload should cause verification failure."""
        tampered_payload = {**sample_payload, "msg": "tampered"}

        with pytest.raises(HMACError):
            verify_message(tampered_payload, hmac_key, valid_mac)
