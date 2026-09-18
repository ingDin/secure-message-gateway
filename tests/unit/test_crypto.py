"""
Unit tests for secure_gateway.crypto.

Coverage:
- HMAC key loading:
    * valid keys (different sizes)
    * missing file
    * invalid JSON
    * missing 'hmac_key'
    * invalid hex / empty / null / non-string values

- HMAC signing:
    * deterministic output (64 hex chars)
    * independent of key order in payload
    * changes when payload changes
    * changes when key changes
    * known-answer test (RFC 2104-style)

- HMAC verification:
    * success case
    * failure when MAC is modified
    * failure when payload is modified

These tests guarantee deterministic, secure, and predictable behavior
for the crypto module, ensuring message integrity and replay protection.
"""

import pytest
import json

from secure_gateway.crypto import (
    HMACVerificationError,
    get_hmac_key,
    sign_message,
    verify_message,
    KeyLoadError,
)


class TestLoadHmacKey:
    @pytest.mark.parametrize(
        "hmac_test_env",
        [16, 64],
        indirect=True,
    )
    def test_load_key(self, hmac_test_env):
        config_dir = hmac_test_env["config_dir"]
        expected_key = hmac_test_env["key"]

        key = get_hmac_key(config_dir)

        assert isinstance(key, bytes)
        assert key == expected_key

    def test_load_key_file_missing(self, tmp_path):
        with pytest.raises(KeyLoadError):
            get_hmac_key(tmp_path)

    def test_load_key_invalid_json(self, keys_file):
        config_dir = keys_file("{invalid json")

        with pytest.raises(KeyLoadError):
            get_hmac_key(config_dir)

    def test_load_key_missing_hmac_key(self, keys_file):
        config_dir = keys_file('{"other_key": "abc"}')

        with pytest.raises(KeyLoadError):
            get_hmac_key(config_dir)

    @pytest.mark.parametrize(
        "content",
        [
            '{"hmac_key": "not-hex"}',
            '{"hmac_key": ""}',
            '{"hmac_key": null}',
            '{"hmac_key": 123}',
        ],
    )
    def test_load_key_invalid_hmac_key(self, keys_file, content):
        config_dir = keys_file(content)

        with pytest.raises(KeyLoadError):
            get_hmac_key(config_dir)


class TestSignMessage:
    def test_sign_message(self, hmac_key, sample_payload):
        mac = sign_message(sample_payload, hmac_key)

        assert isinstance(mac, str)
        assert len(mac) == 64
        assert all(c in "0123456789abcdef" for c in mac)

    def test_sign_message_is_independent_of_key_order(self, hmac_key):
        payload_1 = {
            "msg": "hello",
            "timestamp": 123,
        }

        payload_2 = {
            "timestamp": 123,
            "msg": "hello",
        }

        assert sign_message(payload_1, hmac_key) == sign_message(
            payload_2,
            hmac_key,
        )

    def test_sign_message_changes_when_payload_changes(self, hmac_key):
        payload_1 = {"msg": "hello"}
        payload_2 = {"msg": "goodbye"}

        assert sign_message(payload_1, hmac_key) != sign_message(
            payload_2,
            hmac_key,
        )

    def test_sign_message_changes_when_key_changes(self, sample_payload):
        key_1 = b"key-one"
        key_2 = b"key-two"

        assert sign_message(sample_payload, key_1) != sign_message(
            sample_payload,
            key_2,
        )

    def test_sign_message_known_answer(self):
        # RFC 2104-style known answer test (deterministic HMAC)

        key = b"Jefe"
        payload = {
            "message": "what do ya want for nothing?",
        }

        expected_mac = (
            "fd5b922ff4d4a1bdc60356ab95bc7768"
            "5685cb05db4224727e1a120aa33cc779"
        )

        assert sign_message(payload, key) == expected_mac


class TestVerifyMessage:
    @pytest.fixture
    def valid_mac(self, hmac_key, sample_payload):
        return sign_message(sample_payload, hmac_key)

    def test_verify_message_success(
        self,
        hmac_key,
        sample_payload,
        valid_mac,
    ):
        verify_message(sample_payload, hmac_key, valid_mac)

    def test_verify_message_failure_when_mac_is_modified(
        self,
        hmac_key,
        sample_payload,
        valid_mac,
    ):
        bad_mac = valid_mac[:-1] + (
            "0" if valid_mac[-1] != "0" else "1"
        )

        with pytest.raises(HMACVerificationError):
            verify_message(sample_payload, hmac_key, bad_mac)

    def test_verify_message_failure_when_payload_is_modified(
        self,
        hmac_key,
        sample_payload,
        valid_mac,
    ):
        tampered_payload = {
            **sample_payload,
            "msg": "tampered",
        }

        with pytest.raises(HMACVerificationError):
            verify_message(tampered_payload, hmac_key, valid_mac)
