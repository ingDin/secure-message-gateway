"""
@summary
HMAC‑SHA256 cryptographic backend for the secure‑message‑gateway.

Implements:
- secure key generation
- asynchronous key loading with validation
- deterministic signing (sync + async)
- constant‑time verification (sync + async)

All failures raise `HMACError` to ensure deterministic and auditable behavior.
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
    @summary
    HMAC‑SHA256 implementation of the Algorithm interface. Provides deterministic
    signing and verification using stable JSON serialization and constant‑time
    comparison.

    Responsibilities:
    - generate secure random keys
    - load and validate keys from keys.json
    - sign payloads deterministically
    - verify signatures securely
    - provide async wrappers for CPU‑bound operations

    @examples
    >>> algo = HMACAlgorithm()
    >>> key = algo.generate_key(32)
    >>> sig = algo.sign({"msg": "hello"}, bytes.fromhex(key))
    """

    name = "HMAC"

    def generate_key(self, min_len: int) -> str:
        """
        @summary
        Generate a secure random key of at least `min_len` bytes.

        @parameters
        min_len : int
            Minimum required key length in bytes.

        @returns
        str
            Hex‑encoded random key.

        @examples
        >>> key = algo.generate_key(32)
        """
        return os.urandom(min_len).hex()

    async def load_key_async(self, config):
        """
        @summary
        Load and validate the cryptographic key from keys.json.

        @parameters
        config : dict
            Gateway configuration containing crypto settings.

        @returns
        bytes
            Loaded and validated key material.

        @raises
        HMACError
            If the key is missing, invalid, too short, or the algorithm is not allowed.

        @examples
        >>> key = await algo.load_key_async(config)
        """
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

    def sign(self, payload, key):
        """
        @summary
        Compute a deterministic HMAC‑SHA256 signature for the given payload.

        @parameters
        payload : dict
            JSON‑serializable message to sign.
        key : bytes
            Cryptographic key used for signing.

        @returns
        str
            Hex‑encoded HMAC signature.

        @examples
        >>> sig = algo.sign({"id": 1}, key)
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

        @parameters
        payload : dict
            JSON‑serializable message whose signature is being verified.
        key : bytes
            Cryptographic key used for verification.
        expected_hmac : str
            Expected hex‑encoded signature.

        @returns
        None

        @raises
        HMACError
            If the signature does not match.

        @examples
        >>> algo.verify({"id": 1}, key, sig)
        """
        computed = self.sign(payload, key)
        if not hmac.compare_digest(computed, expected_hmac):
            raise HMACError("HMAC verification failed")

    async def sign_async(self, payload, key):
        """
        @summary
        Asynchronous wrapper for deterministic HMAC signing.

        @parameters
        payload : dict
            JSON‑serializable message to sign.
        key : bytes
            Cryptographic key used for signing.

        @returns
        str
            Hex‑encoded HMAC signature.

        @examples
        >>> sig = await algo.sign_async({"id": 1}, key)
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.sign, payload, key)

    async def verify_async(self, payload, key, expected_hmac):
        """
        @summary
        Asynchronous wrapper for constant‑time HMAC verification.

        @parameters
        payload : dict
            Message whose signature is being verified.
        key : bytes
            Cryptographic key used for verification.
        expected_hmac : str
            Expected hex‑encoded signature.

        @returns
        None

        @raises
        HMACError
            If the signature does not match.

        @examples
        >>> await algo.verify_async({"id": 1}, key, sig)
        """
        computed = await self.sign_async(payload, key)
        if not hmac.compare_digest(computed, expected_hmac):
            raise HMACError("HMAC verification failed")
