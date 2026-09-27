"""
@summary
JSON Schema validation for incoming gateway messages. Ensures strict structural
validation before messages enter the crypto, freshness, and audit pipeline.

This validator enforces:
- required fields
- correct types
- minimum constraints
- no additional properties

All failures raise `SchemaError` to ensure deterministic and auditable behavior.
"""

import jsonschema
from jsonschema import validate, ValidationError
from typing import Dict, Any

from secure_gateway.exceptions import SchemaError


class SchemaValidator:
    """
    @summary
    Class‑based JSON Schema validator for incoming gateway messages. Applies
    strict structural validation aligned with the gateway's IncomingMessage
    contract.

    @examples
    >>> SchemaValidator.validate({"id": 1, "msg": "hi", "counter": 10, "hmac": "abc"})
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
        @summary
        Validate an incoming gateway message against the JSON schema.

        @parameters
        message : dict
            Incoming message containing:
            - id : int
            - msg : str
            - counter : int
            - hmac : str

        @returns
        None

        @raises
        SchemaError
            If the message violates the required structure, types, or constraints.

        @examples
        >>> SchemaValidator.validate({
        ...     "id": 42,
        ...     "msg": "hello",
        ...     "counter": 100,
        ...     "hmac": "deadbeef"
        ... })
        """
        try:
            validate(instance=message, schema=SchemaValidator.MESSAGE_SCHEMA)
        except ValidationError as exc:
            raise SchemaError(f"Invalid message schema: {exc.message}") from exc
