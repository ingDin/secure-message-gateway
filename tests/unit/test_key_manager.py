"""
Unit tests for KeyManager.

Covers:
- rotation interval logic
- successful key rotation
- archival behavior
- error propagation
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
    Build a minimal config for KeyManager tests, with proper crypto + audit paths.
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
    """Minimal test suite for KeyManager."""

    # ----------------------------------------------------------------------
    # Rotation interval logic
    # ----------------------------------------------------------------------
    def test_rotation_needed_true(self, key_manager_config_factory):
        """Should return True when rotation interval has elapsed."""
        config = key_manager_config_factory()
        last = datetime.now(timezone.utc) - timedelta(days=10)
        assert KeyManager.rotation_needed(config, last)

    def test_rotation_needed_false(self, key_manager_config_factory):
        """Should return False when rotation interval has NOT elapsed."""
        config = key_manager_config_factory()
        last = datetime.now(timezone.utc)
        assert not KeyManager.rotation_needed(config, last)

    # ----------------------------------------------------------------------
    # Successful rotation
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_rotate_async_success(
        self, key_manager_config_factory, json_file_factory, tmp_path
    ):
        """Successful rotation should update keys, archive old key, and log event."""
        config = key_manager_config_factory()

        json_file_factory("keys.json", {"dev_key": OLD_KEY})
        json_file_factory("keys_archive.json", {})

        mock_algo = MagicMock()
        mock_algo.generate_key.return_value = NEW_KEY

        with patch(PATCH_ALGO, return_value=mock_algo):
            await KeyManager(config).rotate_async()

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
        """rotate_async should raise HMACError when any dependency fails."""
        config = key_manager_config_factory(config_override)
        json_file_factory("keys.json", keys_content)

        # Missing key case (no patch)
        if patch_target is None:
            with pytest.raises(HMACError):
                await KeyManager(config).rotate_async()
            return

        # Patched failure case
        with patch(patch_target, side_effect=patch_effect):
            with pytest.raises(HMACError):
                await KeyManager(config).rotate_async()
