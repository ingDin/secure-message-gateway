import asyncio
import json
from pathlib import Path

from secure_gateway.gateway import GatewayAsync
from secure_gateway.crypto import get_hmac_key_async, sign_message

EXAMPLES_FILE = Path("examples/examples.json")
CONFIG_DIR = Path("config")
LOG_PATH = Path("logs/gateway.log")


async def main():
    gateway = GatewayAsync(CONFIG_DIR, LOG_PATH)
    key = await get_hmac_key_async(CONFIG_DIR)

    # Load entire message stream
    with open(EXAMPLES_FILE, "r", encoding="utf-8") as f:
        messages = json.load(f)

    print(f"Loaded {len(messages)} messages from examples.json")

    for msg in messages:
        print(f"\n=== Processing message with counter {msg.get('counter')} ===")
        print("Message:", msg)

        # Add HMAC if missing
        if "hmac" not in msg and "counter" in msg and "msg" in msg:
            msg["hmac"] = sign_message(msg, key)

        response = await gateway.process(msg)
        print("Gateway response:", response)


if __name__ == "__main__":
    asyncio.run(main())
