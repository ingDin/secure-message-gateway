"""
Unit test suite for KeyManager.

@resume
    Validates the correctness, stability, and failure behavior of the
    key‑rotation subsystem responsible for generating new cryptographic keys,
    archiving old ones, and enforcing rotation interval policies.

@scope
    - rotation interval logic
    - successful key rotation and archival behavior
    - deterministic error propagation from dependent subsystems
    - correct interaction with algorithm registry, key loader, key writer, and audit

@ensures
    Upstream gateway components relying on KeyManager receive predictable,
    safe, and contract‑respecting behavior.
"""

import pytest
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from secure_gateway.key_manager import KeyManager
from secure_gateway.exceptions import HMACError


# ============================================================================
# Test constants
# ============================================================================

OLD_KEY = "old_key_hex"
NEW_KEY = "new_key_hex"

PATCH_ALGO = "secure_gateway.key_manager.ALGORITHM_REGISTRY.get"
PATCH_LOAD = "secure_gateway.key_manager.KeyFileStore.load_async"
PATCH_WRITE = "secure_gateway.key_manager.KeyFileStore.write_async"
PATCH_IO = "aiofiles.open"


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def key_manager_config_factory(tmp_path, config_factory):
    """
    @resume
        Provides a minimal KeyManager configuration with isolated key and audit paths.

    @scope
        - deterministic filesystem behavior
        - isolated key files and archives
        - reproducible rotation interval logic
        - controlled audit logging environment

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

            "audit": {
                "path": str(tmp_path / "audit.log"),
            },

            **(overrides or {})
        })

    return _create


# ============================================================================
# Test suite
# ============================================================================

"""
Unit test suite for KeyManager.

@resume
    Validates the correctness, stability, and failure behavior of the
    key‑rotation subsystem responsible for generating new cryptographic keys,
    archiving old ones, and enforcing rotation interval policies.

@scope
    - rotation interval logic
    - successful key rotation and archival behavior
    - deterministic error propagation from dependent subsystems
    - correct interaction with algorithm registry, key loader, key writer, and audit

@ensures
    Upstream gateway components relying on KeyManager receive predictable,
    safe, and contract‑respecting behavior.
"""

import pytest
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from secure_gateway.key_manager import KeyManager
from secure_gateway.exceptions import HMACError


# ============================================================================
# Test constants
# ============================================================================

OLD_KEY = "old_key_hex"
NEW_KEY = "new_key_hex"

PATCH_ALGO = "secure_gateway.key_manager.ALGORITHM_REGISTRY.get"
PATCH_LOAD = "secure_gateway.key_manager.KeyFileStore.load_async"
PATCH_WRITE = "secure_gateway.key_manager.KeyFileStore.write_async"
PATCH_IO = "aiofiles.open"


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def key_manager_config_factory(tmp_path, config_factory):
    """
    @resume
        Provides a minimal KeyManager configuration with isolated key and audit paths.

    @scope
        - deterministic filesystem behavior
        - isolated key files and archives
        - reproducible rotation interval logic
        - controlled audit logging environment

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
        - correct key archival and replacement behavior
        - strict failure propagation from dependent subsystems
        - isolated validation of algorithm registry, key loader, key writer, and audit

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
            Validates successful key rotation behavior.
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
    # Failure scenarios
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "keys_content,config_override,patch_target,patch_effect",
        [
            # Missing key in keys.json
            ({"prod_key": OLD_KEY}, {}, None, None),

            # Algorithm registry failure
            ({"dev_key": OLD_KEY}, {"algorithm": "UNKNOWN"},
             PATCH_ALGO, HMACError("algorithm lookup failed")),

            # KeyFileStore.load_async failure
            ({"dev_key": OLD_KEY}, {},
             PATCH_LOAD, HMACError("key loading failed")),

            # KeyFileStore.write_async failure
            ({"dev_key": OLD_KEY}, {},
             PATCH_WRITE, HMACError("key writing failed")),

            # Audit log I/O failure
            ({"dev_key": OLD_KEY}, {},
             PATCH_IO, OSError("audit log write failed")),
        ]
    )
    async def test_rotate_async_failures(
        self, key_manager_config_factory, json_file_factory, tmp_path,
        keys_content, config_override, patch_target, patch_effect
    ):
        """
        @resume
            Validates deterministic failure propagation during rotation.
        """

        # --- Arrange ---
        config = key_manager_config_factory(config_override)
        json_file_factory("keys.json", keys_content)

        # --- Act / Assert ---
        if patch_target is None:
            with pytest.raises(HMACError):
                await KeyManager(config).rotate_async()
            return

        with patch(patch_target, side_effect=patch_effect):
            with pytest.raises(HMACError):
                await KeyManager(config).rotate_async()
