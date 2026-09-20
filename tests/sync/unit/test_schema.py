"""
Unit tests for secure_gateway.schema.

These tests ensure strict validation of incoming messages
before they enter the crypto and freshness pipeline.
"""

import pytest
from secure_gateway.schema import validate_schema
from secure_gateway.exceptions import SchemaError


class TestSchemaValidator:
    """Tests for validating message schema correctness."""

    @pytest.fixture
    def valid_message(self):
        """Fixture providing a valid message structure."""
        return {
            "id": 1,
            "counter": 42,
            "msg": "hello world",
            "hmac": "abcdef123456",
        }

    # ---------------------------------------------------------
    # Positive test
    # ---------------------------------------------------------
    def test_accepts_valid_message(self, valid_message):
        """Valid messages should pass schema validation."""
        validate_schema(valid_message)

    # ---------------------------------------------------------
    # Negative tests (parametrized)
    # ---------------------------------------------------------
    @pytest.mark.parametrize(
        "invalid_message",
        [
            # Missing required field
            {
                "id": 1,
                "counter": 42,
                "hmac": "abcdef123456",
            },

            # Wrong type
            {
                "id": 1,
                "counter": "not-an-int",
                "msg": "hello world",
                "hmac": "abcdef123456",
            },

            # Extra field
            {
                "id": 1,
                "counter": 42,
                "msg": "hello world",
                "hmac": "abcdef123456",
                "extra": "not allowed",
            },
        ],
    )
    def test_rejects_invalid_messages(self, invalid_message):
        """Invalid messages should raise SchemaError."""
        with pytest.raises(SchemaError):
            validate_schema(invalid_message)
