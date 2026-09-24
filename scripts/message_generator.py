"""
Message Generator for secure-message-gateway.

This module produces a deterministic set of example PDUs used to test the
asynchronous security gateway. It generates both valid and intentionally invalid
messages to exercise every major branch of the gateway’s validation pipeline.

Generated message categories:
- Valid HMAC‑signed message
- Invalid HMAC (tampered signature)
- Replay attack (counter lower than expected)
- Schema validation failures (missing or extra fields)
- Large counter jump (may pass or fail freshness rules depending on config)

The resulting messages are written to examples/examples.json and can be used for:
- unit tests
- integration tests
- BDD scenarios
- manual gateway execution via main.py

This ensures consistent, reproducible test vectors for development and debugging.
"""

import json
from pathlib import Path
from secure_gateway.hmac import HMACAlgorithm

EXAMPLES_FILE = Path("examples/examples.json")
CONFIG_DIR = Path("config")


async def main():
    """
    Build and export a complete suite of example messages.

    Workflow:
    1. Load the active HMAC key using HMACAlgorithm.load_key_async().
    2. Initialize a realistic starting counter.
    3. Generate several PDUs, each designed to trigger a specific gateway behavior:
       - a valid, correctly signed message
       - a message with an intentionally incorrect HMAC
       - a replay scenario using a lower counter value
       - a schema error caused by a missing required field
       - a schema error caused by an unexpected extra field
       - a large counter jump to test freshness rules
    4. Sign all valid messages using HMACAlgorithm.sign_async().
    5. Save the entire message set to examples/examples.json.

    This function is intended for developers who need predictable, structured
    test messages to validate gateway behavior or troubleshoot issues.
    """

    algo = HMACAlgorithm()

    # Load config.json
    with open(CONFIG_DIR / "config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    # Load HMAC key
    key = await algo.load_key_async(config)

    messages = []
    counter = 1000  # realistic starting point

    # 1. Valid or invalid depending on rotation
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
        "counter": counter - 2,  # intentionally smaller
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

    # 6. Counter jump (valid)
    msg_jump = {
        "id": 1,
        "counter": counter,
        "msg": "counter_jump"
    }
    messages.append(msg_jump)

    # Save all messages in one JSON file
    with open(EXAMPLES_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=4)

    print(f"Generated {len(messages)} messages in {EXAMPLES_FILE}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
