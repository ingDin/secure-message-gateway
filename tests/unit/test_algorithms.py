"""
Unit test suite for AlgorithmRegistry.

This module validates the foundational behavior of the cryptographic algorithm
registry subsystem. It ensures that:

- valid algorithm identifiers resolve to correct implementation instances
- invalid identifiers fail deterministically with HMACError
- supports() accurately reflects registry capabilities
- the global ALGORITHM_REGISTRY is initialized correctly and behaves
  consistently across lookups

These tests guarantee that upstream cryptographic components relying on
AlgorithmRegistry receive predictable, stable, and contract-respecting behavior.
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
    """
    Provide a fresh AlgorithmRegistry instance for isolated unit testing.

    Ensures that each test executes against a clean registry without shared
    state, preserving determinism and preventing cross-test contamination.
    """
    return AlgorithmRegistry()


@pytest.fixture
def global_registry():
    """
    Expose the global ALGORITHM_REGISTRY instance.

    Validates that the globally shared registry behaves consistently and
    maintains correct algorithm mappings across the application lifecycle.
    """
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
    """
    Unit test suite validating the correctness, stability,
    and contract guarantees of AlgorithmRegistry.

    This suite ensures that:
    - valid algorithm identifiers resolve to correct implementation instances
    - invalid identifiers raise deterministic, domain-specific exceptions
    - supports() accurately reports registry capabilities
    - the global registry instance is properly initialized and behaves
      consistently across lookups

    These checks validate the reliability of the registry layer, which forms
    the foundation for all upstream cryptographic operations.
    """

    # ----------------------------------------------------------------------
    # Valid lookup
    # ----------------------------------------------------------------------
    def test_get_valid_algorithm(self, registry):
        """
        Registry.get() must return a valid HMACAlgorithm instance for supported
        identifiers.
        """
        algo = registry.get(VALID_ALGO)
        assert isinstance(algo, HMACAlgorithm)
        assert algo.name == VALID_ALGO

    # ----------------------------------------------------------------------
    # Invalid lookup
    # ----------------------------------------------------------------------
    def test_get_invalid_algorithm(self, registry):
        """
        Registry.get() must raise HMACError when resolving unknown algorithms.

        This ensures deterministic failure behavior and prevents silent fallback
        to incorrect or insecure algorithm implementations.
        """
        with pytest.raises(HMACError):
            registry.get(INVALID_ALGO)

    # ----------------------------------------------------------------------
    # supports()
    # ----------------------------------------------------------------------
    def test_supports_method(self, registry):
        """
        Registry.supports() must accurately report which algorithms are
        available.

        Guarantees that capability checks performed by upstream components
        behave predictably.
        """
        assert registry.supports(VALID_ALGO) is True
        assert registry.supports(UNSUPPORTED_ALGO_1) is False
        assert registry.supports(UNSUPPORTED_ALGO_2) is False

    # ----------------------------------------------------------------------
    # Global registry
    # ----------------------------------------------------------------------
    def test_global_registry_instance(self, global_registry):
        """
        The global registry must expose HMACAlgorithm and behave consistently
        across lookups.

        Validates correct initialization of the shared registry used throughout
        the gateway.
        """
        algo = global_registry.get(VALID_ALGO)
        assert isinstance(algo, HMACAlgorithm)
        assert global_registry.supports(VALID_ALGO) is True
