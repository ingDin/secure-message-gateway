"""
Unit tests for SchemaValidator.

Covers:
- successful validation of correct messages
- structural validation failures
- type constraints
- additionalProperties violations
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
    """Minimal test suite for SchemaValidator."""

    # ----------------------------------------------------------------------
    # Valid message
    # ----------------------------------------------------------------------
    def test_validate_success(self):
        """A valid message should pass validation."""
        SchemaValidator.validate(VALID_MESSAGE)

    # ----------------------------------------------------------------------
    # Invalid messages
    # ----------------------------------------------------------------------
    @pytest.mark.parametrize("message", INVALID_MESSAGES)
    def test_validate_failures(self, message):
        """Invalid messages should raise SchemaError."""
        with pytest.raises(SchemaError):
            SchemaValidator.validate(message)
