# src/secure_gateway/exceptions.py

# ---------------------------------------------------------
# Gateway exception hierarchy
# Centralized error types used across schema, crypto, and freshness.
# ---------------------------------------------------------
class GatewayError(Exception):
    """Base exception for all gateway-related errors."""


class SchemaError(GatewayError):
    """Raised when incoming message violates the required schema."""


class HMACError(GatewayError):
    """Raised when HMAC signature is invalid or cannot be verified."""


class FreshnessError(GatewayError):
    """Raised when monotonic counter freshness checks fail."""
