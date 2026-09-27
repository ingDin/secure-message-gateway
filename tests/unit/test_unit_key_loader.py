"""
Unit test suite for KeyFileStore.

@resume
    Validates the correctness, stability, and failure behavior of the
    key-loading and key-writing subsystem responsible for reading and
    persisting cryptographic key material.

@scope
    - valid JSON key file parsing
    - malformed or corrupted JSON handling
    - missing file behavior
    - I/O failure propagation during async load
    - correct JSON serialization during async write
    - I/O failure propagation during async write

@ensures
    Upstream cryptographic components relying on KeyFileStore receive
    predictable, safe, and contract-respecting behavior.
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
    @resume
        Contract validation suite for KeyFileStore.

    @scope
        - deterministic JSON parsing
        - strict failure signaling for malformed or missing files
        - reliable async persistence semantics
        - domain-specific error propagation

    @ensures
        The key-loading subsystem behaves predictably and supports secure
        cryptographic initialization.
    """

    # ----------------------------------------------------------------------
    # Async load — valid JSON
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_load_async_valid(self, json_file_factory):
        """
        @resume
            Validates successful async loading of valid JSON key material.

        @scope
            - correct JSON parsing
            - deterministic return of key dictionary

        @returns
            Parsed key material as a Python dict.

        @ensures
            load_async returns valid JSON content exactly as stored.
        """

        # --- Arrange ---
        path = json_file_factory("keys.json", VALID_KEYS)

        # --- Act ---
        result = await KeyFileStore.load_async(path)

        # --- Assert ---
        assert result == VALID_KEYS

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
        @resume
            Validates deterministic rejection of invalid or unreadable key files.

        @scope
            - malformed JSON detection
            - missing file behavior
            - I/O failure propagation

        @raises
            HMACError

        @ensures
            load_async signals domain-specific errors for all invalid load
            conditions, preventing cryptographic initialization with corrupted
            or unreadable key material.
        """

        # --- Arrange ---
        path = tmp_path / "keys.json"

        if callable(setup):
            setup(path)

        # --- Act / Assert ---
        if patch_target is None:
            with pytest.raises(HMACError):
                await KeyFileStore.load_async(path)
            return

        with patch(patch_target, side_effect=patch_effect):
            with pytest.raises(HMACError):
                await KeyFileStore.load_async(path)

    # ----------------------------------------------------------------------
    # Async write — valid JSON
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_write_async_valid(self, tmp_path):
        """
        @resume
            Validates successful async persistence of JSON key material.

        @scope
            - correct JSON serialization
            - reliable write semantics

        @returns
            freshness.json updated with the new key material.

        @ensures
            write_async persists JSON content exactly as provided.
        """

        # --- Arrange ---
        path = tmp_path / "keys.json"

        # --- Act ---
        await KeyFileStore.write_async(path, VALID_KEYS)

        # --- Assert ---
        assert json.loads(path.read_text()) == VALID_KEYS

    # ----------------------------------------------------------------------
    # Async write — I/O error
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_write_async_io_error(self):
        """
        @resume
            Validates deterministic failure behavior when async write operations
            encounter underlying I/O errors.

        @scope
            - I/O failure propagation
            - domain-specific error signaling

        @raises
            HMACError

        @ensures
            write_async never silently corrupts or partially writes key material.
        """

        # --- Arrange ---
        # No file needed; patch will intercept I/O

        # --- Act / Assert ---
        with patch(PATCH_IO, side_effect=OSError("io-fail")):
            with pytest.raises(HMACError):
                await KeyFileStore.write_async(Path("x.json"), VALID_KEYS)
