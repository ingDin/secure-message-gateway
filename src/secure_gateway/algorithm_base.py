"""
@summary
Defines the abstract base interface for all cryptographic algorithms used by the
secure-message-gateway. This module establishes the core contract that every
cryptographic backend must implement, ensuring deterministic behavior and
consistent method signatures across all implementations.

The interface prevents circular dependencies between:
- algorithms.py (algorithm registry)
- hmac.py (HMAC-SHA256 implementation)

All cryptographic backends must inherit from Algorithm and implement both
synchronous and asynchronous key-handling, signing, and verification methods.
"""


class Algorithm:
    """
    @summary
    Abstract base class for cryptographic algorithms used by the gateway.
    Concrete implementations must provide deterministic signing, verification,
    and key-handling behavior.

    Required methods:
    - generate_key(min_len)
    - load_key_async(config)
    - sign(payload, key)
    - verify(payload, key, expected_hmac)
    - sign_async(payload, key)
    - verify_async(payload, key, expected_hmac)

    @examples
    >>> class MyAlgo(Algorithm):
    ...     def generate_key(self, min_len): ...
    ...     async def load_key_async(self, config): ...
    ...     def sign(self, payload, key): ...
    ...     def verify(self, payload, key, expected_hmac): ...
    ...     async def sign_async(self, payload, key): ...
    ...     async def verify_async(self, payload, key, expected_hmac): ...
    """

    name: str = "BASE"

    def generate_key(self, min_len: int):
        """
        @summary
        Generate a new cryptographic key with a required minimum length.

        @parameters
        min_len : int
            Minimum allowed key length.

        @returns
        bytes
            The generated key material.

        @raises
        NotImplementedError
            Must be implemented by concrete algorithm classes.
        """
        raise NotImplementedError

    async def load_key_async(self, config):
        """
        @summary
        Asynchronously load and validate key material from configuration.

        @parameters
        config : dict
            Configuration section containing key material or key paths.

        @returns
        bytes
            Loaded and validated key material.

        @raises
        NotImplementedError
            Must be implemented by concrete algorithm classes.
        """
        raise NotImplementedError

    def sign(self, payload, key):
        """
        @summary
        Produce a deterministic cryptographic signature for the given payload.

        @parameters
        payload : Any
            The message or data to be signed.
        key : bytes
            The cryptographic key used for signing.

        @returns
        bytes
            The computed signature.

        @raises
        NotImplementedError
            Must be implemented by concrete algorithm classes.
        """
        raise NotImplementedError

    def verify(self, payload, key, expected_hmac):
        """
        @summary
        Verify the signature of a payload using constant-time comparison.

        @parameters
        payload : Any
            The message or data whose signature is being verified.
        key : bytes
            The cryptographic key used for verification.
        expected_hmac : bytes
            The expected signature value.

        @returns
        bool
            True if verification succeeds, False otherwise.

        @raises
        NotImplementedError
            Must be implemented by concrete algorithm classes.
        """
        raise NotImplementedError

    async def sign_async(self, payload, key):
        """
        @summary
        Asynchronous wrapper for deterministic signing.

        @parameters
        payload : Any
            The message or data to be signed.
        key : bytes
            The cryptographic key used for signing.

        @returns
        bytes
            The computed signature.

        @raises
        NotImplementedError
            Must be implemented by concrete algorithm classes.
        """
        raise NotImplementedError

    async def verify_async(self, payload, key, expected_hmac):
        """
        @summary
        Asynchronous wrapper for deterministic signature verification.

        @parameters
        payload : Any
            The message or data whose signature is being verified.
        key : bytes
            The cryptographic key used for verification.
        expected_hmac : bytes
            The expected signature value.

        @returns
        bool
            True if verification succeeds, False otherwise.

        @raises
        NotImplementedError
            Must be implemented by concrete algorithm classes.
        """
        raise NotImplementedError
