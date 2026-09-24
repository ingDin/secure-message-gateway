"""
JSON Schema validation for incoming gateway messages.

Ensures strict structural validation before they enter the crypto,
freshness, and audit pipeline.
"""

import jsonschema
from jsonschema import validate, ValidationError
from typing import Dict, Any

from secure_gateway.exceptions import SchemaError


class SchemaValidator:
    """
    Class-based JSON Schema validator for incoming gateway messages.
    Ensures strict structural validation before crypto/freshness/audit.
    """

    # JSON Schema definition (aligned with IncomingMessage)
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

    @staticmethod
    def validate(message: Dict[str, Any]) -> None:
        """
        Validate an incoming gateway message against the JSON schema.

        Raises:
            SchemaError: if the message does not match the required structure.
        """
        try:
            validate(instance=message, schema=SchemaValidator.MESSAGE_SCHEMA)
        except ValidationError as exc:
            raise SchemaError(f"Invalid message schema: {exc.message}") from exc
