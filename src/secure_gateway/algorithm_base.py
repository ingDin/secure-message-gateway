"""
Base interface for all cryptographic algorithms used by the secure gateway.

This module exists to avoid circular imports between:
- algorithms.py (registry)
- hmac.py (concrete implementation)

All crypto backends must inherit from Algorithm.
"""


class Algorithm:
    """
    Abstract base class for crypto algorithms.

    Concrete implementations must override:
    - generate_key()
    - load_key_async()
    - sign()
    - verify()
    - sign_async()
    - verify_async()
    """

    name: str = "BASE"

    def generate_key(self, min_len: int):
        raise NotImplementedError

    async def load_key_async(self, config):
        raise NotImplementedError

    def sign(self, payload, key):
        raise NotImplementedError

    def verify(self, payload, key, expected_hmac):
        raise NotImplementedError

    async def sign_async(self, payload, key):
        raise NotImplementedError

    async def verify_async(self, payload, key, expected_hmac):
        raise NotImplementedError
