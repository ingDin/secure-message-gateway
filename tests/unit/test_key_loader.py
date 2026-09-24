"""
Unit tests for KeyFileStore.

Covers:
- async load (valid JSON)
- async load (invalid JSON)
- async load (missing file)
- async load (I/O error)
- async write (valid JSON)
- async write (I/O error)
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch

from secure_gateway.key_loader import KeyFileStore
from secure_gateway.exceptions import HMACError


# ============================================================================
# Test constants
# ============================================================================

VALID_KEYS = {"dev_key": "hex_key"}
INVALID_JSON = "{invalid json}"
PATCH_IO = "aiofiles.open"


# ============================================================================
# Test suite
# ============================================================================

class TestKeyFileStore:
    """Minimal test suite for KeyFileStore."""

    # ----------------------------------------------------------------------
    # Async load — valid JSON
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_load_async_valid(self, json_file_factory):
        """Valid JSON should be loaded correctly."""
        path = json_file_factory("keys.json", VALID_KEYS)
        assert await KeyFileStore.load_async(path) == VALID_KEYS

    # ----------------------------------------------------------------------
    # Async load — failure scenarios
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "setup,patch_target,patch_effect",
        [
            # Invalid JSON
            (lambda p: p.write_text(INVALID_JSON), None, None),

            # Missing file
            (None, None, None),

            # I/O error
            (lambda p: p.write_text(json.dumps({"x": 1})), PATCH_IO, OSError("io-fail")),
        ]
    )
    async def test_load_async_failures(self, tmp_path, setup, patch_target, patch_effect):
        """load_async should raise HMACError for invalid JSON, missing files, or I/O errors."""
        path = tmp_path / "keys.json"

        # Prepare file if needed
        if callable(setup):
            setup(path)

        # No patch → expect failure directly
        if patch_target is None:
            with pytest.raises(HMACError):
                await KeyFileStore.load_async(path)
            return

        # Patched failure case
        with patch(patch_target, side_effect=patch_effect):
            with pytest.raises(HMACError):
                await KeyFileStore.load_async(path)

    # ----------------------------------------------------------------------
    # Async write — valid JSON
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_write_async_valid(self, tmp_path):
        """write_async should serialize and write JSON content."""
        path = tmp_path / "keys.json"
        await KeyFileStore.write_async(path, VALID_KEYS)
        assert json.loads(path.read_text()) == VALID_KEYS

    # ----------------------------------------------------------------------
    # Async write — I/O error
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_write_async_io_error(self):
        """write_async should raise HMACError when aiofiles.open fails."""
        with patch(PATCH_IO, side_effect=OSError("io-fail")):
            with pytest.raises(HMACError):
                await KeyFileStore.write_async(Path("x.json"), VALID_KEYS)
