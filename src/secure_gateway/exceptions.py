"""
Custom exception hierarchy for the secure gateway.

Defines structured error types used across schema validation,
HMAC verification, freshness checks, and gateway orchestration.
"""

class GatewayError(Exception):
    """Base exception for all gateway-related errors."""


class SchemaError(GatewayError):
    """Raised when incoming message violates the required schema."""


class HMACError(GatewayError):
    """Raised when HMAC signature is invalid or cannot be verified."""


class FreshnessError(GatewayError):
    """Raised when monotonic counter freshness checks fail."""
