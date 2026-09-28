"""
@resume
Behave step definitions for acceptance testing of the secure-message-gateway.

These steps validate observable gateway behavior from a client perspective:
message acceptance, schema validation, HMAC enforcement, freshness protection,
and key rotation handling. The focus is strictly on externally visible effects,
not internal implementation details.
"""

import json
from pathlib import Path
from behave import given, when, then
from secure_gateway.hmac import HMACAlgorithm


# ============================================================================
# Helpers
# ============================================================================

def _audit_events(context):
    audit_path = Path(context.configuration["audit"]["path"])
    lines = audit_path.read_text().splitlines()
    events = []
    for line in lines:
        try:
            events.append(json.loads(line)["event"])
        except Exception:
            events.append(line.strip())
    return events


# ============================================================================
# Response validator
# ============================================================================

@then('the gateway responds with "{reason}"')
def step_gateway_response(context, reason):
    if reason == "ok":
        assert context.response.status == "ok"
    else:
        assert context.response.status == "error"
        assert context.response.reason == reason


# ============================================================================
# Audit order validator
# ============================================================================

@then("the audit log contains at least these entries in order:")
def step_audit_order(context):
    events = _audit_events(context)
    expected = [row[0] for row in context.table]

    idx = 0
    for event in events:
        if event == expected[idx]:
            idx += 1
            if idx == len(expected):
                break

    assert idx == len(expected), (
        f"Order mismatch:\n"
        f"  audit:    {events}\n"
        f"  expected: {expected}"
    )


# ============================================================================
# Background
# ============================================================================

@given("a clean gateway environment")
def step_clean_env(context):
    # Environment is prepared in environment.py
    pass


# ============================================================================
# Scenario: Accept valid message
# ============================================================================

@given("a valid message")
def step_valid_message(context):
    algo = HMACAlgorithm()
    key_hex = "aa" * 32

    keys_path = Path(context.configuration["crypto"]["keys_file"])
    keys_path.write_text(json.dumps({"dev_key": key_hex}))

    payload = {"id": 1, "counter": 1, "msg": "hello"}
    mac = algo.sign(payload, bytes.fromhex(key_hex))
    context.message = {**payload, "hmac": mac}


@when("the gateway processes the message")
async def step_process_message(context):
    context.response = await context.gateway.process(context.message)


# ============================================================================
# Scenario: Reject message with invalid schema
# ============================================================================

@given("a message missing required fields")
def step_invalid_schema(context):
    # Missing msg and hmac
    context.message = {"id": 1, "counter": 1}


# ============================================================================
# Scenario: Reject message with invalid HMAC
# ============================================================================

@given("a message with an invalid HMAC")
def step_invalid_hmac(context):
    payload = {"id": 1, "counter": 1, "msg": "hello"}
    context.message = {**payload, "hmac": "00"}


# ============================================================================
# Scenario: Reject replayed message (counter loaded from file)
# ============================================================================

@given("the gateway starts with a stored counter value")
def step_gateway_stored_counter(context):
    # freshness.json already contains {"counter": 0} from environment.py
    pass


@given("a message with counter 1 is processed successfully")
async def step_first_accept(context):
    algo = HMACAlgorithm()
    key_hex = "aa" * 32

    keys_path = Path(context.configuration["crypto"]["keys_file"])
    keys_path.write_text(json.dumps({"dev_key": key_hex}))

    payload = {"id": 1, "counter": 1, "msg": "hello"}
    mac = algo.sign(payload, bytes.fromhex(key_hex))
    msg = {**payload, "hmac": mac}

    # FIRST → MESSAGE_ACCEPTED (increment = 1 because last=0)
    await context.gateway.process(msg)

    context.last_payload = payload
    context.last_hmac = mac


@given("the same message is processed again with the same counter")
async def step_second_accept(context):
    # SECOND → MESSAGE_ACCEPTED (increment = 1 again, depending on your gateway logic)
    msg = {**context.last_payload, "hmac": context.last_hmac}
    await context.gateway.process(msg)


@given("the same message is processed a third time with the same counter")
def step_third_attempt(context):
    # THIRD → expected to fail freshness (increment = 0)
    context.message = {**context.last_payload, "hmac": context.last_hmac}


@when("the gateway processes the third message")
async def step_process_third(context):
    context.response = await context.gateway.process(context.message)


# ============================================================================
# Scenario: Trigger rotation when interval expired
# ============================================================================

@given("rotation is required")
def step_rotation_required(context):
    context.configuration["crypto"]["rotation_required"] = True


@given("an initial message signed with an outdated key")
def step_outdated_key(context):
    algo = HMACAlgorithm()

    keys_path = Path(context.configuration["crypto"]["keys_file"])
    keys_path.write_text(json.dumps({"dev_key": "00" * 32}))

    payload = {"id": 1, "counter": 1, "msg": "init"}
    mac = algo.sign(payload, b"0" * 32)
    context.initial_message = {**payload, "hmac": mac}


@when("the gateway processes the initial message")
async def step_process_initial(context):
    context.response = await context.gateway.process(context.initial_message)


@then('the audit log contains "ROTATION" as the first event')
def step_rotation_first(context):
    events = _audit_events(context)
    assert events[0] == "KEY_ROTATED"


@when("a valid message signed with the rotated key is processed")
async def step_process_rotated(context):
    algo = HMACAlgorithm()

    keys_path = Path(context.configuration["crypto"]["keys_file"])
    rotated_key_hex = json.loads(keys_path.read_text())["dev_key"]

    payload = {"id": 1, "counter": 2, "msg": "hello"}
    mac = algo.sign(payload, bytes.fromhex(rotated_key_hex))
    context.message = {**payload, "hmac": mac}

    context.response = await context.gateway.process(context.message)
