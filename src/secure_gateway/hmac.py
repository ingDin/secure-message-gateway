"""
@summary
HMAC‑SHA256 cryptographic backend for the secure‑message‑gateway.

Implements:
- secure key generation
- asynchronous key loading with validation
- deterministic signing (sync + async)
- constant‑time verification (sync + async)

Key material validation (missing key, non-hex key) raises `KeyError` to trigger
deterministic key rotation. Cryptographic failures (weak key, disallowed
algorithm, signature mismatch) raise `HMACError`.
"""

import os
import hmac
import json
import asyncio
from hashlib import sha256
from pathlib import Path

from secure_gateway.exceptions import HMACError, KeyError
from secure_gateway.key_loader import KeyFileStore

# Import ONLY the base class to avoid circular import
from secure_gateway.algorithm_base import Algorithm


class HMACAlgorithm(Algorithm):
    """
    @summary
    HMAC‑SHA256 implementation of the Algorithm interface. Provides deterministic
    signing and verification using stable JSON serialization and constant‑time
    comparison.

    Responsibilities:
    - generate secure random keys
    - validate crypto algorithm policy
    - load and validate key material
    - sign payloads deterministically
    - verify signatures securely
    """

    name = "HMAC"

    def __init__(self, config=None):
        """
        @summary
        Initialize the HMAC backend and validate algorithm policy.

        @parameters
        config : dict | None
            Optional gateway configuration. If provided, algorithm policy is
            validated immediately. If not provided, validation occurs when
            load_key_async() is called.
        """
        self.config = config
        if config is not None:
            self._validate_algorithm(config)

    def _validate_algorithm(self, config):
        """
        @summary
        Validate that the configured algorithm is permitted.

        @raises
        HMACError
            If the configured algorithm is not allowed.
        """
        algo = config["crypto"]["hmac_algorithm"]
        allowed = config["crypto"]["allowed_algorithms"]

        if algo not in allowed:
            raise HMACError(f"Algorithm '{algo}' not allowed. Allowed: {allowed}")

    def generate_key(self, min_len: int) -> str:
        """
        @summary
        Generate a secure random key of at least `min_len` bytes.

        @returns
        str
            Hex‑encoded random key.
        """
        return os.urandom(min_len).hex()

    async def load_key_async(self, config):
        """
        @summary
        Load and validate the cryptographic key from keys.json.

        Validation rules:
        - missing key → KeyError
        - non-hex key → KeyError
        - key too short → HMACError
        - disallowed algorithm → HMACError

        @returns
        bytes
            Loaded and validated key material.
        """
        # Validate algorithm policy (if not validated in __init__)
        self._validate_algorithm(config)

        env = config["environment"]
        key_name = f"{env}_key"

        keys_path = Path(config["crypto"]["keys_file"])
        keys = await KeyFileStore.load_async(keys_path)

        if key_name not in keys:
            raise KeyError(f"Missing key '{key_name}' in keys.json")

        # Validate hex encoding
        try:
            key = bytes.fromhex(keys[key_name])
        except ValueError:
            raise KeyError(f"Key '{key_name}' must be hex-encoded")

        # Validate minimum length
        min_len = config["crypto"]["min_key_length"]
        if len(key) < min_len:
            raise HMACError(
                f"Key '{key_name}' too short: {len(key)} bytes (min {min_len})"
            )

        return key

    def sign(self, payload, key):
        """
        @summary
        Compute a deterministic HMAC‑SHA256 signature for the given payload.

        @returns
        str
            Hex‑encoded HMAC signature.
        """
        message = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False
        ).encode()

        return hmac.new(key, message, sha256).hexdigest()

    def verify(self, payload, key, expected_hmac):
        """
        @summary
        Verify the HMAC signature using constant‑time comparison.

        @raises
        HMACError
            If the signature does not match.
        """
        computed = self.sign(payload, key)
        if not hmac.compare_digest(computed, expected_hmac):
            raise HMACError("HMAC verification failed")

    async def sign_async(self, payload, key):
        """
        @summary
        Asynchronous wrapper for deterministic HMAC signing.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.sign, payload, key)

    async def verify_async(self, payload, key, expected_hmac):
        """
        @summary
        Asynchronous wrapper for constant‑time HMAC verification.
        """
        computed = await self.sign_async(payload, key)
        if not hmac.compare_digest(computed, expected_hmac):
            raise HMACError("HMAC verification failed")