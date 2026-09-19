# test_schema.py
import pytest
from schema import validate_schema
from exceptions import SchemaError


class TestSchemaValidator:

    @pytest.fixture
    def valid_message(self):
        return {
            "sender": "clientA",
            "counter": 42,
            "payload": "hello world",
            "hmac": "abcdef123456",
        }

    # ---------------------------------------------------------
    # Positive test
    # ---------------------------------------------------------
    def test_accepts_valid_message(self, valid_message):
        validate_schema(valid_message)

    # ---------------------------------------------------------
    # Negative tests (parametrized)
    # ---------------------------------------------------------
    @pytest.mark.parametrize(
        "invalid_message",
        [
            # Missing required field
            {
                "sender": "clientA",
                "counter": 42,
                "hmac": "abcdef123456",
            },

            # Wrong type
            {
                "sender": "clientA",
                "counter": "not-an-int",
                "payload": "hello world",
                "hmac": "abcdef123456",
            },

            # Extra field
            {
                "sender": "clientA",
                "counter": 42,
                "payload": "hello world",
                "hmac": "abcdef123456",
                "extra": "not allowed",
            },
        ],
    )
    def test_rejects_invalid_messages(self, invalid_message):
        with pytest.raises(SchemaError):
            validate_schema(invalid_message)
