"""
Async unit tests for secure_gateway.crypto.

Coverage:
- Async HMAC key loading (aiofiles)
- Async HMAC signing (thread executor)
- Async HMAC verification (thread executor)

These tests validate the async wrappers and ensure that CPU-bound
crypto operations do not block the asyncio event loop.
"""

import pytest
import pytest_asyncio

from secure_gateway.exceptions import HMACError
from secure_gateway.crypto import (
    get_hmac_key_async,
    sign_message_async,
    verify_message_async,
)


# ---------------------------------------------------------
# Tests for get_hmac_key_async (FULL, pentru că logica e async)
# ---------------------------------------------------------

class TestLoadHmacKeyAsync:
    """Tests for asynchronously loading and validating HMAC keys."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("hmac_test_env", [16, 64], indirect=True)
    async def test_load_key_async(self, hmac_test_env):
        """Valid HMAC keys should load correctly via async loader."""
        config_dir = hmac_test_env["config_dir"]
        expected_key = hmac_test_env["key"]

        key = await get_hmac_key_async(config_dir)

        assert isinstance(key, bytes)
        assert key == expected_key

    @pytest.mark.asyncio
    async def test_load_key_file_missing_async(self, tmp_path):
        """Missing keys.json should raise HMACError."""
        with pytest.raises(HMACError):
            await get_hmac_key_async(tmp_path)

    @pytest.mark.asyncio
    async def test_load_key_invalid_json_async(self, write_keys_fixture):
        """Invalid JSON should raise HMACError."""
        config_dir = write_keys_fixture("{invalid json")

        with pytest.raises(HMACError):
            await get_hmac_key_async(config_dir)

    @pytest.mark.asyncio
    async def test_load_key_missing_hmac_key_async(self, write_keys_fixture):
        """Missing 'hmac_key' field should raise HMACError."""
        config_dir = write_keys_fixture('{"other_key": "abc"}')

        with pytest.raises(HMACError):
            await get_hmac_key_async(config_dir)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "content",
        [
            '{"hmac_key": "not-hex"}',
            '{"hmac_key": ""}',
            '{"hmac_key": null}',
            '{"hmac_key": 123}',
        ],
    )
    async def test_load_key_invalid_hmac_key_async(self, write_keys_fixture, content):
        """Invalid hmac_key values should raise HMACError."""
        config_dir = write_keys_fixture(content)

        with pytest.raises(HMACError):
            await get_hmac_key_async(config_dir)


# ---------------------------------------------------------
# Tests for sign_message_async (MINIMAL, doar wrapper + propagare)
# ---------------------------------------------------------

class TestSignMessageAsync:
    """Tests for async HMAC signing using thread executor."""

    @pytest.mark.asyncio
    async def test_sign_message_async_basic(self, hmac_key, sample_payload):
        """Async signing should produce a valid 64‑char hex digest."""
        mac = await sign_message_async(sample_payload, hmac_key)

        assert isinstance(mac, str)
        assert len(mac) == 64
        assert all(c in "0123456789abcdef" for c in mac)

    @pytest.mark.asyncio
    async def test_sign_message_async_preserves_sync_logic(self, hmac_key):
        """
        Async wrapper should preserve sync determinism:
        same payload → same MAC, indiferent de ordinea cheilor.
        """
        payload_1 = {"msg": "hello", "timestamp": 123}
        payload_2 = {"timestamp": 123, "msg": "hello"}

        mac1 = await sign_message_async(payload_1, hmac_key)
        mac2 = await sign_message_async(payload_2, hmac_key)

        assert mac1 == mac2


# ---------------------------------------------------------
# Tests for verify_message_async (MINIMAL, success + 2 failure paths)
# ---------------------------------------------------------

class TestVerifyMessageAsync:
    """Tests for async HMAC verification."""

    @pytest_asyncio.fixture
    async def valid_mac_async(self, hmac_key, sample_payload):
        """Fixture providing a valid MAC for the sample payload."""
        return await sign_message_async(sample_payload, hmac_key)

    @pytest.mark.asyncio
    async def test_verify_message_async_success(
        self, hmac_key, sample_payload, valid_mac_async
    ):
        """Valid MAC and payload should verify without error."""
        await verify_message_async(sample_payload, hmac_key, valid_mac_async)

    @pytest.mark.asyncio
    async def test_verify_message_async_failure_when_mac_is_modified(
        self, hmac_key, sample_payload, valid_mac_async
    ):
        """Modifying the MAC should cause async verification failure."""
        bad_mac = valid_mac_async[:-1] + ("0" if valid_mac_async[-1] != "0" else "1")

        with pytest.raises(HMACError):
            await verify_message_async(sample_payload, hmac_key, bad_mac)

    @pytest.mark.asyncio
    async def test_verify_message_async_failure_when_payload_is_modified(
        self, hmac_key, sample_payload, valid_mac_async
    ):
        """Modifying the payload should cause async verification failure."""
        tampered_payload = {**sample_payload, "msg": "tampered"}

        with pytest.raises(HMACError):
            await verify_message_async(tampered_payload, hmac_key, valid_mac_async)
