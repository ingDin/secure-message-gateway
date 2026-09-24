import asyncio
import json
from pathlib import Path
from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


async def main():
    # Determine project root dynamically
    project_root = Path(__file__).resolve().parents[1]

    # Load config/config.json
    config_path = project_root / "config" / "config.json"
    config = json.loads(config_path.read_text())

    gateway = GatewayAsync(config)
    algo = HMACAlgorithm()

    # Load examples/examples.json
    examples_path = project_root / "examples" / "examples.json"
    examples = json.loads(examples_path.read_text())

    print("\n=== Running Secure Gateway Simulator ===\n")

    for idx, msg in enumerate(examples, start=1):
        print(f"\n--- Example #{idx}: {msg.get('msg')} ---")

        # If message has no HMAC, sign it with current key
        if "hmac" not in msg:
            try:
                keys_path = Path(config["crypto"]["keys_file"])
                keys_data = json.loads(keys_path.read_text())
                key_hex = keys_data["dev_key"]
                mac = algo.sign(msg, bytes.fromhex(key_hex))
                msg["hmac"] = mac
            except Exception:
                print("Could not sign message (missing or invalid key).")
                pass

        # Process message
        response = await gateway.process(msg)

        print(f"Status: {response.status}")
        print(f"Reason: {response.reason}")


    # Show freshness counter
    freshness_path = Path(config["freshness"]["counter_file"])
    if freshness_path.exists():
        freshness = json.loads(freshness_path.read_text())
        print("\n=== Freshness Counter ===")
        print(freshness)

    # Show audit log
    audit_path = Path(config["audit"]["path"])
    if audit_path.exists():
        print("\n=== Audit Log ===")
        for line in audit_path.read_text().splitlines():
            print(line)


if __name__ == "__main__":
    asyncio.run(main())
