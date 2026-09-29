"""
Shared pytest fixtures providing deterministic, fully-initialized integration
configurations for the secure-message-gateway test suite.

@resume
    Supplies reproducible filesystem scaffolding and complete gateway
    configurations, enabling end-to-end integration tests across all pipeline
    layers: schema validation, cryptographic verification, freshness enforcement,
    key rotation, and audit logging.

@scope
    - creation of all persistence-layer artifacts:
        * keys.json
        * keys_archive.json
        * freshness.json
        * audit.log
    - stable initialization of crypto, freshness, and audit subsystems
    - isolated filesystem behaviour via pytest’s tmp_path fixture
    - seamless override merging through config_factory

@ensures
    Integration tests operate in deterministic, isolated environments with
    predictable state, eliminating cross-test interference and host-level
    variability.
"""

import json
import pytest
from pathlib import Path
from secure_gateway.hmac import HMACAlgorithm


@pytest.fixture
def integration_config_factory(tmp_path, config_factory):
    """
    @resume
        Factory fixture producing complete, ready-to-use integration
        configurations backed by isolated temporary filesystem state.

    @scope
        - initializes all required gateway persistence files
        - writes a valid cryptographic key for the selected environment
        - prepares freshness.json with a deterministic initial counter
        - ensures audit.log exists for append-only logging
        - integrates cleanly with config_factory for override injection

    @returns
        Callable[[], dict]:
            A factory function that constructs and returns a fully-initialized
            gateway configuration suitable for end-to-end testing.

    @ensures
        Integration tests can rely on stable, reproducible configuration
        scaffolding without duplicating boilerplate setup logic.
    """
    def _factory():
        # Paths
        keys_path = tmp_path / "keys.json"
        archive_path = tmp_path / "keys_archive.json"
        freshness_path = tmp_path / "freshness.json"
        audit_path = tmp_path / "audit.log"

        # Generate a valid HMAC key
        algo = HMACAlgorithm()
        key_hex = algo.generate_key(32)

        # Initialize keys.json
        keys_path.write_text(
            json.dumps({"dev_key": key_hex}),
            encoding="utf-8"
        )

        # Initialize archive file
        archive_path.write_text("{}", encoding="utf-8")

        # Initialize freshness state
        freshness_path.write_text(
            json.dumps({"counter": 0}),
            encoding="utf-8"
        )

        # Initialize audit log
        audit_path.write_text("", encoding="utf-8")

        # Build full config
        return config_factory({
            "version": "1.0.0",
            "environment": "dev",

            "crypto": {
                "algorithm": "HMAC",
                "keys_file": str(keys_path),
                "keys_archive": str(archive_path),
                "hmac_algorithm": "HMAC",
                "allowed_algorithms": ["HMAC"],
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
                "initial_counter": "auto",
                "reset_on_start": False,
            },

            "audit": {
                "enabled": True,
                "path": str(audit_path),
            }
        })

    return _factory
