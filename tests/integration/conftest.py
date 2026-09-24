"""
Shared pytest fixtures for integration tests.

Provides:
- integration_config_factory: full config builder with initialized temp files
"""

import json
import pytest
from pathlib import Path


# ============================================================================
# Full integration config factory
# ============================================================================

@pytest.fixture
def integration_config_factory(tmp_path, config_factory):
    """
    Build a full integration config with temporary paths and initialized files.

    Creates:
        - keys.json
        - keys_archive.json
        - freshness.json
        - audit.log
        - gateway.log

    Returns:
        Callable[[], dict]: A function that produces a complete integration config.
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
