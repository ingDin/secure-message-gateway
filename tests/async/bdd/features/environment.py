import json
from pathlib import Path
from secure_gateway.gateway import GatewayAsync


def before_scenario(context, scenario):
    """
    Prepare an isolated async gateway environment for each BDD scenario.

    Creates:
      - tmp_behave/keys.json      → contains the HMAC key
      - tmp_behave/freshness.json → contains the monotonic counter
      - tmp_behave/audit.log      → async audit log file

    Instantiates:
      - GatewayAsync(config_dir, log_path)
    """
    # Temporary directory for scenario
    context.tmp = Path(__file__).resolve().parents[1] / "tmp_behave"
    context.tmp.mkdir(parents=True, exist_ok=True)

    # Write HMAC key
    (context.tmp / "keys.json").write_text(json.dumps({
        "hmac_key": "a" * 64
    }))

    # Write freshness counter
    (context.tmp / "freshness.json").write_text(json.dumps({
        "counter": 0
    }))

    # Prepare audit log file
    context.log_path = context.tmp / "audit.log"
    context.log_path.touch()

    # Instantiate async gateway (behave will call it via asyncio.run)
    context.gateway = GatewayAsync(
        config_dir=context.tmp,
        log_path=context.log_path
    )
