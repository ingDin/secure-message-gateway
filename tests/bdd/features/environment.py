import json
from pathlib import Path
from secure_gateway.gateway import Gateway

def before_scenario(context, scenario):
    context.tmp = Path(__file__).resolve().parents[1] / "tmp_behave"
    context.tmp.mkdir(parents=True, exist_ok=True)

    (context.tmp / "keys.json").write_text(json.dumps({
        "hmac_key": "a" * 64
    }))

    (context.tmp / "freshness.json").write_text(json.dumps({
        "counter": 0
    }))

    context.log_path = context.tmp / "audit.log"
    context.log_path.touch()

    context.gateway = Gateway(
        config_dir=context.tmp,
        log_path=context.log_path
    )
