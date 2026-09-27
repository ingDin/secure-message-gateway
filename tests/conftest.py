"""
Shared pytest fixtures for constructing configuration dictionaries used
throughout the secure-message-gateway test suite.

@resume
    Provides deterministic, override-capable configuration builders that
    support both unit and integration tests by abstracting common configuration
    scaffolding patterns.

@scope
    - consistent baseline configuration across all test modules
    - safe and predictable merging of override sections
    - isolated filesystem behavior via pytest’s tmp_path fixture
    - simplified setup for components relying on crypto, freshness, audit,
      and logging configuration blocks

@ensures
    These fixtures form foundational infrastructure for the gateway’s test
    suite, enabling clean, maintainable, and reproducible test environments
    across security‑critical components.
"""

import json
import pytest
from pathlib import Path


@pytest.fixture
def config_factory(tmp_path):
    """
    @resume
        Factory fixture producing baseline configuration dictionaries with
        deterministic override semantics.

    @scope
        - consistent default configuration structure for all tests
        - safe merging of override dictionaries into existing sections
        - predictable replacement behavior for non-dict overrides
        - isolated filesystem paths for crypto, freshness, audit, and logging

    @parameters
        overrides (dict | None):
            Optional dictionary specifying configuration sections to merge or
            replace. Dict values are merged; non-dict values replace the entire
            section.

    @returns
        Callable[[dict | None], dict]:
            A factory function that builds and returns a fully resolved
            configuration dictionary suitable for initializing gateway
            components in unit or integration tests.

    @ensures
        All test modules can construct deterministic, override-capable
        configuration dictionaries without duplicating boilerplate logic.
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
