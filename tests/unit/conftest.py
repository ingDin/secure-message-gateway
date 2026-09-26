"""
Shared pytest fixtures for the secure-message-gateway test suite.

This module provides reusable, deterministic helpers that support both unit and
integration tests by abstracting common filesystem setup patterns. It ensures:

- consistent creation of temporary JSON files across all test modules
- isolated, reproducible filesystem behavior via pytest's tmp_path fixture
- simplified test authoring by centralizing JSON file generation logic
- reliable encoding and serialization semantics suitable for cryptographic,
  freshness, and audit-related test scenarios

These fixtures form foundational infrastructure for the gateway’s test suite,
enabling clean, maintainable, and predictable test environments across
security‑critical components.
"""

import json
import pytest


@pytest.fixture
def json_file_factory(tmp_path):
    """
    Factory fixture producing JSON files inside the test’s isolated tmp_path.

    This helper ensures:
    - deterministic creation of structured JSON files for tests
    - consistent UTF‑8 encoding across all modules
    - reproducible filesystem behavior independent of environment
    - simplified setup for tests requiring configuration, key material,
      freshness state, or audit log scaffolding

    Parameters:
        filename (str): Name of the JSON file to create.
        content (dict): JSON‑serializable dictionary to write.

    Returns:
        Callable[[str, dict], Path]:
            A factory function that writes the JSON file and returns its full path.
    """
    def _create(filename: str, content: dict):
        path = tmp_path / filename
        path.write_text(json.dumps(content), encoding="utf-8")
        return path

    return _create
