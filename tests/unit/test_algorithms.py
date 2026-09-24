"""
Unit tests for AlgorithmRegistry.

Covers:
- valid algorithm lookup
- invalid algorithm lookup
- supports() behavior
- global registry correctness
"""

import pytest

from secure_gateway.algorithms import AlgorithmRegistry, ALGORITHM_REGISTRY
from secure_gateway.hmac import HMACAlgorithm
from secure_gateway.exceptions import HMACError


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def registry():
    """Return a fresh AlgorithmRegistry instance."""
    return AlgorithmRegistry()


@pytest.fixture
def global_registry():
    """Expose the global ALGORITHM_REGISTRY instance."""
    return ALGORITHM_REGISTRY


# ============================================================================
# Test constants
# ============================================================================

VALID_ALGO = "HMAC"
INVALID_ALGO = "INVALID"
UNSUPPORTED_ALGO_1 = "GMAC"
UNSUPPORTED_ALGO_2 = "POLY1305"


# ============================================================================
# Test suite
# ============================================================================

class TestAlgorithmRegistry:
    """Minimal test suite for AlgorithmRegistry."""

    # ----------------------------------------------------------------------
    # Valid lookup
    # ----------------------------------------------------------------------
    def test_get_valid_algorithm(self, registry):
        """Registry.get() should return a valid HMACAlgorithm instance."""
        algo = registry.get(VALID_ALGO)
        assert isinstance(algo, HMACAlgorithm)
        assert algo.name == VALID_ALGO

    # ----------------------------------------------------------------------
    # Invalid lookup
    # ----------------------------------------------------------------------
    def test_get_invalid_algorithm(self, registry):
        """Registry.get() should raise HMACError for unknown algorithms."""
        with pytest.raises(HMACError):
            registry.get(INVALID_ALGO)

    # ----------------------------------------------------------------------
    # supports()
    # ----------------------------------------------------------------------
    def test_supports_method(self, registry):
        """Registry.supports() should correctly report supported algorithms."""
        assert registry.supports(VALID_ALGO) is True
        assert registry.supports(UNSUPPORTED_ALGO_1) is False
        assert registry.supports(UNSUPPORTED_ALGO_2) is False

    # ----------------------------------------------------------------------
    # Global registry
    # ----------------------------------------------------------------------
    def test_global_registry_instance(self, global_registry):
        """Global registry should contain HMACAlgorithm."""
        algo = global_registry.get(VALID_ALGO)
        assert isinstance(algo, HMACAlgorithm)
        assert global_registry.supports(VALID_ALGO) is True
