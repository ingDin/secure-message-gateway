"""
@resume
    Integration module validating strict JSON schema enforcement across all
    structural validation branches of the gateway.

@scope
    - missing required fields
    - unexpected additional properties
    - incorrect JSON types
    - deterministic SCHEMA_FAIL signalling
    - audit logging of schema violations

@ensures
    Only structurally valid messages proceed to cryptographic and freshness
    subsystems, preserving pipeline integrity.
"""

import pytest
import json
from pathlib import Path
from secure_gateway.gateway import GatewayAsync


class TestIntegrationSchemaInvalid:
    """
    @resume
        Validates rejection of messages missing required fields.

    @scope
        - missing hmac
        - deterministic SCHEMA_FAIL
        - audit logging

    @ensures
        Gateway halts before crypto/freshness execution.
    """

    @pytest.mark.asyncio
    async def test_integration_schema_invalid(self, integration_config_factory):
        # --- Arrange ---
        config = integration_config_factory()
        gateway = GatewayAsync(config)

        msg = {
            "id": 1,
            "counter": 10,
            "msg": "hello"
            # missing hmac
        }

        # --- Act ---
        response = await gateway.process(msg)

        # --- Assert ---
        assert response.status == "error"
        assert response.reason == "SCHEMA_FAIL"

        audit_path = Path(config["audit"]["path"])
        last = json.loads(audit_path.read_text().splitlines()[-1])
        assert last["event"] == "SCHEMA_FAIL"


class TestIntegrationSchemaAdditionalProperties:
    """
    @resume
        Validates rejection of messages containing unexpected fields.

    @scope
        - additionalProperties=False
        - deterministic SCHEMA_FAIL
        - audit logging

    @ensures
        Gateway enforces strict schema contract.
    """

    @pytest.mark.asyncio
    async def test_integration_schema_additional_properties(self, integration_config_factory):
        # --- Arrange ---
        config = integration_config_factory()
        gateway = GatewayAsync(config)

        msg = {
            "id": 1,
            "counter": 10,
            "msg": "hello",
            "hmac": "aa11bb22",
            "unexpected": "not_allowed"
        }

        # --- Act ---
        response = await gateway.process(msg)

        # --- Assert ---
        assert response.status == "error"
        assert response.reason == "SCHEMA_FAIL"

        audit_path = Path(config["audit"]["path"])
        last = json.loads(audit_path.read_text().splitlines()[-1])
        assert last["event"] == "SCHEMA_FAIL"


class TestIntegrationSchemaWrongTypes:
    """
    @resume
        Validates rejection of messages containing incorrect JSON types.

    @scope
        - id wrong type
        - counter wrong type
        - msg wrong type
        - hmac wrong type
        - deterministic SCHEMA_FAIL

    @ensures
        Gateway prevents malformed data from entering security subsystems.
    """

    @pytest.mark.asyncio
    async def test_integration_schema_wrong_types(self, integration_config_factory):
        # --- Arrange ---
        config = integration_config_factory()
        gateway = GatewayAsync(config)

        msg = {
            "id": "wrong",
            "counter": "10",
            "msg": 123,
            "hmac": 999
        }

        # --- Act ---
        response = await gateway.process(msg)

        # --- Assert ---
        assert response.status == "error"
        assert response.reason == "SCHEMA_FAIL"

        audit_path = Path(config["audit"]["path"])
        last = json.loads(audit_path.read_text().splitlines()[-1])
        assert last["event"] == "SCHEMA_FAIL"
