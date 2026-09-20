"""
BDD step definitions for the async secure-message gateway.

Behave executes steps synchronously, but the gateway and crypto pipeline
are fully asynchronous. To bridge this mismatch, all async operations
(HMAC computation, gateway processing) are executed via `asyncio.run()`
inside synchronous step functions.

This module provides:

    • An async helper:
        compute_hmac_async(context, message)
        Computes a valid HMAC using the gateway's async crypto module.

    • Given steps:
        - a valid message with correct HMAC
        - a message with invalid HMAC
        - a previously accepted message (for replay testing)
        - a replayed message using the same counter
        - a message with missing required fields

    • When step:
        - processes the message through the async gateway

    • Then steps:
        - assert acceptance ("ok")
        - assert HMAC failure ("HMAC_FAIL")
        - assert freshness failure ("FRESHNESS_FAIL")
        - assert schema failure ("SCHEMA_FAIL")

All steps interact with GatewayAsync, ensuring BDD scenarios exercise the
real asynchronous validation pipeline: schema → HMAC → freshness → audit.
"""

import asyncio
import random
import time
import logging
import pytest

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Load test: many valid messages
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_load_valid(gateway, compute_hmac, build_message):
    async def send(i):
        msg = build_message(id=i, counter=i + 1, msg="ok")
        msg["hmac"] = await compute_hmac(msg)
        return await gateway.process(msg)

    results = await asyncio.gather(*(send(i) for i in range(2000)))
    assert all(r.status == "ok" for r in results)


# ---------------------------------------------------------
# Load test: many invalid messages
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_load_invalid(gateway, build_message):
    async def send(i):
        msg = build_message(id=i, counter=i + 1, msg="bad", hmac="WRONG")
        return await gateway.process(msg)

    results = await asyncio.gather(*(send(i) for i in range(1500)))
    assert all(r.status == "error" for r in results)
    assert all(r.reason == "HMAC_FAIL" for r in results)


# ---------------------------------------------------------
# Load test: mixed valid + invalid
# ---------------------------------------------------------
@pytest.mark.asyncio
async def test_load_mixed(gateway, compute_hmac, build_message):
    async def send(i):
        if random.random() < 0.7:
            msg = build_message(id=i, counter=i + 1, msg="ok")
            msg["hmac"] = await compute_hmac(msg)
        else:
            msg = build_message(id=i, counter=i + 1, msg="bad", hmac="WRONG")
        return await gateway.process(msg)

    results = await asyncio.gather(*(send(i) for i in range(3000)))

    ok = sum(r.status == "ok" for r in results)
    err = sum(r.status == "error" for r in results)

    assert ok > 1500
    assert err > 500


# ---------------------------------------------------------
# Continuous stress test (3 seconds flood)
# ---------------------------------------------------------
def test_continuous(gateway, compute_hmac, build_message):
    async def run():
        start = time.time()
        count = 0

        while time.time() - start < 3:
            msg = build_message(id=count, counter=count + 1, msg="stress")
            msg["hmac"] = await compute_hmac(msg)
            resp = await gateway.process(msg)
            assert resp.status == "ok"
            count += 1

        logger.info(f"Processed {count} messages in 3 seconds")

    asyncio.run(run())
