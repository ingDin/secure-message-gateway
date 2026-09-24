"""
Class-based algorithm registry for the secure gateway.

Provides:
- AlgorithmRegistry (selects the correct crypto backend)
- ALGORITHM_REGISTRY (global singleton)
"""

from typing import Dict
from secure_gateway.exceptions import HMACError

# Import base class + concrete algorithms
from secure_gateway.algorithm_base import Algorithm
from secure_gateway.hmac import HMACAlgorithm


class AlgorithmRegistry:
    """
    Registry mapping algorithm names to class instances.

    Responsibilities:
    - expose available crypto backends
    - validate algorithm names
    - provide a global singleton for easy access
    """

    def __init__(self):
        self._algorithms: Dict[str, Algorithm] = {
            "HMAC": HMACAlgorithm(),
            # Future:
            # "GMAC": GMACAlgorithm(),
            # "CMAC": CMACAlgorithm(),
            # "POLY1305": Poly1305Algorithm(),
        }

    def get(self, name: str) -> Algorithm:
        """
        Return the algorithm instance for the given name.
        Raise HMACError if the name is unknown.
        """
        try:
            return self._algorithms[name]
        except KeyError:
            raise HMACError(f"Unknown algorithm '{name}'")

    def supports(self, name: str) -> bool:
        """
        Return True if the registry contains the given algorithm name.
        """
        return name in self._algorithms


# Global singleton registry
ALGORITHM_REGISTRY = AlgorithmRegistry()
