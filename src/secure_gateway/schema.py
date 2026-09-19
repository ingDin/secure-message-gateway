# schema.py
"""
JSON Schema validator for gateway incoming messages.

This module ensures that every incoming message respects the
mandatory structure before entering the crypto and freshness pipeline.
"""

import jsonschema
from jsonschema import validate, ValidationError

from exceptions import SchemaError


# ---------------------------------------------------------
# JSON Schema definition (enterprise-grade, strict)
# ---------------------------------------------------------
MESSAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "sender": {"type": "string", "minLength": 1},
        "counter": {"type": "integer", "minimum": 0},
        "payload": {"type": "string", "minLength": 1},
        "hmac": {"type": "string", "minLength": 1},
    },
    "required": ["sender", "counter", "payload", "hmac"],
    "additionalProperties": False,
}


# ---------------------------------------------------------
# Validator function
# ---------------------------------------------------------
def validate_schema(message: dict) -> None:
    """
    Validate an incoming gateway message against the JSON schema.

    Raises:
        SchemaError: if the message does not match the required structure.
    """
    try:
        validate(instance=message, schema=MESSAGE_SCHEMA)
    except ValidationError as exc:
        raise SchemaError(f"Invalid message schema: {exc.message}") from exc
