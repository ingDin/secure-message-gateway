"""
Shared pytest fixtures for the secure-message-gateway test suite.

@resume
    Provides reusable, deterministic helpers that support both unit and
    integration tests by abstracting common filesystem setup patterns.

@scope
    - consistent creation of temporary JSON files across all test modules
    - isolated, reproducible filesystem behaviour via pytest's tmp_path fixture
    - simplified test authoring through centralized JSON file generation
    - reliable encoding and serialization semantics suitable for cryptographic
      and freshness-related tests
    - robust JSON handling required for audit-focused test scenarios

@ensures
    These fixtures form foundational infrastructure for the gateway’s test
    suite, enabling clean, maintainable, and predictable test environments
    across security‑critical components.
"""

import json
import pytest


@pytest.fixture
def json_file_factory(tmp_path):
    """
    @resume
        Factory fixture producing JSON files inside the test’s isolated tmp_path.

    @scope
        - deterministic creation of structured JSON files
        - consistent UTF‑8 encoding across all modules
        - reproducible filesystem behaviour independent of environment
        - simplified setup for tests requiring configuration, key material,
          freshness state, or audit log scaffolding

    @parameters
        filename (str): Name of the JSON file to create.
        content (dict): JSON‑serializable dictionary to write.

    @returns
        Callable[[str, dict], Path]:
            A factory function that writes the JSON file and returns its full path.

    @ensures
        All test modules can generate isolated, predictable JSON fixtures without
        duplicating boilerplate logic.
    """
    def _create(filename: str, content: dict):
        path = tmp_path / filename
        path.write_text(json.dumps(content), encoding="utf-8")
        return path

    return _create
