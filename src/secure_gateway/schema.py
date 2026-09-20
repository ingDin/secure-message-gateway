"""
JSON Schema validator for secure‑gateway messages.

Provides strict structural validation for incoming JSON payloads
before they enter the crypto, freshness, and audit pipeline.
"""

import jsonschema
from jsonschema import validate, ValidationError

from secure_gateway.exceptions import SchemaError

# ---------------------------------------------------------
# JSON Schema definition (aligned with IncomingMessage)
# ---------------------------------------------------------
MESSAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer", "minimum": 0},
        "msg": {"type": "string", "minLength": 1},
        "counter": {"type": "integer", "minimum": 0},
        "hmac": {"type": "string", "minLength": 1},
    },
    "required": ["id", "msg", "counter", "hmac"],
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
