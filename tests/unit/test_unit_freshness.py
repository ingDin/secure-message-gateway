"""
@summary
Unit test suite for FreshnessManager.

@resume
    Validates observable behaviour of the freshness subsystem, including
    deterministic bootstrap behaviour, strict monotonicity rules, increment
    and drift constraints, and correct persistence semantics.

@scope
    - bootstrap modes (existing file, auto, numeric)
    - reset_on_start behaviour
    - monotonicity and replay protection
    - increment validation (min/max)
    - drift enforcement
    - persistence correctness
    - orchestrator behaviour (bootstrap + validate + update)

@ensures
    FreshnessManager behaves predictably and adheres to its contract under all
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
    """
    @resume
        Constructs a freshness configuration with optional overrides.

    @scope
        - base freshness configuration
        - override injection for targeted tests

    @ensures
        Each test receives an isolated, deterministic configuration.
    """
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
    """
    @resume
        Reads the persisted freshness counter from disk.

    @scope
        - direct JSON read
        - deterministic counter extraction

    @ensures
        Tests can assert persistence correctness.
    """
    return json.loads(counter_file.read_text())["counter"]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def fm_factory(tmp_path, config_factory):
    """
    @resume
        Provides a FreshnessManager instance and an isolated freshness.json file.

    @scope
        - isolated filesystem
        - configurable initial counter
        - DRY construction for multiple tests

    @ensures
        Each test receives a clean FreshnessManager + counter file pair.
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
    """
    @resume
        Validates deterministic bootstrap behaviour, monotonicity rules,
        increment constraints, drift enforcement, and persistence semantics.

    @scope
        - bootstrap from existing file
        - auto bootstrap using incoming value
        - numeric bootstrap using configured value
        - reset_on_start behaviour
        - monotonicity and replay protection
        - increment and drift rule enforcement
        - orchestrator behaviour (bootstrap + validate + update)
        - persistence correctness

    @ensures
        FreshnessManager enforces all freshness rules consistently and updates
        state predictably across all operational modes.
    """

    # ----------------------------------------------------------------------
    # Bootstrap: file exists overrides config
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_bootstrap_existing_file_overrides_config(self, fm_factory):
        """
        @resume
            Validates that an existing freshness.json file takes precedence
            over initial_counter configuration.

        @scope
            - existing counter file
            - initial_counter ignored
            - stored counter loaded deterministically

        @ensures
            Bootstrap uses the persisted counter value.
        """

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
        """
        @resume
            Validates auto bootstrap behaviour when no freshness.json exists.

        @scope
            - initial_counter="auto"
            - incoming value defines counter
            - counter persisted deterministically

        @ensures
            Auto bootstrap uses incoming as the initial counter.
        """

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
        """
        @resume
            Validates numeric bootstrap behaviour when no freshness.json exists.

        @scope
            - initial_counter numeric
            - configured value defines counter
            - counter persisted deterministically

        @ensures
            Numeric bootstrap uses configured initial_counter.
        """

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
        """
        @resume
            Validates reset_on_start behaviour with auto bootstrap.

        @scope
            - delete existing freshness.json
            - initial_counter="auto"
            - incoming defines counter

        @ensures
            Reset removes stale state and auto bootstrap initializes correctly.
        """

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
        """
        @resume
            Validates reset_on_start behaviour with numeric bootstrap.

        @scope
            - delete existing freshness.json
            - initial_counter numeric
            - configured value defines counter

        @ensures
            Reset removes stale state and numeric bootstrap initializes correctly.
        """

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
        """
        @resume
            Validates all monotonicity and increment rule failure branches.

        @scope
            - replay detection
            - increment too small
            - increment too large
            - drift too large

        @ensures
            FreshnessManager raises FreshnessError with correct reason.
        """

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
        """
        @resume
            Validates acceptance of a valid increment.

        @scope
            - monotonic progression
            - increment within allowed bounds

        @ensures
            No exception is raised for valid increments.
        """

        # --- Arrange ---
        fm, _ = fm_factory(VALID_LAST)
        fm.counter = VALID_LAST

        # --- Act ---
        fm.validate_rules(VALID_INCOMING)

        # --- Assert ---
        assert True

    # ----------------------------------------------------------------------
    # Orchestrator: bootstrap + validate + update
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_validate_and_update_bootstraps_then_updates(self, fm_factory):
        """
        @resume
            Validates orchestrator behaviour when freshness state is uninitialized.

        @scope
            - counter starts as None
            - bootstrap loads stored counter from freshness.json
            - monotonicity rules applied to incoming value
            - updated counter persisted deterministically

        @ensures
            validate_and_update_async performs bootstrap, rule validation, and
            counter persistence in a single deterministic operation.
        """

        # --- Arrange ---
        fm, counter_file = fm_factory(VALID_LAST)

        # --- Act ---
        await fm.validate_and_update_async(VALID_INCOMING)

        # --- Assert ---
        assert fm.counter == VALID_INCOMING
        assert read_counter(counter_file) == VALID_INCOMING

    # ----------------------------------------------------------------------
    # Orchestrator: counter already set → validate + update
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_validate_and_update_skips_bootstrap_when_counter_set(self, fm_factory):
        """
        @resume
            Validates orchestrator behaviour when freshness state is already
            initialized (counter is not None).

        @scope
            - counter pre‑initialized in memory
            - bootstrap skipped
            - monotonicity rules applied to incoming
            - updated counter persisted deterministically

        @ensures
            validate_and_update_async performs rule validation and persistence
            without invoking bootstrap when counter is already set.
        """

        # --- Arrange ---
        fm, counter_file = fm_factory(VALID_LAST)
        fm.counter = VALID_LAST  # simulate completed bootstrap

        # --- Act ---
        await fm.validate_and_update_async(VALID_INCOMING)

        # --- Assert ---
        assert fm.counter == VALID_INCOMING
        assert read_counter(counter_file) == VALID_INCOMING
