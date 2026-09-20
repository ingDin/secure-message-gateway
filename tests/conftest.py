import json
import secrets
import pytest
from pathlib import Path
from secure_gateway.logger import AuditLoggerAsync
from secure_gateway.gateway import GatewayAsync
from secure_gateway.crypto import sign_message_async, get_hmac_key_async
import pytest_asyncio

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
    """
    Write the HMAC key file (keys.json) into the given directory.

    Parameters:
        directory (Path): Target directory where keys.json will be created.
        content (dict | str): Either a dictionary to be JSON-serialized
                              or a raw string written directly.

    Returns:
        Path: The full path to the written keys.json file.
    """
    return write_json(directory, "keys.json", content)


# ---------------------------------------------------------
# New helper for freshness
# ---------------------------------------------------------

def write_freshness(directory: Path, content):
    """
    Write the freshness counter file (freshness.json) into the given directory.

    Parameters:
        directory (Path): Target directory where freshness.json will be created.
        content (dict | str): Either a dictionary to be JSON-serialized
                              or a raw string written directly.

    Returns:
        Path: The full path to the written freshness.json file.
    """
    return write_json(directory, "freshness.json", content)


# ---------------------------------------------------------
# Fixture: directory for HMAC config
# ---------------------------------------------------------

@pytest.fixture
def hmac_config_dir(tmp_path):
    """
    Provide a temporary directory used as the configuration root
    for HMAC-related tests.

    This directory is intentionally empty; tests populate it with
    keys.json and freshness.json as needed.

    Returns:
        Path: A fresh temporary directory for HMAC configuration.
    """
    return tmp_path


# ---------------------------------------------------------
# Fixture: full HMAC test environment (returns dict)
# ---------------------------------------------------------

@pytest.fixture
def hmac_test_env(hmac_config_dir, request):
    """
    Create a complete HMAC test environment containing:
      - config_dir: directory holding keys.json
      - key: the binary HMAC key (bytes)
      - key_hex: the hex-encoded key string
      - keys_path: the path to keys.json

    The key size can be parametrized via pytest's 'param' mechanism.

    Returns:
        dict: A structured environment used by HMAC-related tests.
    """
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
    """
    Provide a helper for writing malformed or invalid keys.json content.

    This is used in negative test scenarios to verify that the gateway
    correctly rejects invalid key files.

    Returns:
        Callable[[str], Path]: A function that writes raw content
                               directly into keys.json.
    """
    def _write(raw_content: str):
        return write_keys(tmp_path, raw_content)
    return _write


# ---------------------------------------------------------
# Fixture: shortcut for accessing only the HMAC key
# ---------------------------------------------------------

@pytest.fixture
def hmac_key(hmac_test_env):
    """
    Extract the binary HMAC key from the full HMAC test environment.

    This fixture is useful when tests only need the key itself,
    without requiring the entire environment dictionary.

    Returns:
        bytes: The binary HMAC key.
    """
    return hmac_test_env["key"]


# ---------------------------------------------------------
# Fixture: sample payload
# ---------------------------------------------------------

@pytest.fixture
def sample_payload():
    """
    Provide a minimal, valid message payload used in multiple tests.

    This payload intentionally omits the freshness counter and HMAC,
    allowing tests to add them as needed.

    Returns:
        dict: A simple message payload with id and msg fields.
    """
    return {"id": 1, "msg": "hello"}


# ---------------------------------------------------------
# Fixture: writer for freshness.json (used in tests)
# ---------------------------------------------------------

@pytest.fixture
def write_freshness_fixture(tmp_path):
    """
    Provide a helper for writing custom freshness.json content.

    This is used in negative or edge-case tests to simulate invalid
    freshness counters or malformed JSON.

    Returns:
        Callable[[dict | str], Path]: A function that writes content
                                      into freshness.json.
    """
    def _write(content):
        return write_freshness(tmp_path, content)
    return _write


# ---------------------------------------------------------
# Fixture: enterprise logger environment
# ---------------------------------------------------------

