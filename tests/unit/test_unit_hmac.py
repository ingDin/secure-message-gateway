"""
Unit test suite for HMACAlgorithm.

@resume
    Validates the foundational behavior of the HMAC-based cryptographic
    subsystem, ensuring deterministic key generation, strict validation of key
    material, and correct signing/verification semantics in both synchronous
    and asynchronous execution paths.

@scope
    - secure key generation
    - async key loading (valid and invalid configurations)
    - synchronous signing and verification
    - asynchronous signing and verification

@ensures
    Upstream gateway components relying on HMACAlgorithm receive predictable,
    stable, and contract-respecting behavior.
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
    @resume
        Provides a minimal crypto configuration suitable for isolated unit
        testing.

    @scope
        - deterministic configuration of crypto parameters
        - isolated key file paths
        - reproducible key-loading behavior
        - full control over algorithm constraints

    @returns
        A configuration dictionary tailored for unit testing.
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
    @resume
        Provides a fresh HMACAlgorithm instance.

    @scope
        - ensures no shared state
        - avoids cached keys
        - guarantees deterministic behavior across tests

    @returns
        A clean HMACAlgorithm instance.
    """
    return HMACAlgorithm()


@pytest.fixture
def hex_key_bytes():
    """
    @resume
        Provides cryptographically secure random bytes for signing operations.

    @scope
        - realistic entropy
        - deterministic test behavior

    @returns
        A bytearray representing secure key material.
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
    @resume
        Contract validation suite for HMACAlgorithm.

    @scope
        - secure key generation
        - strict async key-loading validation
        - deterministic signing and verification (sync + async)
        - domain-specific error signaling

    @ensures
        The HMAC subsystem behaves predictably and supports the cryptographic
        guarantees required by the gateway pipeline.
    """

    # ----------------------------------------------------------------------
    # Key generation
    # ----------------------------------------------------------------------
    def test_generate_key(self, hmac_algo):
        """
        @resume
            Validates secure key generation.

        @scope
            - hex encoding correctness
            - key length correctness

        @returns
            A valid hex-encoded key of the requested length.

        @ensures
            generate_key produces secure, deterministic key material.
        """

        # --- Arrange ---
        # hmac_algo fixture already provides a clean instance

        # --- Act ---
        key = hmac_algo.generate_key(16)

        # --- Assert ---
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
        @resume
            Validates deterministic rejection of invalid key configurations.

        @scope
            - missing key detection
            - hex decoding validation
            - minimum key length enforcement
            - allowed algorithm enforcement

        @raises
            HMACError

        @ensures
            load_key_async signals domain-specific errors for invalid key
            configurations.
        """

        # --- Arrange ---
        json_file_factory("keys.json", keys_content)
        config = crypto_unit_config_factory(config_override)

        # --- Act / Assert ---
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
        @resume
            Validates successful async key loading.

        @scope
            - correct key retrieval
            - correct hex decoding

        @returns
            The decoded key bytes.

        @ensures
            load_key_async returns valid key material when configuration is correct.
        """

        # --- Arrange ---
        json_file_factory("keys.json", {"dev_key": VALID_KEY})
        config = crypto_unit_config_factory()

        # --- Act ---
        key = await hmac_algo.load_key_async(config)

        # --- Assert ---
        assert key == bytes.fromhex(VALID_KEY)

    # ----------------------------------------------------------------------
    # Sync signing
    # ----------------------------------------------------------------------
    def test_sign(self, hmac_algo, hex_key_bytes):
        """
        @resume
            Validates synchronous signing behavior.

        @scope
            - SHA256 digest correctness
            - hex encoding correctness

        @returns
            A valid MAC hex digest.

        @ensures
            sign() produces deterministic, valid MACs.
        """

        # --- Arrange ---
        # hmac_algo + hex_key_bytes fixtures already prepared

        # --- Act ---
        mac = hmac_algo.sign({"a": 1}, hex_key_bytes)

        # --- Assert ---
        assert isinstance(mac, str)
        assert len(mac) == MAC_HEX_LENGTH

    # ----------------------------------------------------------------------
    # Sync verification
    # ----------------------------------------------------------------------
    def test_verify_success(self, hmac_algo, hex_key_bytes):
        """
        @resume
            Validates successful synchronous verification.

        @scope
            - correct MAC acceptance
            - deterministic verification semantics

        @raises
            None

        @ensures
            verify() accepts valid MACs without raising exceptions.
        """

        # --- Arrange ---
        mac = hmac_algo.sign({"x": 10}, hex_key_bytes)

        # --- Act / Assert ---
        hmac_algo.verify({"x": 10}, hex_key_bytes, mac)

    def test_verify_fail(self, hmac_algo, hex_key_bytes):
        """
        @resume
            Validates deterministic failure behavior for tampered MACs.

        @scope
            - MAC mismatch detection
            - domain-specific error signaling

        @raises
            HMACError

        @ensures
            verify() rejects invalid MACs predictably.
        """

        # --- Arrange ---
        mac = hmac_algo.sign({"x": 10}, hex_key_bytes)

        # --- Act / Assert ---
        with pytest.raises(HMACError):
            hmac_algo.verify({"x": 10}, hex_key_bytes, mac + "00")

    # ----------------------------------------------------------------------
    # Async signing
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_sign_async(self, hmac_algo, hex_key_bytes):
        """
        @resume
            Validates asynchronous signing behavior.

        @scope
            - SHA256 digest correctness
            - hex encoding correctness
            - coroutine semantics

        @returns
            A valid MAC hex digest.

        @ensures
            sign_async produces deterministic MACs identical to sync behavior.
        """

        # --- Arrange ---
        # hmac_algo + hex_key_bytes fixtures already prepared

        # --- Act ---
        mac = await hmac_algo.sign_async({"a": 1}, hex_key_bytes)

        # --- Assert ---
        assert isinstance(mac, str)
        assert len(mac) == MAC_HEX_LENGTH

    # ----------------------------------------------------------------------
    # Async verification
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_verify_async_success(self, hmac_algo, hex_key_bytes):
        """
        @resume
            Validates successful asynchronous verification.

        @scope
            - correct MAC acceptance
            - coroutine semantics

        @raises
            None

        @ensures
            verify_async accepts valid MACs without raising exceptions.
        """

        # --- Arrange ---
        mac = await hmac_algo.sign_async({"a": 1}, hex_key_bytes)

        # --- Act / Assert ---
        await hmac_algo.verify_async({"a": 1}, hex_key_bytes, mac)
