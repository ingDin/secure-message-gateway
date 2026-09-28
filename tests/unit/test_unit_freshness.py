"""
Unit test suite for FreshnessManager (DRY version).

@resume
    Validates observable behavior of the freshness subsystem:
    deterministic bootstrap, strict monotonicity rules, drift and increment
    constraints, and correct persistence semantics.

@scope
    - bootstrap modes (file, auto, numeric)
    - reset_on_start behavior
    - monotonicity and replay protection
    - increment validation (min/max)
    - drift enforcement
    - persistence correctness

@ensures
    FreshnessManager behaves predictably and contract-respecting under all
    supported configurations.
"""

import pytest
import json

from secure_gateway.freshness import FreshnessManager
from secure_gateway.exceptions import FreshnessError


# ============================================================================
# Shared helpers (DRY)
# ============================================================================

def make_config(config_factory, counter_file, **overrides):
    """Create a freshness config with overrides."""
    base = {
        "counter_file": str(counter_file),
        "min_increment": 1,
        "max_increment": 5,
        "max_drift": 2,
        "reject_out_of_range": True,
        "initial_counter": "auto",
        "reset_on_start": False,
    }
    base.update(overrides)
    return config_factory({"freshness": base})


def read_counter(counter_file):
    """Read counter from freshness.json."""
    return json.loads(counter_file.read_text())["counter"]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def fm_factory(tmp_path, config_factory):
    """
    Provides a FreshnessManager + isolated freshness.json file.
    """
    def _create(last_value: int, extra_cfg=None):
        counter_file = tmp_path / "freshness.json"
        counter_file.write_text(json.dumps({"counter": last_value}))

        config = make_config(config_factory, counter_file, **(extra_cfg or {}))
        return FreshnessManager(counter_file, config), counter_file

    return _create


# ============================================================================
# Constants
# ============================================================================

VALID_LAST = 10
VALID_INCOMING = 12

ERR_REPLAY = "Replay detected"
ERR_INC_SMALL = "increment too small"
ERR_INC_LARGE = "increment too large"
ERR_DRIFT = "drift too large"


# ============================================================================
# Test suite
# ============================================================================

class TestFreshnessManager:

    # ----------------------------------------------------------------------
    # Bootstrap: file exists overrides config
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_bootstrap_existing_file_overrides_config(self, fm_factory):
        # --- Arrange ---
        fm, counter_file = fm_factory(VALID_LAST, {"initial_counter": 999})

        # --- Act ---
        await fm.bootstrap_async(1)

        # --- Assert ---
        assert fm.counter == VALID_LAST
        assert read_counter(counter_file) == VALID_LAST

    # ----------------------------------------------------------------------
    # Bootstrap: auto mode
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_bootstrap_auto_uses_incoming(self, tmp_path, config_factory):
        # --- Arrange ---
        counter_file = tmp_path / "freshness.json"
        config = make_config(config_factory, counter_file, initial_counter="auto")
        fm = FreshnessManager(counter_file, config)

        # --- Act ---
        await fm.bootstrap_async(42)

        # --- Assert ---
        assert fm.counter == 42
        assert read_counter(counter_file) == 42

    # ----------------------------------------------------------------------
    # Bootstrap: numeric mode
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_bootstrap_numeric_uses_config_value(self, tmp_path, config_factory):
        # --- Arrange ---
        counter_file = tmp_path / "freshness.json"
        config = make_config(config_factory, counter_file, initial_counter=100)
        fm = FreshnessManager(counter_file, config)

        # --- Act ---
        await fm.bootstrap_async(1)

        # --- Assert ---
        assert fm.counter == 100
        assert read_counter(counter_file) == 100

    # ----------------------------------------------------------------------
    # Bootstrap: reset_on_start + auto
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_reset_on_start_auto_bootstrap(self, tmp_path, config_factory):
        # --- Arrange ---
        counter_file = tmp_path / "freshness.json"
        counter_file.write_text(json.dumps({"counter": 999}))

        config = make_config(config_factory, counter_file,
                             initial_counter="auto", reset_on_start=True)

        # --- Act ---
        fm = FreshnessManager(counter_file, config)

        # --- Assert ---
        assert not counter_file.exists()

        # --- Act ---
        await fm.bootstrap_async(7)

        # --- Assert ---
        assert fm.counter == 7
        assert read_counter(counter_file) == 7

    # ----------------------------------------------------------------------
    # Bootstrap: reset_on_start + numeric
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_reset_on_start_numeric_bootstrap(self, tmp_path, config_factory):
        # --- Arrange ---
        counter_file = tmp_path / "freshness.json"
        counter_file.write_text(json.dumps({"counter": 999}))

        config = make_config(config_factory, counter_file,
                             initial_counter=100, reset_on_start=True)

        # --- Act ---
        fm = FreshnessManager(counter_file, config)

        # --- Assert ---
        assert not counter_file.exists()

        # --- Act ---
        await fm.bootstrap_async(7)

        # --- Assert ---
        assert fm.counter == 100
        assert read_counter(counter_file) == 100

    # ----------------------------------------------------------------------
    # Monotonic rule failures (DRY via parametrization)
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "last,incoming,expected",
        [
            (VALID_LAST, 9, ERR_REPLAY),
            (VALID_LAST, 10, ERR_INC_SMALL),
            (VALID_LAST, 16, ERR_INC_LARGE),
            (VALID_LAST, 13, ERR_DRIFT),
        ]
    )
    async def test_validate_rules_failures(self, fm_factory, last, incoming, expected):
        # --- Arrange ---
        fm, _ = fm_factory(last)
        fm.counter = last

        # --- Act / Assert ---
        with pytest.raises(FreshnessError) as exc:
            fm.validate_rules(incoming)

        assert expected in str(exc.value)

    # ----------------------------------------------------------------------
    # Monotonic rule success
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_validate_rules_success(self, fm_factory):
        # --- Arrange ---
        fm, _ = fm_factory(VALID_LAST)
        fm.counter = VALID_LAST

        # --- Act ---
        fm.validate_rules(VALID_INCOMING)

        # --- Assert ---
        assert True

    # ----------------------------------------------------------------------
    # Orchestrator: counter None → no update
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_validate_and_update_does_not_update_when_counter_is_none(self, fm_factory):
        # --- Arrange ---
        fm, counter_file = fm_factory(VALID_LAST)

        # --- Act ---
        await fm.validate_and_update_async(VALID_INCOMING)

        # --- Assert ---
        assert fm.counter == VALID_LAST
        assert read_counter(counter_file) == VALID_LAST

    # ----------------------------------------------------------------------
    # Orchestrator: counter set → update
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_validate_and_update_updates_after_bootstrap(self, fm_factory):
        # --- Arrange ---
        fm, counter_file = fm_factory(VALID_LAST)
        fm.counter = VALID_LAST

        # --- Act ---
        await fm.validate_and_update_async(VALID_INCOMING)

        # --- Assert ---
        assert fm.counter == VALID_INCOMING
        assert read_counter(counter_file) == VALID_INCOMING
