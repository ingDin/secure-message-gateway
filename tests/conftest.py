import json
import secrets
import pytest
from pathlib import Path
from secure_gateway.logger import AuditLogger

DEFAULT_HMAC_KEY_SIZE = 32


# ---------------------------------------------------------
# Generic JSON writer (reusable for keys.json, freshness.json, etc.)
# ---------------------------------------------------------
def write_json(directory: Path, filename: str, content) -> Path:
    """
    Writes <filename> inside directory.
    - If content is dict → JSON serialize
    - If content is str  → write raw text
    """
    file_path = directory / filename

    if isinstance(content, dict):
        text = json.dumps(content)
    else:
        text = content

    file_path.write_text(text, encoding="utf-8")
    return file_path


# ---------------------------------------------------------
# Backwards-compatible helper for crypto
# ---------------------------------------------------------
def write_keys(directory: Path, content):
    return write_json(directory, "keys.json", content)


# ---------------------------------------------------------
# New helper for freshness
# ---------------------------------------------------------
def write_freshness(directory: Path, content):
    return write_json(directory, "freshness.json", content)


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
def write_keys_fixture(tmp_path):
    def _write(raw_content: str):
        return write_keys(tmp_path, raw_content)
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


# ---------------------------------------------------------
# Fixture: writer for freshness.json (used in tests)
# ---------------------------------------------------------
@pytest.fixture
def write_freshness_fixture(tmp_path):
    def _write(content):
        return write_freshness(tmp_path, content)
    return _write


# ---------------------------------------------------------
# Fixture: enterprise logger environment
# ---------------------------------------------------------
@pytest.fixture
def logger_env(tmp_path):
    class LoggerEnv:
        def __init__(self, base):
            self.log_path = base / "audit.log"
            self.logger = AuditLogger(self.log_path)

        def read_lines(self):
            if not self.log_path.exists():
                return []
            return self.log_path.read_text(encoding="utf-8").splitlines()

        def read_json_lines(self):
            return [json.loads(line) for line in self.read_lines()]

    return LoggerEnv(tmp_path)
