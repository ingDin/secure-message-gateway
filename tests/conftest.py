"""
Shared pytest fixtures for building configuration dictionaries.

Provides:
- config_factory: base config builder with safe override merging
"""

import json
import pytest
from pathlib import Path


# ============================================================================
# Config factory
# ============================================================================

@pytest.fixture
def config_factory(tmp_path):
    """
    Build a base configuration dictionary for tests.

    Supports section overrides:
        - If override value is a dict → merge into section.
        - If override value is non-dict → replace entire section.

    Returns:
        Callable[[dict | None], dict]: A function that produces configs.
    """
    def _factory(overrides=None):
        base = {
            "environment": "dev",
            "crypto": {},
            "freshness": {},
            "audit": {},
            "logging": {},
        }

        if overrides:
            for section, values in overrides.items():
                # Create missing sections
                if section not in base:
                    base[section] = {}

                # Merge dict values or replace entire section
                if isinstance(values, dict):
                    base[section].update(values)
                else:
                    base[section] = values

        return base

    return _factory
