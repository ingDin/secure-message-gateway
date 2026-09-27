"""
Behave step definitions for validating the secure-message-gateway
acceptance scenarios.
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
# Generic response step (ONE definition only)
# ============================================================================

@then('the gateway responds with "{reason}"')
def step_gateway_response(context, reason):
    if reason == "ok":
        assert context.response.status == "ok"
    else:
        assert context.response.status == "error"
        assert context.response.reason == reason


# ============================================================================
# Generic audit table validator (ONE definition only)
# ============================================================================

@then("the audit log contains entries in order:")
def step_audit_order(context):
    events = _audit_events(context)
    expected = [row[0] for row in context.table]

    print("AUDIT PATH:", context.configuration["audit"]["path"])
    print("AUDIT CONTENT:", events)
    print("EXPECTED:", expected)
    print("table:",context.table)

    assert events == expected


# ============================================================================
# Generic single-entry audit validator (ONE definition only)
# ============================================================================

@then('the audit log contains exactly 1 entry "{event}"')
def step_single_event(context, event):
    assert _audit_events(context) == [event]


# ============================================================================
# Background
# ============================================================================

@given("a clean gateway environment")
def step_clean_env(context):
    pass


# ============================================================================
# 1. Valid message → ok
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


# ============================================================================
# UNIVERSAL When step (ONE definition only)
# ============================================================================

@when("the gateway processes the message")
async def step_process_message(context):
    context.response = await context.gateway.process(context.message)


# ============================================================================
# 2. Invalid schema → SCHEMA_FAIL
# ============================================================================

@given("a message missing required fields")
def step_invalid_schema(context):
    context.message = {"id": 1, "counter": 1}  # missing msg + hmac


# ============================================================================
# 3. Wrong HMAC → HMAC_FAIL
# ============================================================================

@given("a message with an invalid HMAC")
def step_invalid_hmac(context):
    payload = {"id": 1, "counter": 1, "msg": "hello"}
    context.message = {**payload, "hmac": "00"}


# ============================================================================
# 4. Replay → FRESHNESS_FAIL
# ============================================================================

@given("a previously accepted message")
async def step_previously_accepted(context):
    algo = HMACAlgorithm()
    key_hex = "aa" * 32

    keys_path = Path(context.configuration["crypto"]["keys_file"])
    keys_path.write_text(json.dumps({"dev_key": key_hex}))

    payload = {"id": 1, "counter": 1, "msg": "hello"}
    mac = algo.sign(payload, bytes.fromhex(key_hex))
    msg = {**payload, "hmac": mac}

    # FIRST gateway call → MESSAGE_ACCEPTED
    await context.gateway.process(msg)

    context.last_payload = payload


@given("a replayed message with the same counter")
def step_replay(context):
    algo = HMACAlgorithm()
    key_hex = json.loads(Path(context.configuration["crypto"]["keys_file"]).read_text())["dev_key"]

    payload = context.last_payload
    mac = algo.sign(payload, bytes.fromhex(key_hex))

    context.message = {**payload, "hmac": mac}


# ============================================================================
# 5. Rotation interval expired → rotation event logged
# ============================================================================

@given("rotation is required")
def step_rotation_required(context):
    context.configuration["crypto"]["rotation_required"] = True


@given("an initial message signed with an outdated key")
def step_outdated_key(context):
    algo = HMACAlgorithm()

    keys_path = Path(context.configuration["crypto"]["keys_file"])
    keys_path.write_text(json.dumps({"dev_key": "00" * 32}))  # outdated key

    payload = {"id": 1, "counter": 1, "msg": "init"}
    mac = algo.sign(payload, b"0" * 32)
    context.initial_message = {**payload, "hmac": mac}


@when("the gateway processes the initial message")
async def step_process_initial(context):
    context.response = await context.gateway.process(context.initial_message)


@then('the audit log contains "ROTATION" as the first event')
def step_rotation_first(context):
    events = _audit_events(context)
    assert events[0] == "ROTATION"


@when("a valid message signed with the rotated key is processed")
async def step_process_rotated(context):
    algo = HMACAlgorithm()

    keys_path = Path(context.configuration["crypto"]["keys_file"])
    rotated_key_hex = json.loads(keys_path.read_text())["dev_key"]

    payload = {"id": 1, "counter": 2, "msg": "hello"}
    mac = algo.sign(payload, bytes.fromhex(rotated_key_hex))
    context.message = {**payload, "hmac": mac}

    context.response = await context.gateway.process(context.message)
