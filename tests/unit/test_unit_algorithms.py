"""
Unit test suite for AlgorithmRegistry.

@resume
    Validates the foundational behaviour of the cryptographic algorithm
    registry subsystem.

@scope
    - deterministic resolution of valid algorithm identifiers
    - domain-specific failure signalling for invalid identifiers
    - capability reporting via supports()
    - correct initialization and behaviour of the global ALGORITHM_REGISTRY

@ensures
    Upstream cryptographic components relying on AlgorithmRegistry receive
    predictable, stable, and contract-respecting behaviour.
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
    @resume
        Provides a fresh AlgorithmRegistry instance for isolated unit testing.

    @scope
        - ensures deterministic behaviour by avoiding shared state
        - prevents cross-test contamination

    @returns
        A clean AlgorithmRegistry instance.
    """
    return AlgorithmRegistry()


@pytest.fixture
def global_registry():
    """
    @resume
        Exposes the global ALGORITHM_REGISTRY instance.

    @scope
        - validates correct initialization of the shared registry
        - ensures consistent behaviour across application lifecycle

    @returns
        The global AlgorithmRegistry singleton.
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
    @resume
        Contract validation suite for AlgorithmRegistry.

    @scope
        - valid algorithm resolution
        - deterministic failure signalling
        - capability reporting
        - global registry correctness

    @ensures
        The registry layer behaves predictably and supports all upstream
        cryptographic operations with stable, contract-respecting semantics.
    """

    # ----------------------------------------------------------------------
    # Valid lookup
    # ----------------------------------------------------------------------
    def test_get_valid_algorithm(self, registry):
        """
        @resume
            Validates that AlgorithmRegistry.get() resolves known algorithm
            identifiers to their correct implementation instances.

        @scope
            - HMACAlgorithm resolution
            - instance type correctness
            - name contract validation

        @raises
            None

        @ensures
            Registry returns a deterministic, contract-respecting crypto backend.
        """

        # --- Arrange ---
        # registry fixture already provides a clean AlgorithmRegistry instance

        # --- Act ---
        algo = registry.get(VALID_ALGO)

        # --- Assert ---
        assert isinstance(algo, HMACAlgorithm)
        assert algo.name == VALID_ALGO

    # ----------------------------------------------------------------------
    # Invalid lookup
    # ----------------------------------------------------------------------
    def test_get_invalid_algorithm(self, registry):
        """
        @resume
            Validates deterministic failure signalling when resolving unknown
            algorithm identifiers.

        @scope
            - invalid identifier resolution
            - domain-specific exception raising

        @raises
            HMACError

        @ensures
            Registry fails deterministically and safely for unknown algorithms.
        """

        # --- Arrange ---
        # registry fixture already provides a clean AlgorithmRegistry instance

        # --- Act / Assert ---
        with pytest.raises(HMACError):
            registry.get(INVALID_ALGO)

    # ----------------------------------------------------------------------
    # supports()
    # ----------------------------------------------------------------------
    def test_supports_method(self, registry):
        """
        @resume
            Validates capability reporting via AlgorithmRegistry.supports().

        @scope
            - positive capability reporting for supported algorithms
            - negative reporting for unsupported algorithms

        @ensures
            supports() behaves deterministically and reflects registry capabilities.
        """

        # --- Arrange ---
        # registry fixture already provides a clean AlgorithmRegistry instance

        # --- Act / Assert ---
        assert registry.supports(VALID_ALGO) is True
        assert registry.supports(UNSUPPORTED_ALGO_1) is False
        assert registry.supports(UNSUPPORTED_ALGO_2) is False

    # ----------------------------------------------------------------------
    # Global registry
    # ----------------------------------------------------------------------
    def test_global_registry_instance(self, global_registry):
        """
        @resume
            Validates correct initialization and behaviour of the global
            ALGORITHM_REGISTRY instance.

        @scope
            - global registry correctness
            - deterministic behaviour across lookups

        @ensures
            The global registry behaves consistently across the application lifecycle.
        """

        # --- Arrange ---
        # global_registry fixture exposes ALGORITHM_REGISTRY

        # --- Act ---
        algo = global_registry.get(VALID_ALGO)

        # --- Assert ---
        assert isinstance(algo, HMACAlgorithm)
        assert global_registry.supports(VALID_ALGO) is True
