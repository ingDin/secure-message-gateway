"""
HMAC-SHA256 crypto backend for the secure gateway.

Implements:
- key generation
- async key loading with validation
- synchronous and asynchronous signing
- synchronous and asynchronous verification
"""

import os
import hmac
import json
import asyncio
from hashlib import sha256
from pathlib import Path

from secure_gateway.exceptions import HMACError
from secure_gateway.key_loader import KeyFileStore

# Import ONLY the base class to avoid circular import
from secure_gateway.algorithm_base import Algorithm


class HMACAlgorithm(Algorithm):
    """
    HMAC-SHA256 implementation of the Algorithm interface.

    Responsibilities:
    - generate secure random keys
    - load and validate keys from keys.json
    - sign payloads deterministically
    - verify signatures securely
    - provide async wrappers for CPU-bound operations
    """

    name = "HMAC"

    # ---------------------------------------------------------
    # Key generation
    # ---------------------------------------------------------
    def generate_key(self, min_len: int) -> str:
        return os.urandom(min_len).hex()

    # ---------------------------------------------------------
    # Key loading (async)
    # ---------------------------------------------------------
    async def load_key_async(self, config):
        env = config["environment"]
        key_name = f"{env}_key"

        keys_path = Path(config["crypto"]["keys_file"])
        keys = await KeyFileStore.load_async(keys_path)

        if key_name not in keys:
            raise HMACError(f"Missing key '{key_name}' in keys.json")

        try:
            key = bytes.fromhex(keys[key_name])
        except ValueError:
            raise HMACError(f"Key '{key_name}' must be hex-encoded")

        min_len = config["crypto"]["min_key_length"]
        if len(key) < min_len:
            raise HMACError(
                f"Key '{key_name}' too short: {len(key)} bytes (min {min_len})"
            )

        algo = config["crypto"]["hmac_algorithm"]
        allowed = config["crypto"]["allowed_algorithms"]
        if algo not in allowed:
            raise HMACError(f"Algorithm '{algo}' not allowed. Allowed: {allowed}")

        return key

    # ---------------------------------------------------------
    # Signing (sync)
    # ---------------------------------------------------------
    def sign(self, payload, key):
        message = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False
        ).encode()

        return hmac.new(key, message, sha256).hexdigest()

    # ---------------------------------------------------------
    # Verification (sync)
    # ---------------------------------------------------------
    def verify(self, payload, key, expected_hmac):
        computed = self.sign(payload, key)
        if not hmac.compare_digest(computed, expected_hmac):
            raise HMACError("HMAC verification failed")

    # ---------------------------------------------------------
    # Signing (async)
    # ---------------------------------------------------------
    async def sign_async(self, payload, key):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.sign, payload, key)

    # ---------------------------------------------------------
    # Verification (async)
    # ---------------------------------------------------------
    async def verify_async(self, payload, key, expected_hmac):
        computed = await self.sign_async(payload, key)
        if not hmac.compare_digest(computed, expected_hmac):
            raise HMACError("HMAC verification failed")
