"""
Asynchronous HMAC utilities for the secure gateway.

Provides non‑blocking key loading, async wrappers for CPU‑bound
HMAC operations, and compatibility with the gateway's async pipeline.
"""

import hmac
import json
import asyncio
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict
import aiofiles

from secure_gateway.exceptions import HMACError


# ---------------------------------------------------------
# Async key loader (I/O non-blocking)
# ---------------------------------------------------------
async def _load_keys_async(config_path: Path) -> Dict[str, Any]:
    """
    Asynchronously load and parse the HMAC keys JSON file.

    This function performs non-blocking file I/O using aiofiles,
    allowing the gateway to continue processing other tasks while
    the keys.json file is being read.

    Parameters
    ----------
    config_path : Path
        Path to the keys.json file.

    Returns
    -------
    Dict[str, Any]
        Parsed JSON dictionary containing the HMAC key.

    Raises
    ------
    HMACError
        If the file cannot be read, parsed, or does not contain
        the required 'hmac_key' field.
    """
    try:
        async with aiofiles.open(config_path, "r", encoding="utf-8") as f:
            raw = await f.read()
            data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise HMACError(f"Failed to load keys from {config_path}") from exc

    if "hmac_key" not in data:
        raise HMACError("Missing 'hmac_key' in keys.json")

    return data


async def get_hmac_key_async(config_dir: Path = Path("config")) -> bytes:
    """
    Asynchronously load and validate the HMAC key from config/keys.json.

    This function wraps `_load_keys_async` and performs hex decoding
    of the key. It ensures the key is valid and non-empty.

    Parameters
    ----------
    config_dir : Path, optional
        Directory containing keys.json. Defaults to 'config'.

    Returns
    -------
    bytes
        The decoded HMAC key as raw bytes.

    Raises
    ------
    HMACError
        If the key is missing, invalid, or cannot be decoded.
    """
    keys_path = config_dir / "keys.json"
    keys = await _load_keys_async(keys_path)

    try:
        key = bytes.fromhex(keys["hmac_key"])
    except (TypeError, ValueError) as exc:
        raise HMACError("Invalid 'hmac_key' in keys.json") from exc

    if not key:
        raise HMACError("Invalid 'hmac_key' in keys.json")

    return key


# ---------------------------------------------------------
# Sync crypto functions (unchanged)
# ---------------------------------------------------------
def sign_message(payload: Dict[str, Any], key: bytes) -> str:
    """
    Compute HMAC-SHA256 for a JSON payload (synchronous version).

    This function performs deterministic JSON serialization and
    computes the HMAC digest using the provided key.

    Parameters
    ----------
    payload : Dict[str, Any]
        Message dictionary WITHOUT the 'hmac' field.
    key : bytes
        Raw HMAC key.

    Returns
    -------
    str
        Hex-encoded HMAC digest.
    """
    message = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    mac = hmac.new(key, message, sha256).hexdigest()
    return mac


def verify_message(payload: Dict[str, Any], key: bytes, expected_hmac: str) -> None:
    """
    Verify HMAC-SHA256 for a given payload (synchronous version).

    Uses constant-time comparison to prevent timing attacks.

    Parameters
    ----------
    payload : Dict[str, Any]
        Message dictionary WITHOUT the 'hmac' field.
    key : bytes
        Raw HMAC key.
    expected_hmac : str
        Hex-encoded HMAC provided by the sender.

    Raises
    ------
    HMACError
        If the computed HMAC does not match the expected value.
    """
    computed = sign_message(payload, key)
    if not hmac.compare_digest(computed, expected_hmac):
        raise HMACError("HMAC verification failed")


# ---------------------------------------------------------
# Async wrappers using thread executor
# ---------------------------------------------------------
async def sign_message_async(payload: Dict[str, Any], key: bytes) -> str:
    """
    Asynchronously compute HMAC-SHA256 using a thread executor.

    Crypto operations are CPU-bound and cannot be awaited directly.
    This wrapper offloads the synchronous `sign_message` function
    to a background thread so the asyncio event loop remains free.

    Parameters
    ----------
    payload : Dict[str, Any]
        Message dictionary WITHOUT the 'hmac' field.
    key : bytes
        Raw HMAC key.

    Returns
    -------
    str
        Hex-encoded HMAC digest.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, sign_message, payload, key)


async def verify_message_async(payload: Dict[str, Any], key: bytes, expected_hmac: str) -> None:
    """
    Asynchronously verify HMAC-SHA256 using a thread executor.

    This function wraps the synchronous verification logic and
    ensures the event loop is not blocked by CPU-bound operations.

    Parameters
    ----------
    payload : Dict[str, Any]
        Message dictionary WITHOUT the 'hmac' field.
    key : bytes
        Raw HMAC key.
    expected_hmac : str
        Hex-encoded HMAC provided by the sender.

    Raises
    ------
    HMACError
        If the computed HMAC does not match the expected value.
    """
    computed = await sign_message_async(payload, key)
    if not hmac.compare_digest(computed, expected_hmac):
        raise HMACError("HMAC verification failed")
