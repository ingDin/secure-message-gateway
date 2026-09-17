import json
import secrets
import pytest
from pathlib import Path

DEFAULT_HMAC_KEY_SIZE = 16


@pytest.fixture
def hmac_config_dir(tmp_path):
    return tmp_path

@pytest.fixture
def hmac_test_env(hmac_config_dir, request):
    key_size = getattr(request, "param", DEFAULT_HMAC_KEY_SIZE)

    key_hex = secrets.token_hex(key_size)

    keys_file = hmac_config_dir / "keys.json"
    keys_file.write_text(
        json.dumps({"hmac_key": key_hex}),
        encoding="utf-8",
    )

    return hmac_config_dir, bytes.fromhex(key_hex)

@pytest.fixture
def keys_file(tmp_path):
    def _write(content):
        keys_file = tmp_path / "keys.json"
        keys_file.write_text(content, encoding="utf-8")
        return tmp_path

    return _write

@pytest.fixture
def hmac_key(hmac_test_env):
    _, key = hmac_test_env
    return key

@pytest.fixture
def sample_payload():
    return {"id": 1, "msg": "hello"}