"""
Unit tests for HMACAlgorithm.

Covers:
- key generation
- async key loading (valid + invalid)
- sync signing/verification
- async signing/verification
"""

import pytest
import os
import json

from secure_gateway.hmac import HMACAlgorithm
from secure_gateway.exceptions import HMACError


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def crypto_unit_config_factory(tmp_path):
    """
    Create a minimal crypto config for unit tests.
    Allows overriding crypto fields.
    """
    def _factory(overrides=None):
        base = {
            "environment": "dev",
            "crypto": {
                "algorithm": "HMAC",
                "keys_file": str(tmp_path / "keys.json"),
                "keys_archive": str(tmp_path / "keys_archive.json"),

                # Minimal requirements for unit tests
                "hmac_algorithm": "HMAC",
                "allowed_algorithms": ["HMAC"],
                "min_key_length": 4,
                "rotation_required": False,
                "rotation_interval_days": 1,
            }
        }

        if overrides:
            base["crypto"].update(overrides)

        return base

    return _factory


@pytest.fixture
def hmac_algo():
    """Return a fresh HMACAlgorithm instance."""
    return HMACAlgorithm()


@pytest.fixture
def hex_key_bytes():
    """Return cryptographically secure random bytes."""
    return bytearray.fromhex(os.urandom(16).hex())


# ============================================================================
# Test constants
# ============================================================================

VALID_KEY = os.urandom(16).hex()
INVALID_HEX = "zzzzzzzz"
SHORT_KEY = "aa"
MAC_HEX_LENGTH = 64  # SHA256 hex digest length


# ============================================================================
# Test suite
# ============================================================================

class TestHMACAlgorithm:
    """Minimal test suite for HMACAlgorithm."""

    # ----------------------------------------------------------------------
    # Key generation
    # ----------------------------------------------------------------------
    def test_generate_key(self, hmac_algo):
        """generate_key should return a valid hex string of correct length."""
        key = hmac_algo.generate_key(16)
        assert isinstance(key, str)
        assert len(bytes.fromhex(key)) == 16

    # ----------------------------------------------------------------------
    # Async key loading — failures
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "keys_content,config_override,expected_error",
        [
            ({"prod_key": VALID_KEY}, {}, "Missing key"),
            ({"dev_key": INVALID_HEX}, {}, "hex-encoded"),
            ({"dev_key": SHORT_KEY}, {"min_key_length": 4}, "too short"),
            ({"dev_key": VALID_KEY}, {"allowed_algorithms": ["SHA1"]}, "not allowed"),
        ]
    )
    async def test_load_key_async_failures(
        self, hmac_algo, json_file_factory, crypto_unit_config_factory,
        keys_content, config_override, expected_error
    ):
        """load_key_async should reject invalid key configurations."""
        json_file_factory("keys.json", keys_content)
        config = crypto_unit_config_factory(config_override)

        with pytest.raises(HMACError) as exc:
            await hmac_algo.load_key_async(config)

        assert expected_error in str(exc.value)

    # ----------------------------------------------------------------------
    # Async key loading — success
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_load_key_async_valid(
        self, hmac_algo, json_file_factory, crypto_unit_config_factory
    ):
        """load_key_async should return the decoded key when valid."""
        json_file_factory("keys.json", {"dev_key": VALID_KEY})
        config = crypto_unit_config_factory()

        key = await hmac_algo.load_key_async(config)
        assert key == bytes.fromhex(VALID_KEY)

    # ----------------------------------------------------------------------
    # Sync signing
    # ----------------------------------------------------------------------
    def test_sign(self, hmac_algo, hex_key_bytes):
        """sign() should return a valid SHA256 hex digest."""
        mac = hmac_algo.sign({"a": 1}, hex_key_bytes)
        assert isinstance(mac, str)
        assert len(mac) == MAC_HEX_LENGTH

    # ----------------------------------------------------------------------
    # Sync verification
    # ----------------------------------------------------------------------
    def test_verify_success(self, hmac_algo, hex_key_bytes):
        """verify() should not raise when MAC is correct."""
        mac = hmac_algo.sign({"x": 10}, hex_key_bytes)
        hmac_algo.verify({"x": 10}, hex_key_bytes, mac)

    def test_verify_fail(self, hmac_algo, hex_key_bytes):
        """verify() should raise HMACError for tampered MAC."""
        mac = hmac_algo.sign({"x": 10}, hex_key_bytes)
        with pytest.raises(HMACError):
            hmac_algo.verify({"x": 10}, hex_key_bytes, mac + "00")

    # ----------------------------------------------------------------------
    # Async signing
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_sign_async(self, hmac_algo, hex_key_bytes):
        """sign_async should return a valid SHA256 hex digest."""
        mac = await hmac_algo.sign_async({"a": 1}, hex_key_bytes)
        assert isinstance(mac, str)
        assert len(mac) == MAC_HEX_LENGTH

    # ----------------------------------------------------------------------
    # Async verification
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_verify_async_success(self, hmac_algo, hex_key_bytes):
        """verify_async should not raise when MAC is correct."""
        mac = await hmac_algo.sign_async({"a": 1}, hex_key_bytes)
        await hmac_algo.verify_async({"a": 1}, hex_key_bytes, mac)
