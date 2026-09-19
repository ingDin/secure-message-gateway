# src/secure_gateway/crypto.py

import hmac
import json
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict


# ---------------------------------------------------------
# Exception hierarchy for crypto operations
# ---------------------------------------------------------
class CryptoError(Exception):
    """Base exception for crypto-related errors."""


class KeyLoadError(CryptoError):
    """Raised when HMAC key cannot be loaded."""


class HMACVerificationError(CryptoError):
    """Raised when HMAC verification fails."""


# ---------------------------------------------------------
# Internal key loader
# Loads and validates the HMAC key from config/keys.json
# ---------------------------------------------------------
def _load_keys(config_path: Path) -> Dict[str, Any]:
    """
    Load keys from a JSON file.

    :param config_path: Path to keys.json
    :return: dict with keys
    :raises KeyLoadError: if file missing or invalid
    """
    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise KeyLoadError(f"Failed to load keys from {config_path}") from exc

    if "hmac_key" not in data:
        raise KeyLoadError("Missing 'hmac_key' in keys.json")

    return data


# ---------------------------------------------------------
# Public API: return HMAC key as bytes
# Ensures hex decoding and validates key integrity
# ---------------------------------------------------------
def get_hmac_key(config_dir: Path = Path("config")) -> bytes:
    keys_path = config_dir / "keys.json"
    keys = _load_keys(keys_path)

    try:
        key = bytes.fromhex(keys["hmac_key"])
    except (TypeError, ValueError) as exc:
        raise KeyLoadError("Invalid 'hmac_key' in keys.json") from exc

    if not key:
        raise KeyLoadError("Invalid 'hmac_key' in keys.json")

    return key


# ---------------------------------------------------------
# Compute HMAC-SHA256 for a JSON payload
# Payload must NOT contain the hmac field
# ---------------------------------------------------------
def sign_message(payload: Dict[str, Any], key: bytes) -> str:
    """
    Compute HMAC-SHA256 over a JSON-serialized payload.

    :param payload: message dict (without hmac field)
    :param key: HMAC key as bytes
    :return: hex-encoded HMAC
    """
    # Stable JSON encoding ensures deterministic HMAC
    message = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    mac = hmac.new(key, message, sha256).hexdigest()
    return mac


# ---------------------------------------------------------
# Verify HMAC-SHA256 for a given payload
# Uses compare_digest to prevent timing attacks
# ---------------------------------------------------------
def verify_message(payload: Dict[str, Any], key: bytes, expected_hmac: str) -> None:
    """
    Verify HMAC-SHA256 for a given payload.

    :param payload: message dict (without hmac field)
    :param key: HMAC key as bytes
    :param expected_hmac: hex-encoded HMAC to verify against
    :raises HMACVerificationError: if HMAC does not match
    """
    computed = sign_message(payload, key)

    # Constant-time comparison to avoid timing side-channel leaks
    if not hmac.compare_digest(computed, expected_hmac):
        raise HMACVerificationError("HMAC verification failed")
