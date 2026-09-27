"""
@summary
Provides the class-based registry for cryptographic algorithms used by the
secure-message-gateway. The registry offers deterministic lookup of crypto
backends and maintains a global singleton for consistent access across the
gateway pipeline.

This module ensures:
- centralized algorithm resolution
- deterministic validation of algorithm names
- clean separation between registry logic and concrete implementations

All cryptographic backends must implement the Algorithm interface defined in
`algorithm_base.py` and be registered here.
"""

from typing import Dict
from secure_gateway.exceptions import HMACError

# Import base class + concrete algorithms
from secure_gateway.algorithm_base import Algorithm
from secure_gateway.hmac import HMACAlgorithm


class AlgorithmRegistry:
    """
    @summary
    Registry mapping algorithm identifiers to concrete algorithm instances.
    Ensures deterministic selection of cryptographic backends and predictable
    error signaling for unsupported algorithms.

    @examples
    >>> registry = AlgorithmRegistry()
    >>> algo = registry.get("HMAC")
    >>> registry.supports("HMAC")
    True
    """

    def __init__(self):
        self._algorithms: Dict[str, Algorithm] = {
            "HMAC": HMACAlgorithm(),
            # Future extensions:
            # "GMAC": GMACAlgorithm(),
            # "CMAC": CMACAlgorithm(),
            # "POLY1305": Poly1305Algorithm(),
        }

    def get(self, name: str) -> Algorithm:
        """
        @summary
        Retrieve the algorithm instance associated with the given name.

        @parameters
        name : str
            The algorithm identifier (e.g., "HMAC").

        @returns
        Algorithm
            The concrete algorithm instance registered under the given name.

        @raises
        HMACError
            If the algorithm name is unknown or unsupported.

        @examples
        >>> algo = registry.get("HMAC")
        """
        try:
            return self._algorithms[name]
        except KeyError:
            raise HMACError(f"Unknown algorithm '{name}'")

    def supports(self, name: str) -> bool:
        """
        @summary
        Check whether the registry contains the specified algorithm name.

        @parameters
        name : str
            The algorithm identifier to validate.

        @returns
        bool
            True if the algorithm is registered, False otherwise.

        @examples
        >>> registry.supports("HMAC")
        True
        """
        return name in self._algorithms


# Global singleton registry
ALGORITHM_REGISTRY = AlgorithmRegistry()
