import json
from pathlib import Path
from secure_gateway.crypto import sign_message, get_hmac_key_async

EXAMPLES_FILE = Path("examples/examples.json")
CONFIG_DIR = Path("config")


async def main():
    key = await get_hmac_key_async(CONFIG_DIR)

    messages = []
    counter = 1000  # punct de start realist

    # 1. Mesaj valid
    counter += 1
    msg_valid = {
        "id": 1,
        "counter": counter,
        "msg": "valid_message"
    }
    msg_valid["hmac"] = sign_message(msg_valid, key)
    messages.append(msg_valid)

    # 2. Mesaj invalid HMAC
    counter += 1
    msg_bad_hmac = {
        "id": 1,
        "counter": counter,
        "msg": "invalid_hmac",
        "hmac": "WRONG_HMAC"
    }
    messages.append(msg_bad_hmac)

    # 3. Replay attack (counter mai mic)
    msg_replay = {
        "id": 1,
        "counter": counter - 2,  # intentionally smaller
        "msg": "replay_attack"
    }
    msg_replay["hmac"] = sign_message(msg_replay, key)
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

    # 6. Counter jump (valid or invalid depending on freshness)
    counter += 5000
    msg_jump = {
        "id": 1,
        "counter": counter,
        "msg": "counter_jump"
    }
    msg_jump["hmac"] = sign_message(msg_jump, key)
    messages.append(msg_jump)

    # Save all messages in one JSON file
    with open(EXAMPLES_FILE, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=4)

    print(f"Generated {len(messages)} messages in {EXAMPLES_FILE}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
