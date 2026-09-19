"""
Unit tests for secure_gateway.freshness.

Coverage:
- Counter loading:
    * valid JSON with integer counter
    * invalid JSON
    * missing 'counter' field
    * non-integer counter values

- Counter storing:
    * writes correct JSON structure
    * persists updated counter value

- Freshness verification:
    * accepts strictly increasing counters
    * rejects equal counters (replay)
    * rejects lower counters (replay)

- Freshness update:
    * loads existing counter
    * verifies monotonicity
    * stores updated counter
    * propagates CounterLoadError for invalid files
    * propagates CounterReplayError for stale counters

These tests guarantee deterministic, monotonic, and secure behavior
for the freshness module, ensuring replay protection and correct
counter persistence across gateway operations.
"""

import json
import pytest

from secure_gateway.freshness import (
    _load_counter,
    _store_counter,
    verify_freshness,
    update_freshness,
    CounterLoadError,
    CounterReplayError,
)


# ---------------------------------------------------------
# Tests for _load_counter
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "content, expected",
    [
        ({"counter": 10}, 10),
        ("{invalid json", CounterLoadError),
        ({"x": 123}, CounterLoadError),
        ({"counter": "abc"}, CounterLoadError),
    ],
)
class TestLoadCounter:
    def test_load_counter(self, write_freshness_fixture, content, expected):
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
    def test_store_counter(self, tmp_path):
        path = tmp_path / "freshness.json"
        _store_counter(path, 42)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["counter"] == 42


# ---------------------------------------------------------
# Tests for verify_freshness
# ---------------------------------------------------------

class TestVerifyFreshness:
    def test_verify_ok(self):
        verify_freshness(counter=11, last_counter=10)

    def test_verify_equal_replay(self):
        with pytest.raises(CounterReplayError):
            verify_freshness(counter=10, last_counter=10)

    def test_verify_lower_replay(self):
        with pytest.raises(CounterReplayError):
            verify_freshness(counter=9, last_counter=10)


# ---------------------------------------------------------
# Tests for update_freshness
# ---------------------------------------------------------

class TestUpdateFreshness:
    @pytest.mark.parametrize("content", [{"counter": 10}])
    def test_update_success(self, write_freshness_fixture, content):
        path = write_freshness_fixture(content)
        update_freshness(path, incoming_counter=11)
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["counter"] == 11

    @pytest.mark.parametrize("content", [{"counter": 10}])
    def test_update_replay(self, write_freshness_fixture, content):
        path = write_freshness_fixture(content)
        with pytest.raises(CounterReplayError):
            update_freshness(path, incoming_counter=5)

    @pytest.mark.parametrize("content", ["{invalid json"])
    def test_update_load_error(self, write_freshness_fixture, content):
        path = write_freshness_fixture(content)
        with pytest.raises(CounterLoadError):
            update_freshness(path, incoming_counter=99)
