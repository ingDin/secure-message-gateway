"""
Unit test suite for FreshnessManager.

@resume
    Validates the foundational behavior of the freshness subsystem, ensuring
    deterministic enforcement of monotonicity rules, increment boundaries,
    drift constraints, and correct async persistence semantics.

@scope
    - monotonicity and replay protection
    - increment validation (min/max)
    - drift enforcement
    - async load/store correctness
    - successful update behavior

@ensures
    Upstream gateway components relying on freshness validation receive
    predictable, stable, and contract-respecting behavior.
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
    @resume
        Provides a factory that constructs a FreshnessManager instance along
        with an isolated counter file.

    @scope
        - deterministic state initialization
        - isolation of freshness.json semantics
        - reproducible async load/store behavior

    @returns
        A tuple (FreshnessManager instance, counter_file path).
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
    """
    @resume
        Contract validation suite for FreshnessManager.

    @scope
        - deterministic rejection of invalid increments
        - predictable monotonicity and replay protection
        - strict enforcement of increment and drift constraints
        - reliable async persistence semantics
        - correct counter progression on successful updates

    @ensures
        The freshness subsystem behaves predictably and supports replay
        protection and state consistency across the gateway pipeline.
    """

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
        """
        @resume
            Validates deterministic rejection of invalid increments.

        @scope
            - replay detection
            - minimum increment enforcement
            - maximum increment enforcement
            - drift constraint enforcement

        @raises
            FreshnessError

        @ensures
            validate_and_update_async signals domain-specific errors for each
            invalid freshness condition.
        """

        # --- Arrange ---
        fm, _ = fm_factory(last)

        # --- Act / Assert ---
        with pytest.raises(FreshnessError) as exc:
            await fm.validate_and_update_async(incoming)

        assert expected_error in str(exc.value)

    # ----------------------------------------------------------------------
    # Success scenario
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_freshness_success(self, fm_factory):
        """
        @resume
            Validates successful counter update when all freshness rules pass.

        @scope
            - monotonic increment
            - valid increment boundaries
            - acceptable drift

        @returns
            Updated counter value persisted to freshness.json.

        @ensures
            validate_and_update_async produces correct counter progression.
        """

        # --- Arrange ---
        fm, counter_file = fm_factory(VALID_LAST)

        # --- Act ---
        await fm.validate_and_update_async(VALID_INCOMING)

        # --- Assert ---
        data = json.loads(counter_file.read_text())
        assert data["counter"] == VALID_INCOMING

    # ----------------------------------------------------------------------
    # Async load
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_load_async(self, fm_factory):
        """
        @resume
            Validates deterministic retrieval of the persisted counter.

        @scope
            - async load semantics
            - correctness of stored counter value

        @returns
            The exact counter value stored in freshness.json.

        @ensures
            load_async returns the correct persisted state.
        """

        # --- Arrange ---
        fm, _ = fm_factory(VALID_LAST)

        # --- Act ---
        value = await fm.load_async()

        # --- Assert ---
        assert value == VALID_LAST

    # ----------------------------------------------------------------------
    # Async store
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_store_async(self, fm_factory):
        """
        @resume
            Validates reliable persistence of updated counter values.

        @scope
            - async write semantics
            - JSON serialization correctness

        @returns
            freshness.json updated with the new counter value.

        @ensures
            store_async writes the correct counter value to disk.
        """

        # --- Arrange ---
        fm, counter_file = fm_factory(VALID_LAST)

        # --- Act ---
        await fm.store_async(STORE_VALUE)

        # --- Assert ---
        data = json.loads(counter_file.read_text())
        assert data["counter"] == STORE_VALUE
