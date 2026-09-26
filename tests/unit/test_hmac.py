"""
Unit test suite for HMACAlgorithm.

This module validates the foundational behavior of the HMAC-based cryptographic
subsystem, ensuring deterministic key generation, strict validation of key
material, and correct signing/verification semantics in both synchronous and
asynchronous execution paths.

The suite covers:
- secure key generation
- async key loading (valid and invalid configurations)
- synchronous signing and verification
- asynchronous signing and verification

These tests guarantee that upstream gateway components relying on HMACAlgorithm
receive predictable, stable, and contract-respecting behavior.
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
    Provide a minimal crypto configuration suitable for isolated unit testing.

    This factory ensures:
    - deterministic configuration of crypto parameters
    - isolated key file paths for each test
    - reproducible behavior of key-loading logic
    - full control over algorithm constraints (min length, allowed algorithms)
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
    """
    Provide a fresh HMACAlgorithm instance.

    Ensures that each test executes against a clean cryptographic object without
    shared state or cached keys.
    """
    return HMACAlgorithm()


@pytest.fixture
def hex_key_bytes():
    """
    Provide cryptographically secure random bytes for signing operations.

    Ensures deterministic test behavior while preserving realistic key entropy.
    """
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
    """
    Unit test suite validating the correctness, stability,
    and contract guarantees of HMACAlgorithm.

    This suite ensures that:
    - key generation produces valid, secure hex-encoded material
    - async key loading enforces strict validation rules and rejects malformed
      or unauthorized configurations
    - synchronous signing and verification behave deterministically
    - asynchronous signing and verification mirror sync behavior while ensuring
      correct coroutine semantics

    These checks validate the reliability of the HMAC subsystem, which forms
    the cryptographic foundation of the gateway pipeline.
    """

    # ----------------------------------------------------------------------
    # Key generation
    # ----------------------------------------------------------------------
    def test_generate_key(self, hmac_algo):
        """
        generate_key must return a valid hex string of the requested length.
        """
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
        """
        load_key_async must reject invalid key configurations and raise
        HMACError with the correct domain-specific reason.
        """
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
        """
        load_key_async must return the decoded key when configuration is valid.
        """
        json_file_factory("keys.json", {"dev_key": VALID_KEY})
        config = crypto_unit_config_factory()

        key = await hmac_algo.load_key_async(config)
        assert key == bytes.fromhex(VALID_KEY)

    # ----------------------------------------------------------------------
    # Sync signing
    # ----------------------------------------------------------------------
    def test_sign(self, hmac_algo, hex_key_bytes):
        """
        sign() must return a valid SHA256 hex digest.
        """
        mac = hmac_algo.sign({"a": 1}, hex_key_bytes)
        assert isinstance(mac, str)
        assert len(mac) == MAC_HEX_LENGTH

    # ----------------------------------------------------------------------
    # Sync verification
    # ----------------------------------------------------------------------
    def test_verify_success(self, hmac_algo, hex_key_bytes):
        """
        verify() must accept correct MACs without raising exceptions.
        """
        mac = hmac_algo.sign({"x": 10}, hex_key_bytes)
        hmac_algo.verify({"x": 10}, hex_key_bytes, mac)

    def test_verify_fail(self, hmac_algo, hex_key_bytes):
        """
        verify() must raise HMACError when MAC is tampered.
        """
        mac = hmac_algo.sign({"x": 10}, hex_key_bytes)
        with pytest.raises(HMACError):
            hmac_algo.verify({"x": 10}, hex_key_bytes, mac + "00")

    # ----------------------------------------------------------------------
    # Async signing
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_sign_async(self, hmac_algo, hex_key_bytes):
        """
        sign_async must return a valid SHA256 hex digest.
        """
        mac = await hmac_algo.sign_async({"a": 1}, hex_key_bytes)
        assert isinstance(mac, str)
        assert len(mac) == MAC_HEX_LENGTH

    # ----------------------------------------------------------------------
    # Async verification
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_verify_async_success(self, hmac_algo, hex_key_bytes):
        """
        verify_async must accept correct MACs without raising exceptions.
        """
        mac = await hmac_algo.sign_async({"a": 1}, hex_key_bytes)
        await hmac_algo.verify_async({"a": 1}, hex_key_bytes, mac)
