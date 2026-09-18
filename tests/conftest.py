import json
import secrets
import pytest
from pathlib import Path

DEFAULT_HMAC_KEY_SIZE = 32


# ---------------------------------------------------------
# Single helper: writes keys.json (raw or JSON)
# ---------------------------------------------------------
def write_keys(directory: Path, content) -> Path:
    """
    Writes keys.json inside directory.
    - If content is dict → JSON serialize
    - If content is str  → write raw text
    """
    keys_path = directory / "keys.json"

    if isinstance(content, dict):
        text = json.dumps(content)
    else:
        text = content

    keys_path.write_text(text, encoding="utf-8")
    return keys_path


# ---------------------------------------------------------
# Fixture: directory for HMAC config
# ---------------------------------------------------------
@pytest.fixture
def hmac_config_dir(tmp_path):
    return tmp_path


# ---------------------------------------------------------
# Fixture: full HMAC test environment (returns dict)
# ---------------------------------------------------------
@pytest.fixture
def hmac_test_env(hmac_config_dir, request):
    key_size = getattr(request, "param", DEFAULT_HMAC_KEY_SIZE)
    key_hex = secrets.token_hex(key_size)

    keys_path = write_keys(hmac_config_dir, {"hmac_key": key_hex})

    return {
        "config_dir": hmac_config_dir,
        "key": bytes.fromhex(key_hex),
        "key_hex": key_hex,
        "keys_path": keys_path,
    }


# ---------------------------------------------------------
# Fixture: negative tests (invalid JSON, missing fields)
# ---------------------------------------------------------
@pytest.fixture
def keys_file(tmp_path):
    def _write(raw_content: str):
        write_keys(tmp_path, raw_content)
        return tmp_path
    return _write


# ---------------------------------------------------------
# Fixture: shortcut for accessing only the HMAC key
# ---------------------------------------------------------
@pytest.fixture
def hmac_key(hmac_test_env):
    return hmac_test_env["key"]


# ---------------------------------------------------------
# Fixture: sample payload
# ---------------------------------------------------------
@pytest.fixture
def sample_payload():
    return {"id": 1, "msg": "hello"}
