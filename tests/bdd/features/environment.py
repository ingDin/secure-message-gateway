"""
Behave environment setup for initializing deterministic, fully isolated
integration contexts used by the secure-message-gateway pipeline.

@resume
    Provides reproducible, security-focused initialization scaffolding for
    Behave scenarios, ensuring each test begins with a clean filesystem state
    and a fully constructed gateway configuration.

@scope
    - deterministic creation of persistence-layer artifacts:
        * keys.json
        * keys_archive.json
        * freshness.json
        * audit.log
        * gateway.log
    - stable initialization semantics for cryptographic, freshness, logging,
      and audit subsystems
    - predictable behavior across integration scenarios, independent of host
      environment variability
    - centralized setup logic enforcing uniformity, maintainability, and
      security-focused test scaffolding

@ensures
    Behave scenarios execute against isolated, reproducible environments,
    enabling deterministic end-to-end testing for safety-critical and
    distributed deployments.
"""

import json
from pathlib import Path
from secure_gateway.gateway import GatewayAsync


def before_scenario(context, scenario):
    """
    @resume
        Initializes a fully isolated integration environment for each Behave
        scenario, ensuring deterministic filesystem and configuration state.

    @scope
        - creation of tmp_behave directory for scenario-local persistence
        - initialization of all required gateway persistence files
        - construction of a complete configuration object with stable defaults
        - instantiation of a GatewayAsync instance bound to isolated state

    @parameters
        context:
            Behave context object used to store scenario-specific state.
        scenario:
            The scenario currently being executed.

    @ensures
        Each scenario begins with a clean, reproducible environment, guaranteeing
        deterministic gateway behavior across cryptographic, freshness, logging,
        and audit subsystems.
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
