# src/secure_gateway/exceptions.py

class GatewayError(Exception):
    """
    Root exception for all gateway-related errors.
    Every module should raise subclasses of this.
    """


class SchemaError(GatewayError):
    """
    Raised when incoming message does not match the required schema.
    Example: missing fields, wrong types, malformed JSON.
    """


class HMACError(GatewayError):
    """
    Raised when HMAC signature is invalid or cannot be verified.
    Covers: wrong key, tampered payload, mismatched signature.
    """


class FreshnessError(GatewayError):
    """
    Raised when anti‑replay freshness checks fail.
    Covers: stale counter, replay attack, invalid counter file.
    """