@pytest_asyncio.fixture
async def logger_env(tmp_path):
    """
    Provide an isolated async logging environment for tests that verify
    the gateway's audit logging behavior.

    This fixture creates:
      - audit.log: a temporary log file unique to each test
      - AuditLoggerAsync instance: writes structured log entries asynchronously

    Returns:
        LoggerEnvAsync: A wrapper exposing:
            - log_path: Path to audit.log
            - logger:   AuditLoggerAsync instance
            - read_lines():       Read raw log lines (sync)
            - read_json_lines():  Read parsed JSON entries (sync)
    """
    class LoggerEnvAsync:
        def __init__(self, base: Path):
            self.log_path = base / "audit.log"
            self.logger = AuditLoggerAsync(self.log_path)

        def read_lines(self):
            if not self.log_path.exists():
                return []
            return self.log_path.read_text(encoding="utf-8").splitlines()

        def read_json_lines(self):
            return [json.loads(line) for line in self.read_lines()]

    return LoggerEnvAsync(tmp_path)


# ---------------------------------------------------------
# Fixture: config_dir
# ---------------------------------------------------------

@pytest.fixture
def config_dir(tmp_path):
    """
    Create an isolated configuration directory required by the gateway.

    This fixture generates two files:
      - keys.json: contains the static HMAC key used for signing messages.
      - freshness.json: stores the monotonic counter used to detect replay attacks.

    Each test receives a fresh temporary directory, ensuring complete isolation
    and preventing state leakage between tests.

    Returns:
        Path: The temporary directory containing the gateway configuration files.
    """
    (tmp_path / "keys.json").write_text(json.dumps({
        "hmac_key": "a" * 64
    }))
    (tmp_path / "freshness.json").write_text(json.dumps({
        "counter": 0
    }))
    return tmp_path


# ---------------------------------------------------------
# Fixture: gateway
# ---------------------------------------------------------

@pytest.fixture
def gateway(config_dir, tmp_path):
    """
    Provide a fully initialized Gateway instance for integration testing.

    The gateway is configured with:
      - config_dir: directory containing keys.json and freshness.json.
      - audit.log: a temporary log file created per test run.

    This fixture ensures each test interacts with a clean gateway instance
    with isolated configuration and logging.

    Returns:
        Gateway: A fresh gateway instance ready to process messages.
    """
    return GatewayAsync(config_dir=config_dir, log_path=tmp_path / "audit.log")


# ---------------------------------------------------------
# Fixture: build_message
# ---------------------------------------------------------

@pytest.fixture
def build_message():
    """
    Factory for constructing IncomingMessage dictionaries that match
    the gateway's expected schema.

    Parameters:
        id (int): Unique message identifier.
        msg (str): Message payload.
        counter (int): Freshness counter used for replay protection.
        hmac (str): HMAC signature (empty by default).

    Returns:
        Callable[..., dict]: A function that builds message dictionaries
        with the correct structure for gateway processing.
    """
    def _build(id=1, msg="hello", counter=1, hmac=""):
        return {"id": id, "msg": msg, "counter": counter, "hmac": hmac}
    return _build


# ---------------------------------------------------------
# Fixture: compute_hmac
# ---------------------------------------------------------

@pytest_asyncio.fixture
async def compute_hmac(config_dir):
    """
    Async test fixture that returns a callable for computing valid HMACs.

    Loads the gateway's HMAC key asynchronously from config/keys.json,
    then provides an async function `_compute(message)` which:
      - extracts the payload fields (id, msg, counter)
      - computes a deterministic HMAC-SHA256 digest using sign_message_async
      - returns the hex-encoded MAC string

    Used in integration tests to generate correct HMAC values for messages.
    """
    key = await get_hmac_key_async(config_dir)

    async def _compute(message):
        payload = {
            "id": message["id"],
            "msg": message["msg"],
            "counter": message["counter"],
        }
        return await sign_message_async(payload, key)

    return _compute
