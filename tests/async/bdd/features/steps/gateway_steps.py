"""
BDD step definitions for the async secure gateway.

This module adapts Behave's synchronous step execution model to the
gateway's asynchronous processing pipeline. Because Behave does not
support async/await natively, all async gateway operations are executed
synchronously using `asyncio.run()`.

Provided steps:
    • Given steps build various message states:
        - valid message with correct HMAC
        - invalid HMAC
        - previously accepted message (for replay testing)
        - replayed message with same counter
        - invalid schema message

    • When step triggers the async gateway processing:
        - `context.response = asyncio.run(context.gateway.process(...))`

    • Then steps assert the structured GatewayResponse:
        - accepted message
        - HMAC_FAIL
        - FRESHNESS_FAIL
        - SCHEMA_FAIL

The helper `compute_hmac_async()` computes valid HMAC digests using the
gateway's async crypto module, ensuring BDD tests remain aligned with
the real async pipeline.
"""

from behave import given, when, then
import json
import asyncio

from secure_gateway.crypto import sign_message_async, get_hmac_key_async


# ---------------------------------------------------------
# Minimal async helper (not duplicated anywhere)
# ---------------------------------------------------------
async def compute_hmac_async(context, message):
    """
    Compute a valid HMAC asynchronously for BDD tests.

    Behave is sync-only, so this helper is executed via asyncio.run()
    inside the step definitions.
    """
    key = await get_hmac_key_async(context.tmp)
    payload = {
        "id": message["id"],
        "msg": message["msg"],
        "counter": message["counter"],
    }
    return await sign_message_async(payload, key)


# ---------------------------------------------------------
# Given steps
# ---------------------------------------------------------

@given("a valid message")
def step_valid_message(context):
    msg = {"id": 1, "msg": "hello", "counter": 1}
    msg["hmac"] = asyncio.run(compute_hmac_async(context, msg))
    context.msg = msg


@given("a message with an invalid HMAC")
def step_invalid_hmac(context):
    context.msg = {"id": 1, "msg": "hello", "counter": 1, "hmac": "WRONG_HMAC"}


@given("a previously accepted message")
def step_previous_message(context):
    # First valid message
    msg1 = {"id": 1, "msg": "hello", "counter": 1}
    msg1["hmac"] = asyncio.run(compute_hmac_async(context, msg1))

    # Process async gateway synchronously
    asyncio.run(context.gateway.process(msg1))

    # Read updated freshness.json
    freshness = json.loads((context.tmp / "freshness.json").read_text())
    updated_counter = freshness["counter"]

    # Save payload for replay
    context.payload = {
        "id": 1,
        "msg": "hello",
        "counter": updated_counter,
    }


@given("a replayed message with the same counter")
def step_replayed_message(context):
    msg2 = dict(context.payload)
    msg2["hmac"] = asyncio.run(compute_hmac_async(context, msg2))
    context.msg = msg2


@given("a message with missing required fields")
def step_invalid_schema(context):
    context.msg = {"id": 1, "counter": 1, "hmac": "1234"}


# ---------------------------------------------------------
# When step
# ---------------------------------------------------------

@when("the gateway processes the message")
def step_process_message(context):
    context.response = asyncio.run(context.gateway.process(context.msg))


# ---------------------------------------------------------
# Then steps
# ---------------------------------------------------------

@then("the gateway accepts the message")
def step_accept(context):
    assert context.response.status == "ok"


@then('the gateway rejects the message with reason "HMAC_FAIL"')
def step_hmac_fail(context):
    assert context.response.status == "error"
    assert context.response.reason == "HMAC_FAIL"


@then('the gateway rejects the message with reason "FRESHNESS_FAIL"')
def step_freshness_fail(context):
    assert context.response.status == "error"
    assert context.response.reason == "FRESHNESS_FAIL"


@then('the gateway rejects the message with reason "SCHEMA_FAIL"')
def step_schema_fail(context):
    assert context.response.status == "error"
    assert context.response.reason == "SCHEMA_FAIL"
