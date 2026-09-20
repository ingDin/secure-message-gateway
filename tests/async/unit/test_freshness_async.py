"""
Async unit tests for secure_gateway.freshness.

Coverage:
- Async counter loading (aiofiles)
- Async counter storing (aiofiles)
- Async freshness pipeline (load → verify → store)
"""

import pytest
import json

from secure_gateway.exceptions import FreshnessError
from secure_gateway.freshness import (
    _load_counter_async,
    _store_counter_async,
    update_freshness_async,
)


# ---------------------------------------------------------
# Tests for _load_counter_async
# ---------------------------------------------------------

class TestLoadCounterAsync:
    """Tests for asynchronously loading the monotonic counter."""

    @pytest.mark.asyncio
    async def test_load_counter_valid(self, tmp_path, write_freshness_fixture):
        counter_path = write_freshness_fixture({"counter": 5})
        value = await _load_counter_async(counter_path)
        assert value == 5

    @pytest.mark.asyncio
    async def test_load_counter_missing_file(self, tmp_path):
        counter_path = tmp_path / "freshness.json"
        with pytest.raises(FreshnessError):
            await _load_counter_async(counter_path)

    @pytest.mark.asyncio
    async def test_load_counter_invalid_json(self, tmp_path, write_freshness_fixture):
        counter_path = write_freshness_fixture("{invalid json")
        with pytest.raises(FreshnessError):
            await _load_counter_async(counter_path)

    @pytest.mark.asyncio
    async def test_load_counter_missing_field(self, tmp_path, write_freshness_fixture):
        counter_path = write_freshness_fixture({"other": 123})
        with pytest.raises(FreshnessError):
            await _load_counter_async(counter_path)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("content", [
        {"counter": "not-int"},
        {"counter": None},
        {"counter": {}},
        {"counter": []},
    ])
    async def test_load_counter_invalid_value(self, tmp_path, write_freshness_fixture, content):
        counter_path = write_freshness_fixture(content)
        with pytest.raises(FreshnessError):
            await _load_counter_async(counter_path)


# ---------------------------------------------------------
# Tests for _store_counter_async
# ---------------------------------------------------------

class TestStoreCounterAsync:
    """Tests for asynchronously storing the monotonic counter."""

    @pytest.mark.asyncio
    async def test_store_counter_async(self, tmp_path):
        counter_path = tmp_path / "freshness.json"
        await _store_counter_async(counter_path, 42)

        raw = counter_path.read_text(encoding="utf-8")
        data = json.loads(raw)

        assert data["counter"] == 42


# ---------------------------------------------------------
# Tests for update_freshness_async
# ---------------------------------------------------------

class TestUpdateFreshnessAsync:
    """Tests for the full async freshness pipeline."""

    @pytest.mark.asyncio
    async def test_update_freshness_success(self, tmp_path, write_freshness_fixture):
        counter_path = write_freshness_fixture({"counter": 10})
        await update_freshness_async(counter_path, 11)

        data = json.loads(counter_path.read_text(encoding="utf-8"))
        assert data["counter"] == 11

    @pytest.mark.asyncio
    async def test_update_freshness_replay_equal(self, tmp_path, write_freshness_fixture):
        counter_path = write_freshness_fixture({"counter": 10})
        with pytest.raises(FreshnessError):
            await update_freshness_async(counter_path, 10)

    @pytest.mark.asyncio
    async def test_update_freshness_replay_lower(self, tmp_path, write_freshness_fixture):
        counter_path = write_freshness_fixture({"counter": 10})
        with pytest.raises(FreshnessError):
            await update_freshness_async(counter_path, 9)

    @pytest.mark.asyncio
    async def test_update_freshness_invalid_json(self, tmp_path, write_freshness_fixture):
        counter_path = write_freshness_fixture("{invalid json")
        with pytest.raises(FreshnessError):
            await update_freshness_async(counter_path, 5)

    @pytest.mark.asyncio
    async def test_update_freshness_missing_file(self, tmp_path):
        counter_path = tmp_path / "freshness.json"
        with pytest.raises(FreshnessError):
            await update_freshness_async(counter_path, 5)
