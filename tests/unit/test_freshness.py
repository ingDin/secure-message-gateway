"""
Unit tests for FreshnessManager.

Covers:
- monotonicity rules
- increment rules
- drift rules
- async load/store
- successful update
"""

import pytest
import json

from secure_gateway.freshness import FreshnessManager
from secure_gateway.exceptions import FreshnessError


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def fm_factory(tmp_path, config_factory):
    """
    Build a FreshnessManager + counter file using config_factory.
    """
    def _create(last_value: int):
        counter_file = tmp_path / "freshness.json"
        counter_file.write_text(json.dumps({"counter": last_value}))

        config = config_factory({
            "freshness": {
                "counter_file": str(counter_file),
                "min_increment": 1,
                "max_increment": 5,
                "max_drift": 2,
                "reject_out_of_range": True,
            }
        })

        return FreshnessManager(counter_file, config), counter_file

    return _create


# ============================================================================
# Test constants
# ============================================================================

VALID_LAST = 10
VALID_INCOMING = 12
STORE_VALUE = 15

ERR_REPLAY = "Replay detected"
ERR_INC_SMALL = "increment too small"
ERR_INC_LARGE = "increment too large"
ERR_DRIFT = "drift too large"


# ============================================================================
# Test suite
# ============================================================================

class TestFreshnessManager:
    """Minimal test suite for FreshnessManager."""

    # ----------------------------------------------------------------------
    # Failure scenarios
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "last,incoming,expected_error",
        [
            (VALID_LAST, 9, ERR_REPLAY),
            (VALID_LAST, 10, ERR_INC_SMALL),
            (VALID_LAST, 16, ERR_INC_LARGE),
            (VALID_LAST, 13, ERR_DRIFT),
        ]
    )
    async def test_freshness_failures(self, fm_factory, last, incoming, expected_error):
        """validate_and_update_async should reject invalid increments."""
        fm, _ = fm_factory(last)

        with pytest.raises(FreshnessError) as exc:
            await fm.validate_and_update_async(incoming)

        assert expected_error in str(exc.value)

    # ----------------------------------------------------------------------
    # Success scenario
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_freshness_success(self, fm_factory):
        """validate_and_update_async should update counter when rules pass."""
        fm, counter_file = fm_factory(VALID_LAST)
        await fm.validate_and_update_async(VALID_INCOMING)

        data = json.loads(counter_file.read_text())
        assert data["counter"] == VALID_INCOMING

    # ----------------------------------------------------------------------
    # Async load
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_load_async(self, fm_factory):
        """load_async should return the stored counter."""
        fm, _ = fm_factory(VALID_LAST)
        assert await fm.load_async() == VALID_LAST

    # ----------------------------------------------------------------------
    # Async store
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_store_async(self, fm_factory):
        """store_async should write the new counter to disk."""
        fm, counter_file = fm_factory(VALID_LAST)
        await fm.store_async(STORE_VALUE)

        data = json.loads(counter_file.read_text())
        assert data["counter"] == STORE_VALUE
