import asyncio
import json
import time
from pathlib import Path

from secure_gateway.gateway import GatewayAsync
from secure_gateway.hmac import HMACAlgorithm


def load_config(project_root: Path) -> dict:
    """
    @summary
    Load gateway configuration from the config directory.
    """
    config_path = project_root / "config" / "config.json"
    return json.loads(config_path.read_text())


def load_start_counter(config: dict) -> int:
    """
    @summary
    Return the counter stored in the freshness counter file.
    No fallback, no validation, no error handling.
    """
    freshness_path = Path(config["freshness"]["counter_file"])
    data = json.loads(freshness_path.read_text())
    return int(data["counter"])


def load_active_key(config: dict) -> str:
    """
    @summary
    Load the active HMAC key from the key store.
    """
    keys_path = Path(config["crypto"]["keys_file"])
    keys_data = json.loads(keys_path.read_text())
    return keys_data["dev_key"]


async def async_message_generator(count: int, key_hex: str, start_counter: int):
    """
    @summary
    Asynchronous streaming generator for synthetic messages.
    Counter increases strictly and deterministically.
    """
    algo = HMACAlgorithm()
    key_bytes = bytes.fromhex(key_hex)

    counter = start_counter

    for _ in range(count):
        counter += 1

        payload = {
            "id": counter,
            "counter": counter,
            "msg": f"auto-msg-{counter}"
        }

        mac = algo.sign(payload, key_bytes)
        yield {**payload, "hmac": mac}

        await asyncio.sleep(0)  # cooperative scheduling


async def process_sequential(gateway: GatewayAsync, key_hex: str, total: int, start_counter: int) -> int:
    """
    @summary
    Process messages strictly sequentially.
    Ensures freshness monotonicity without concurrency.
    """
    processed = 0

    async for message in async_message_generator(total, key_hex, start_counter):
        await gateway.process(message)
        processed += 1

    return processed


def compute_throughput(processed: int, elapsed: float) -> float:
    """
    @summary
    Compute messages per second.
    """
    return processed / elapsed if elapsed > 0 else 0.0


async def main():
    """
    @summary
    Deterministic load tester for the secure-message-gateway.
    Sequential processing ensures strict freshness correctness.
    """
    project_root = Path(__file__).resolve().parents[1]

    config = load_config(project_root)
    key_hex = load_active_key(config)
    start_counter = load_start_counter(config)

    gateway = GatewayAsync(config)

    total_messages = 5000  # adjust freely

    start_time = time.perf_counter()

    processed = await process_sequential(
        gateway,
        key_hex,
        total_messages,
        start_counter
    )

    elapsed = time.perf_counter() - start_time
    throughput = compute_throughput(processed, elapsed)

    print(f"Total messages processed: {processed}")
    print(f"Total time: {elapsed:.4f} seconds")
    print(f"Throughput: {throughput:.2f} messages/sec")


if __name__ == "__main__":
    asyncio.run(main())
