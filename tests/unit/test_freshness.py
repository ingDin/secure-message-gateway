"""
Unit tests for secure_gateway.freshness.

These tests guarantee deterministic, monotonic, and secure behavior
for the freshness module, ensuring replay protection and correct
counter persistence across gateway operations.
"""

import json
import pytest

from secure_gateway.exceptions import FreshnessError
from secure_gateway.freshness import (
    _load_counter,
    _store_counter,
    verify_freshness,
    update_freshness,
)


# ---------------------------------------------------------
# Tests for _load_counter
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "content, expected",
    [
        ({"counter": 10}, 10),
        ("{invalid json", FreshnessError),
        ({"x": 123}, FreshnessError),
        ({"counter": "abc"}, FreshnessError),
    ],
)
class TestLoadCounter:
    """Tests for loading freshness counters from disk."""

    def test_load_counter(self, write_freshness_fixture, content, expected):
        """Valid counters load correctly; invalid files raise FreshnessError."""
        path = write_freshness_fixture(content)

        if isinstance(expected, type) and issubclass(expected, Exception):
            with pytest.raises(expected):
                _load_counter(path)
        else:
            assert _load_counter(path) == expected


# ---------------------------------------------------------
# Tests for _store_counter
# ---------------------------------------------------------

class TestStoreCounter:
    """Tests for storing freshness counters to disk."""

    def test_store_counter(self, tmp_path):
        """Storing a counter should write correct JSON structure."""
        path = tmp_path / "freshness.json"
        _store_counter(path, 42)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["counter"] == 42


# ---------------------------------------------------------
# Tests for verify_freshness
# ---------------------------------------------------------

class TestVerifyFreshness:
    """Tests for monotonic counter verification."""

    def test_verify_ok(self):
        """Strictly increasing counters should be accepted."""
        verify_freshness(counter=11, last_counter=10)

    def test_verify_equal_replay(self):
        """Equal counters should be rejected as replay."""
        with pytest.raises(FreshnessError):
            verify_freshness(counter=10, last_counter=10)

    def test_verify_lower_replay(self):
        """Lower counters should be rejected as replay."""
        with pytest.raises(FreshnessError):
            verify_freshness(counter=9, last_counter=10)


# ---------------------------------------------------------
# Tests for update_freshness
# ---------------------------------------------------------

class TestUpdateFreshness:
    """Tests for loading, verifying, and updating freshness counters."""

    @pytest.mark.parametrize("content", [{"counter": 10}])
    def test_update_success(self, write_freshness_fixture, content):
        """Valid update should store the new counter."""
        path = write_freshness_fixture(content)
        update_freshness(path, incoming_counter=11)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["counter"] == 11

    @pytest.mark.parametrize("content", [{"counter": 10}])
    def test_update_replay(self, write_freshness_fixture, content):
        """Stale counters should raise FreshnessError."""
        path = write_freshness_fixture(content)
        with pytest.raises(FreshnessError):
            update_freshness(path, incoming_counter=5)

    @pytest.mark.parametrize("content", ["{invalid json"])
    def test_update_load_error(self, write_freshness_fixture, content):
        """Invalid freshness files should propagate FreshnessError."""
        path = write_freshness_fixture(content)
        with pytest.raises(FreshnessError):
            update_freshness(path, incoming_counter=99)
