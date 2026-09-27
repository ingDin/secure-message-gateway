"""
@summary
Defines the structured exception hierarchy for the secure-message-gateway.
All error types provide deterministic signaling across schema validation,
cryptographic verification, freshness enforcement, and gateway orchestration.

All exceptions derive from GatewayError to ensure consistent handling,
auditable failure paths, and predictable propagation throughout the pipeline.
"""


class GatewayError(Exception):
    """
    @summary
    Base class for all gateway-related errors. Serves as the root of the
    deterministic error model used throughout the secure-message-gateway.

    @raises
    GatewayError
        Raised indirectly by all specialized gateway exceptions.

    @examples
    >>> raise GatewayError("General gateway failure")
    """


class SchemaError(GatewayError):
    """
    @summary
    Raised when an incoming message violates the required schema.

    @raises
    SchemaError
        When structural, type-level, or required-field constraints are violated.

    @examples
    >>> raise SchemaError("Missing required field 'payload'")
    """


class HMACError(GatewayError):
    """
    @summary
    Raised when HMAC verification fails or key material is invalid.

    @raises
    HMACError
        For signature mismatches, corrupted keys, unsupported algorithms,
        or any deterministic cryptographic failure.

    @examples
    >>> raise HMACError("Invalid HMAC signature")
    """


class FreshnessError(GatewayError):
    """
    @summary
    Raised when monotonic counter freshness checks fail.

    @raises
    FreshnessError
        For replay detection, abnormal increments, drift violations,
        or out-of-range counter updates.

    @examples
    >>> raise FreshnessError("Replay detected: incoming < last")
    """
