"""
Shared pytest fixtures for the test suite.

Provides:
- json_file_factory: helper for writing JSON files in tmp_path
"""

import json
import pytest


# ============================================================================
# JSON file factory
# ============================================================================

@pytest.fixture
def json_file_factory(tmp_path):
    """
    Create a JSON file inside tmp_path and return its path.

    Parameters:
        filename (str): Name of the file to create.
        content (dict): JSON-serializable content to write.

    Returns:
        Path: Full path to the created file.
    """
    def _create(filename: str, content: dict):
        path = tmp_path / filename
        path.write_text(json.dumps(content), encoding="utf-8")
        return path

    return _create
