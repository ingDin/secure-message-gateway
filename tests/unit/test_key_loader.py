"""
Unit test suite for KeyFileStore.

This module validates the correctness, stability, and failure behavior of the
key-loading and key-writing subsystem responsible for reading and persisting
cryptographic key material. It ensures deterministic handling of:

- valid JSON key files
- malformed or corrupted JSON
- missing key files
- I/O failures during async load
- correct JSON serialization during async write
- I/O failures during async write

These tests guarantee that upstream cryptographic components relying on
KeyFileStore receive predictable, safe, and contract-respecting behavior.
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
    """
    Unit test suite validating the correctness and robustness
    of KeyFileStore.

    This suite ensures that:
    - valid key files are parsed correctly
    - corrupted or malformed JSON triggers deterministic failure
    - missing files produce predictable error behavior
    - I/O failures during async load and write are surfaced as HMACError
    - JSON serialization and persistence behave reliably under normal conditions

    These checks validate the reliability of the key-loading subsystem, which
    forms the foundation for secure cryptographic initialization.
    """

    # ----------------------------------------------------------------------
    # Async load — valid JSON
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_load_async_valid(self, json_file_factory):
        """
        load_async must correctly parse and return valid JSON key material.
        """
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
        """
        load_async must raise HMACError for invalid JSON, missing files,
        or I/O failures.

        This ensures deterministic failure behavior and prevents cryptographic
        initialization from proceeding with invalid or unreadable key material.
        """
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
        """
        write_async must serialize and persist JSON content correctly.
        """
        path = tmp_path / "keys.json"
        await KeyFileStore.write_async(path, VALID_KEYS)
        assert json.loads(path.read_text()) == VALID_KEYS

    # ----------------------------------------------------------------------
    # Async write — I/O error
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_write_async_io_error(self):
        """
        write_async must raise HMACError when underlying I/O operations fail.

        This ensures that key persistence failures are surfaced immediately and
        do not result in silent corruption or partial writes.
        """
        with patch(PATCH_IO, side_effect=OSError("io-fail")):
            with pytest.raises(HMACError):
                await KeyFileStore.write_async(Path("x.json"), VALID_KEYS)
