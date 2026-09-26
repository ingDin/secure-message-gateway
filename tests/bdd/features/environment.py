"""
Behave environment setup for initializing deterministic,
fully isolated integration contexts used by the secure-message-gateway
pipeline.

This module ensures that each scenario begins with a clean, reproducible
filesystem state and a fully constructed gateway configuration. It provides:

- consistent creation of temporary persistence-layer artifacts
  (keys.json, keys_archive.json, freshness.json, audit.log, gateway.log)
- stable initialization semantics for cryptographic, freshness, logging,
  and audit subsystems
- predictable behavior across all integration scenarios, independent of
  host environment variability
- centralized setup logic that enforces uniformity, maintainability, and
  security-focused test scaffolding

These guarantees form the foundation for deterministic end-to-end testing
of the gateway’s behavior in safety-critical and distributed deployments.
"""

import json
from pathlib import Path
from secure_gateway.gateway import GatewayAsync

def before_scenario(context, scenario):
    """
    Initialize a fully isolated integration environment for each Behave scenario.

    This setup routine ensures:
    - creation of a dedicated tmp_behave directory for scenario-local state
    - deterministic initialization of all persistence files required by the
      gateway (keys.json, keys_archive.json, freshness.json, audit.log,
      gateway.log)
    - construction of a complete configuration object with stable defaults for
      cryptographic, freshness, logging, and audit subsystems
    - instantiation of a GatewayAsync instance bound to the scenario’s isolated
      configuration

    Parameters:
        context: Behave context object used to store scenario-specific state.
        scenario: The scenario currently being executed.

    The resulting environment guarantees reproducible, security-focused
    integration behavior across all gateway pipeline tests.
    """

    # Create tmp directory in the current working directory
    context.tmp = Path.cwd() / "tmp_behave"
    context.tmp.mkdir(parents=True, exist_ok=True)

    # Paths for temporary files
    keys_path = context.tmp / "keys.json"
    archive_path = context.tmp / "keys_archive.json"
    freshness_path = context.tmp / "freshness.json"
    audit_path = context.tmp / "audit.log"
    gateway_log_path = context.tmp / "gateway.log"

    # Write minimal test data
    keys_path.write_text(json.dumps({"dev_key": "a" * 64}))
    archive_path.write_text(json.dumps({}))
    freshness_path.write_text(json.dumps({"counter": 0}))
    audit_path.write_text("")
    gateway_log_path.write_text("")

    # Configuration object (safe name: configuration)
    context.configuration = {
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
            "path": str(gateway_log_path),
        },

        "audit": {
            "enabled": True,
            "path": str(audit_path),
        }
    }

    # Create gateway instance
    context.gateway = GatewayAsync(context.configuration)
