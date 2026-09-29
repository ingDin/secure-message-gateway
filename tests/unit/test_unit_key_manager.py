"""
@summary
Unit test suite for KeyManager.

@resume
    Validates the correctness, stability, and failure behaviour of the
    key‑rotation subsystem responsible for generating new cryptographic keys,
    archiving old ones, and enforcing rotation interval policies.

@scope
    - rotation interval logic
    - successful key rotation and archival behaviour
    - deterministic error propagation from dependent subsystems
    - correct interaction with algorithm registry, key loader, and key writer

@ensures
    Upstream gateway components relying on KeyManager receive predictable,
    safe, and contract‑respecting behaviour.
"""

import pytest
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from secure_gateway.key_manager import KeyManager
from secure_gateway.exceptions import HMACError, KeyError


# ============================================================================
# Test constants
# ============================================================================

OLD_KEY = "old_key_hex"
NEW_KEY = "new_key_hex"

PATCH_ALGO = "secure_gateway.key_manager.ALGORITHM_REGISTRY.get"
PATCH_LOAD = "secure_gateway.key_manager.KeyFileStore.load_async"
PATCH_WRITE = "secure_gateway.key_manager.KeyFileStore.write_async"


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def key_manager_config_factory(tmp_path, config_factory):
    """
    @resume
        Provides a minimal KeyManager configuration with isolated key paths.

    @scope
        - deterministic filesystem behaviour
        - isolated key files and archives
        - reproducible rotation interval logic

    @returns
        A fully configured KeyManager configuration dictionary.
    """
    def _create(overrides=None):
        return config_factory({
            "environment": "dev",

            "crypto": {
                "keys_file": str(tmp_path / "keys.json"),
                "keys_archive": str(tmp_path / "keys_archive.json"),
                "algorithm": "HMAC",
                "min_key_length": 4,
                "rotation_interval_days": 7,
            },

            # audit logging is no longer used by KeyManager.rotate_async
            "audit": {
                "path": str(tmp_path / "audit.log"),
            },

            **(overrides or {})
        })

    return _create


# ============================================================================
# Test suite
# ============================================================================

class TestKeyManager:
    """
    @resume
        Contract validation suite for KeyManager.

    @scope
        - deterministic rotation interval evaluation
        - correct key archival and replacement behaviour
        - strict failure propagation from dependent subsystems
        - isolated validation of algorithm registry, key loader, and key writer

    @ensures
        The key‑rotation subsystem behaves predictably and supports secure
        cryptographic lifecycle management.
    """

    # ----------------------------------------------------------------------
    # Rotation interval logic
    # ----------------------------------------------------------------------
    def test_rotation_needed_true(self, key_manager_config_factory):
        """
        @resume
            Validates rotation interval expiration logic.
        """

        # --- Arrange ---
        config = key_manager_config_factory()
        last = datetime.now(timezone.utc) - timedelta(days=10)

        # --- Act ---
        result = KeyManager.rotation_needed(config, last)

        # --- Assert ---
        assert result is True

    def test_rotation_needed_false(self, key_manager_config_factory):
        """
        @resume
            Validates rotation interval non-expiration logic.
        """

        # --- Arrange ---
        config = key_manager_config_factory()
        last = datetime.now(timezone.utc)

        # --- Act ---
        result = KeyManager.rotation_needed(config, last)

        # --- Assert ---
        assert result is False

    # ----------------------------------------------------------------------
    # Successful rotation
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_rotate_async_success(
        self, key_manager_config_factory, json_file_factory, tmp_path
    ):
        """
        @resume
            Validates successful key rotation behaviour.

        @scope
            - correct archival of old key
            - correct generation and persistence of new key
            - deterministic update of keys.json and keys_archive.json

        @ensures
            rotate_async performs a complete, deterministic key rotation.
        """

        # --- Arrange ---
        config = key_manager_config_factory()
        json_file_factory("keys.json", {"dev_key": OLD_KEY})
        json_file_factory("keys_archive.json", {})

        mock_algo = MagicMock()
        mock_algo.generate_key.return_value = NEW_KEY

        # --- Act ---
        with patch(PATCH_ALGO, return_value=mock_algo):
            await KeyManager(config).rotate_async()

        # --- Assert ---
        updated_keys = json.loads((tmp_path / "keys.json").read_text())
        updated_archive = json.loads((tmp_path / "keys_archive.json").read_text())

        assert updated_keys["dev_key"] == NEW_KEY
        assert OLD_KEY in updated_archive.values()

    # ----------------------------------------------------------------------
    # Async key rotation — failure scenarios
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "keys_content,config_override,patch_target,patch_effect,expected_exception,expected_message",
        [
            # Missing key in keys.json → HMACError
            (
                {"prod_key": OLD_KEY},
                {},
                None,
                None,
                HMACError,
                "Missing key"
            ),

            # Algorithm registry failure → HMACError
            (
                {"dev_key": OLD_KEY},
                {"algorithm": "UNKNOWN"},
                PATCH_ALGO,
                HMACError("algorithm lookup failed"),
                HMACError,
                "Algorithm"
            ),

            # KeyFileStore.load_async failure → KeyError
            (
                {"dev_key": OLD_KEY},
                {},
                PATCH_LOAD,
                KeyError("key loading failed"),
                KeyError,
                "key loading failed"
            ),

            # KeyFileStore.write_async failure → KeyError
            (
                {"dev_key": OLD_KEY},
                {},
                PATCH_WRITE,
                KeyError("key writing failed"),
                KeyError,
                "key writing failed"
            ),
        ]
    )
    async def test_rotate_async_failures(
        self, key_manager_config_factory, json_file_factory, tmp_path,
        keys_content, config_override, patch_target, patch_effect,
        expected_exception, expected_message
    ):
        """
        @resume
            Validates deterministic failure propagation during async key rotation.

        @scope
            - missing key detection in keys.json (HMACError)
            - algorithm registry lookup failures (HMACError)
            - key file loading failures (KeyError)
            - key file writing failures (KeyError)

        @ensures
            rotate_async raises the correct domain‑specific exception type
            (HMACError vs KeyError) for each failure scenario.
        """

        # --- Arrange ---
        config = key_manager_config_factory(config_override)
        json_file_factory("keys.json", keys_content)

        # --- Act / Assert ---
        if patch_target is None:
            # Missing key case: no patching, direct HMACError
            with pytest.raises(expected_exception) as exc:
                await KeyManager(config).rotate_async()
            assert expected_message in str(exc.value)
            return

        with patch(patch_target, side_effect=patch_effect):
            with pytest.raises(expected_exception) as exc:
                await KeyManager(config).rotate_async()
            assert expected_message in str(exc.value)
