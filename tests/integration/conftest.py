"""
Enterprise-level shared pytest fixtures for constructing fully initialized
integration configurations used throughout the secure-message-gateway test suite.

This module provides deterministic, reproducible helpers that assemble complete
gateway configurations backed by temporary filesystem state. It ensures:

- consistent creation of all persistence-layer artifacts required by integration
  tests (keys.json, keys_archive.json, freshness.json, audit.log, gateway.log)
- isolated and reproducible filesystem behavior via pytest’s tmp_path fixture
- stable initialization semantics for cryptographic, freshness, logging, and
  audit subsystems
- simplified test authoring by centralizing integration configuration setup

These fixtures form foundational infrastructure for the gateway’s integration
tests, enabling predictable, maintainable, and security‑focused test environments
across all pipeline layers.
"""


import json
import pytest
from pathlib import Path


@pytest.fixture
def integration_config_factory(tmp_path, config_factory):
    """
    Factory fixture producing fully initialized integration configurations with
    deterministic filesystem scaffolding.

    This helper ensures:
    - creation of all required persistence files (keys.json, keys_archive.json,
      freshness.json, audit.log, gateway.log)
    - stable initialization of cryptographic, freshness, logging, and audit
      configuration blocks
    - reproducible test environments independent of host system state
    - seamless integration with config_factory for safe override merging

    Returns:
        Callable[[], dict]:
            A factory function that constructs and returns a complete integration
            configuration dictionary suitable for end-to-end gateway testing.
    """
    def _factory():
        # Paths
        keys_path = tmp_path / "keys.json"
        archive_path = tmp_path / "keys_archive.json"
        freshness_path = tmp_path / "freshness.json"
        audit_path = tmp_path / "audit.log"
        gateway_log_path = tmp_path / "gateway.log"

        # Initialize files
        keys_path.write_text("{}", encoding="utf-8")
        archive_path.write_text("{}", encoding="utf-8")
        freshness_path.write_text(json.dumps({"counter": 0}), encoding="utf-8")
        audit_path.write_text("", encoding="utf-8")
        gateway_log_path.write_text("", encoding="utf-8")

        # Build full config
        return config_factory({
            "version": "1.0.0",
            "environment": "dev",

            "crypto": {
                "algorithm": "HMAC",
                "keys_file": str(keys_path),
                "keys_archive": str(archive_path),
                "hmac_algorithm": "SHA256",
                "allowed_algorithms": ["SHA256"],
                "min_key_length": 32,
                "rotation_required": False,
                "rotation_interval_days": 30,
            },

            "freshness": {
                "counter_file": str(freshness_path),
                "min_increment": 1,
                "max_increment": 5,
                "max_drift": 10,
                "reject_out_of_range": True,
            },

            "logging": {
                "path": str(gateway_log_path)
            },

            "audit": {
                "enabled": True,
                "path": str(audit_path),
            }
        })

    return _factory
