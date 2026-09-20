from behave import given, when, then
import json
from secure_gateway.crypto import sign_message, get_hmac_key


# Minimal helper (not duplicated anywhere)
def compute_hmac(context, message):
    key = get_hmac_key(context.tmp)
    payload = {
        "id": message["id"],
        "msg": message["msg"],
        "counter": message["counter"],
    }
    return sign_message(payload, key)


# ---------------------------------------------------------
# Given steps
# ---------------------------------------------------------

@given("a valid message")
def step_valid_message(context):
    context.msg = {"id": 1, "msg": "hello", "counter": 1}
    context.msg["hmac"] = compute_hmac(context, context.msg)


@given("a message with an invalid HMAC")
def step_invalid_hmac(context):
    context.msg = {"id": 1, "msg": "hello", "counter": 1, "hmac": "WRONG_HMAC"}


@given("a previously accepted message")
def step_previous_message(context):
    msg1 = {"id": 1, "msg": "hello", "counter": 1}
    msg1["hmac"] = compute_hmac(context, msg1)
    context.gateway.process(msg1)

    freshness = json.loads((context.tmp / "freshness.json").read_text())
    context.payload = {
        "id": 1,
        "msg": "hello",
        "counter": freshness["counter"],
    }


@given("a replayed message with the same counter")
def step_replayed_message(context):
    msg2 = dict(context.payload)
    msg2["hmac"] = compute_hmac(context, msg2)
    context.msg = msg2


@given("a message with missing required fields")
def step_invalid_schema(context):
    context.msg = {"id": 1, "counter": 1, "hmac": "1234"}


# ---------------------------------------------------------
# When step
# ---------------------------------------------------------

@when("the gateway processes the message")
def step_process_message(context):
    context.response = context.gateway.process(context.msg)


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

