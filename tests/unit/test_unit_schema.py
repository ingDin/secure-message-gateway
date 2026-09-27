"""
Unit test suite for SchemaValidator.

@resume
    Validates the correctness, stability, and failure behavior of the
    schema‑validation subsystem responsible for enforcing structural, type,
    and constraint correctness of incoming gateway messages.

@scope
    - successful validation of structurally correct messages
    - structural validation failures (missing required fields)
    - type constraint violations
    - numeric and string constraint enforcement
    - additionalProperties rejection

@ensures
    Upstream gateway components relying on SchemaValidator receive predictable,
    strict, and contract‑respecting behavior before any cryptographic or
    freshness logic is executed.
"""

import pytest
from secure_gateway.schema import SchemaValidator
from secure_gateway.exceptions import SchemaError


# ============================================================================
# Test constants
# ============================================================================

VALID_MESSAGE = {"id": 1, "msg": "ok", "counter": 0, "hmac": "abcd"}

INVALID_MESSAGES = [
    {"id": 1, "msg": "ok", "counter": 0},                     # missing hmac
    {"id": "x", "msg": "ok", "counter": 0, "hmac": "abcd"},   # wrong type
    {"id": -1, "msg": "ok", "counter": 0, "hmac": "abcd"},    # numeric constraint
    {"id": 1, "msg": "", "counter": 0, "hmac": "abcd"},       # string constraint
    {"id": 1, "msg": "ok", "counter": 0, "hmac": "abcd", "extra": 1},  # extra field
]


# ============================================================================
# Test suite
# ============================================================================

class TestSchemaValidator:
    """
    @resume
        Contract validation suite for SchemaValidator.

    @scope
        - deterministic acceptance of valid messages
        - strict rejection of malformed messages
        - precise detection of structural, type, and constraint violations
        - enforcement of additionalProperties rules

    @ensures
        The schema‑validation layer behaves predictably and forms the first,
        immutable gate in the gateway’s security pipeline.
    """

    # ----------------------------------------------------------------------
    # Valid message
    # ----------------------------------------------------------------------
    def test_validate_success(self):
        """
        @resume
            Validates successful schema validation for correct messages.
        """

        # --- Arrange ---
        # VALID_MESSAGE constant already provides a correct payload

        # --- Act ---
        SchemaValidator.validate(VALID_MESSAGE)

        # --- Assert ---
        # No exception means success; nothing else required

    # ----------------------------------------------------------------------
    # Invalid messages
    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("message", INVALID_MESSAGES)
    def test_validate_failures(self, message):
        """
        @resume
            Validates deterministic rejection of invalid messages.
        """

        # --- Arrange ---
        # message parameter provides each malformed payload

        # --- Act / Assert ---
        with pytest.raises(SchemaError):
            SchemaValidator.validate(message)
