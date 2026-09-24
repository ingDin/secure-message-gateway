import json
from pathlib import Path
from secure_gateway.gateway import GatewayAsync

def before_scenario(context, scenario):
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
            "level": "INFO",
            "max_size_mb": 1,
            "max_backups": 5,
        },

        "audit": {
            "enabled": True,
            "path": str(audit_path),
        }
    }

    # Create gateway instance
    context.gateway = GatewayAsync(context.configuration)
