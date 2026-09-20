"""
Unit tests for secure_gateway.freshness (synchronous logic).

These tests validate the core monotonicity rules of the freshness module,
ensuring that strictly increasing counters are accepted and that equal or
lower counters are correctly rejected as replay attempts. This suite verifies
the deterministic, security‑critical behavior of the freshness check that
protects the gateway against stale or duplicated messages.
"""


import json
import pytest

from secure_gateway.exceptions import FreshnessError
from secure_gateway.freshness import verify_freshness


#
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
