import json
import os
from pathlib import Path
from behave import given, when, then
from secure_gateway.hmac import HMACAlgorithm


# ---------------------------------------------------------------------------
# Scenario 1: Full pipeline without rotation
# ---------------------------------------------------------------------------

@given("a valid message with correct HMAC")
def step_impl(context):
    algo = HMACAlgorithm()
    payload = {"id": 1, "counter": 1, "msg": "hello"}

    # Write valid key
    keys_path = Path(context.configuration["crypto"]["keys_file"])
    valid_key = os.urandom(32).hex()
    keys_path.write_text(json.dumps({"dev_key": valid_key}))

    mac = algo.sign(payload, bytes.fromhex(valid_key))
    context.msg = {**payload, "hmac": mac}


@when("the gateway processes the message")
async def step_impl(context):
    context.response = await context.gateway.process(context.msg)


@then("the gateway accepts the message")
def step_impl(context):
    assert context.response.status == "ok"


@then("the freshness counter is updated")
def step_impl(context):
    freshness_path = Path(context.configuration["freshness"]["counter_file"])
    data = json.loads(freshness_path.read_text())
    assert data["counter"] == context.msg["counter"]


@then('the audit log contains exactly 1 entry "MESSAGE_ACCEPTED"')
def step_impl(context):
    audit_path = Path(context.configuration["audit"]["path"])
    lines = audit_path.read_text().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["event"] == "MESSAGE_ACCEPTED"


# ---------------------------------------------------------------------------
# Scenario 2: Full rotation pipeline
# ---------------------------------------------------------------------------

@given("rotation is required")
def step_impl(context):
    context.configuration["crypto"]["rotation_required"] = True


@given("an initial message with a fake key")
def step_impl(context):
    algo = HMACAlgorithm()

    # Write fake key
    keys_path = Path(context.configuration["crypto"]["keys_file"])
    keys_path.write_text(json.dumps({"dev_key": "00" * 32}))

    payload_init = {"id": 1, "counter": 1, "msg": "init"}
    fake_mac = algo.sign(payload_init, b"0" * 32)

    context.initial_msg = {**payload_init, "hmac": fake_mac}


@when("the gateway processes the initial message")
async def step_impl(context):
    # Gateway does NOT throw — it returns an error response
    context.response_init = await context.gateway.process(context.initial_msg)


@then('the gateway must log an error "HMAC_FAIL"')
def step_impl(context):
    assert context.response_init.status == "error"
    assert context.response_init.reason == "HMAC_FAIL"


@when("a valid message signed with the rotated key is processed")
async def step_impl(context):
    algo = HMACAlgorithm()

    keys_path = Path(context.configuration["crypto"]["keys_file"])
    keys_data = json.loads(keys_path.read_text())
    rotated_key = bytes.fromhex(keys_data["dev_key"])

    payload = {"id": 1, "counter": 1, "msg": "hello"}
    mac = algo.sign(payload, rotated_key)

    context.msg = {**payload, "hmac": mac}
    context.response = await context.gateway.process(context.msg)


@then("the audit log contains rotation, HMAC_FAIL and MESSAGE_ACCEPTED")
def step_impl(context):
    audit_path = Path(context.configuration["audit"]["path"])
    lines = audit_path.read_text().splitlines()

    assert len(lines) == 3, f"Expected 3 audit lines, got {len(lines)}"

    events = []
    for line in lines:
        try:
            entry = json.loads(line)
            events.append(entry["event"])
        except json.JSONDecodeError:
            # ROTATION is plain text
            if "Rotated key" in line:
                events.append("ROTATION")
            else:
                events.append(line.strip())

    assert "ROTATION" in events, "Rotation event missing"
    assert "HMAC_FAIL" in events, "HMAC_FAIL event missing"
    assert "MESSAGE_ACCEPTED" in events, "MESSAGE_ACCEPTED event missing"
