"""
Message Generator for secure-message-gateway.

Creates a deterministic set of example PDUs for testing the gateway. Includes:
- valid HMAC‑signed messages
- invalid HMAC messages
- replay attacks
- schema validation failures
- large counter jumps

Output is written to examples/examples.json and used in unit, integration, and BDD tests.
"""

import json
from pathlib import Path
from secure_gateway.hmac import HMACAlgorithm

EXAMPLES_FILE = Path("examples/examples.json")
CONFIG_DIR = Path("config")


async def main():
    """
    Generate and export example PDUs.

    Steps:
    - load HMAC key
    - increment counter
    - build messages covering all validation paths
    - sign valid messages
    - save to examples/examples.json
    """

    algo = HMACAlgorithm()

    # Load config.json
    with open(CONFIG_DIR / "config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    # Load HMAC key
    key = await algo.load_key_async(config)

    messages = []
    counter = 1000  # realistic starting point

    # 1. Valid message
    counter += 1
    msg_valid = {
        "id": 1,
        "counter": counter,
        "msg": "valid_message"
    }
    msg_valid["hmac"] = await algo.sign_async(msg_valid, key)
    messages.append(msg_valid)

    # 2. Invalid HMAC
    counter += 1
    msg_bad_hmac = {
        "id": 1,
        "counter": counter,
        "msg": "invalid_hmac",
        "hmac": "WRONG_HMAC"
    }
    messages.append(msg_bad_hmac)

    # 3. Replay attack (lower counter)
    msg_replay = {
        "id": 1,
        "counter": counter - 2,
        "msg": "replay_attack"
    }
    msg_replay["hmac"] = await algo.sign_async(msg_replay, key)
    messages.append(msg_replay)

    # 4. Schema fail (missing field)
    counter += 1
    msg_schema_missing = {
        "id": 1,
        "msg": "missing_counter"
    }
    messages.append(msg_schema_missing)

    # 5. Schema fail (extra field)
    counter += 1
    msg_schema_extra = {
        "id": 1,
        "counter": counter,
        "msg": "extra_field",
        "extra": "not_allowed"
    }
    messages.append(msg_schema_extra)

    # 6. Counter jump
    counter += 5000
    msg_jump = {
        "id": 1,
        "counter": counter,
        "msg": "counter_jump"
    }
    msg_jump["hmac"] = await algo.sign_async(msg_jump, key)
    messages.append(msg_jump)

    # Save all messages in one JSON file
    with open(EXAMPLES_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=4)

    print(f"Generated {len(messages)} messages in {EXAMPLES_FILE}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
