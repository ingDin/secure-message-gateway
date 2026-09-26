"""
Unit test suite for SchemaValidator.

This module validates the correctness, stability, and failure behavior of the
schema-validation subsystem responsible for enforcing structural, type, and
constraint correctness of incoming gateway messages.

The suite covers:
- successful validation of structurally correct messages
- structural validation failures (missing required fields)
- type constraint violations
- numeric and string constraint enforcement
- additionalProperties rejection

These tests guarantee that upstream gateway components relying on SchemaValidator
receive predictable, strict, and contract-respecting behavior before any
cryptographic or freshness logic is executed.
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
    Unit test suite validating the correctness, stability,
    and contract guarantees of SchemaValidator.

    This suite ensures that:
    - valid messages pass validation without raising exceptions
    - invalid messages fail deterministically with SchemaError
    - structural, type, and constraint violations are detected precisely
    - additionalProperties rules are enforced strictly

    These checks validate the reliability of the schema-validation layer, which
    forms the first and immutable gate in the gateway’s security pipeline.
    """

    # ----------------------------------------------------------------------
    # Valid message
    # ----------------------------------------------------------------------
    def test_validate_success(self):
        """
        validate() must accept structurally correct messages without raising errors.
        """
        SchemaValidator.validate(VALID_MESSAGE)

    # ----------------------------------------------------------------------
    # Invalid messages
    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("message", INVALID_MESSAGES)
    def test_validate_failures(self, message):
        """
        validate() must raise SchemaError for any message violating schema rules.

        This ensures deterministic rejection of malformed payloads before they
        reach cryptographic or freshness subsystems.
        """
        with pytest.raises(SchemaError):
            SchemaValidator.validate(message)
