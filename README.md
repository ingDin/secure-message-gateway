<div align="center">
<pre>
╔════════════════════════════════════╗
║      SMG-CORE: CRYPTO FABRIC       ║
╠════════════════════════════════════╣
║  • SCHEMA VALIDATION UNIT          ║
║  • KEY ROTATION CONTROLLER         ║
║  • HMAC-SHA256 COMPUTE ENGINE      ║
║  • MONOTONIC COUNTER (ANTI-REPLAY) ║
║  • AUDIT TRACE OUTPUT              ║
╚════════════════════════════════════╝

⇣ VERIFIED • INTEGRITY-PROTECTED • REPLAY-SAFE ⇣

SECURE MESSAGE GATEWAY — SMG‑CORE v1
Deterministic Crypto • Monotonic Counter • Full Audit Trail
</pre>

[![Tests](https://img.shields.io/badge/Tests-GitHub%20Actions-blue.svg)](https://github.com/ingDin/secure-message-gateway/actions)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/ingDin/secure-message-gateway?tab=MIT-1-ov-file)

</div>

---

## 🔐 What is Secure Message Gateway?

**Secure Message Gateway** is a minimal, extensible Python security layer designed for systems that require:

- **Message integrity** via HMAC  
- **Freshness protection** (anti‑replay counters)  
- **Async key loading & rotation**  
- **Audit logging** for every operation  
- **Strict JSON schema validation**  
- **Full test coverage** (unit, integration, acceptance)

It is built for **safety‑critical environments**, embedded systems, and distributed architectures where message trust is mandatory.

---

## 📦 Installation

To set up the secure-message-gateway in a clean, isolated environment:

```bash
pip install -r requirements.txt
pip install -e .
python -m venv .venv
```

This installs the gateway package and exposes all core subsystems:

- HMAC engine (cryptographic integrity)
- Freshness Manager (monotonic counter + replay protection)
- Key Loader & Rotation (key lifecycle)
- Audit Logger (append‑only JSON-lines)
- GatewayAsync pipeline (deterministic orchestration)

---

## 🚀 Get Started

Before running the gateway with `python src/main`, you must configure three fields that directly affect how the freshness counter behaves at startup:

- `initial_counter`
- `reset_on_start`
- `counter_file`

These determine how the gateway initializes and validates the monotonic counter for the first and subsequent messages.

---

## 🔄 Freshness Counter Basics

The freshness subsystem stores its monotonic counter in:

`config/freshness.json`

At startup, the gateway decides which counter value to use based on:

- the config (`initial_counter`)
- the stored file (`freshness.json`)
- the reset policy (`reset_on_start`)

This directly affects the behaviour of `python src/main`.

---

## 🔍 Freshness Initialization Rules

### 1. `initial_counter: N`
This numeric value is used only when `freshness.json` does not exist or when `reset_on_start` is set to `true`.  
If the file already exists and `reset_on_start` is `false`, the gateway will always load the stored counter instead of the configured value.

---

### 2. `initial_counter: "auto"`
The `auto` mode provides adaptive behavior:
- If `freshness.json` exists, the stored counter is loaded.
- If the file is missing, the counter starts at `0`.

This mode is useful in production environments where the gateway should continue from the last known valid counter.

---

### 3. `reset_on_start: true`
When enabled, the gateway overwrites `freshness.json` at every startup.  
The counter is reset to the value defined in `initial_counter` (numeric or `"auto"`).  
This ensures deterministic behavior and is ideal for testing or controlled environments.

---

### 4. `reset_on_start: false`
(This is the case in the current `config.json`.)

The gateway preserves the existing counter stored in `freshness.json`.  
The `initial_counter` value is used only if the file does not exist.  
This is the recommended behavior for production, where counter persistence is required.


---

## ▶️ Runtime Behaviour When Running `python src/main`

The gateway applies freshness rules starting from the **first** processed message whenever a stored counter already exists in `freshness.json`.  
Bootstrap (automatic acceptance of the first message) happens **only** when the counter file is missing.

### Startup sequence
1. The gateway checks whether `freshness.json` exists.  
2. If the file exists, the stored counter is loaded and freshness validation begins immediately.  
3. The first incoming message must respect the increment rules:
   - `min_increment = 1`
   - `max_increment = 5`
4. Any message whose counter does not fall within the allowed increment range results in `FRESHNESS_FAIL`.

### Example timeline
Stored counter = `37`  
You run `python src/main`.

Gateway behaviour:
- First message must be between **38–42**  
- Any value outside this range → `FRESHNESS_FAIL`

---

## 📈 Runtime Execution and Audit Logging

Running the gateway benchmark with:

`python src/main.py`

executes the full processing pipeline and prints performance statistics to the console.  
A typical output looks like:

- **Total messages processed:** 5000  
- **Total time:** 14.0653 seconds  
- **Throughput:** 355.48 messages/sec  

This reflects the end‑to‑end processing speed of the gateway, including HMAC validation, freshness checks, rotation logic, and audit logging.

---

## 📝 Audit Log Entries

All processed messages are recorded in `logs/audit.log`.  
Each entry is stored as a single JSON line, making the log easy to parse, stream, or export.

Example entries:

```log 
{"timestamp": "2026-09-29T21:03:38.850937+00:00", "event": "MESSAGE_ACCEPTED", "payload": {"id": 1, "counter": 1, "msg": "auto-msg-1"}}
{"timestamp": "2026-09-29T21:03:38.860673+00:00", "event": "MESSAGE_ACCEPTED", "payload": {"id": 2, "counter": 2, "msg": "auto-msg-2"}}
```

Each log entry contains:

- **timestamp** — precise UTC time of processing  
- **event** — the gateway event type (e.g., `MESSAGE_ACCEPTED`)  
- **payload** — message metadata including:
  - `id` — message identifier  
  - `counter` — freshness counter value  
  - `msg` — message content  

This format ensures the audit log is fully machine‑readable and suitable for monitoring, replay, or compliance pipelines.

## 📌 Notes

- The gateway logs **every accepted message**, making it easy to track counter progression.  
- The audit log grows line‑by‑line and can be exported or analyzed with standard tools (`jq`, Python, CSV exporters).  
- The benchmark script is designed for high throughput testing and demonstrates the gateway’s performance under load.

---

## 🧪 Test Coverage Overview

The project currently includes **functional tests only**, implemented with `pytest` and organized into three categories:

### 1. Unit Tests
Unit tests validate individual components in isolation.  
They ensure that core modules (HMAC validation, freshness logic, configuration parsing, audit logging, etc.) behave correctly without interacting with other subsystems.

### 2. Integration Tests
Integration tests verify that multiple components work correctly together.  
These tests cover interactions such as:
- HMAC + freshness validation
- counter progression + audit logging
- configuration + runtime behavior

They confirm that the gateway behaves consistently when subsystems are combined.

### 3. Acceptance Tests
Acceptance tests validate the full message-processing pipeline from the perspective of a real user or system.  
They check:
- startup initialization
- sequential message handling
- correct counter increments
- complete audit trail generation

These tests ensure the gateway meets its functional requirements end‑to‑end.

---

## ▶️ Running the Test Suite

All functional tests (unit, integration, acceptance) are executed with:

`pytest tests/`

---

## ⚠️ Note on Performance Testing

The project **does not include performance, load, stress, or concurrency tests**.  
Only functional correctness is covered at this stage.

---

## 📚 Documentation

**Architecture Overview**  
[docs/ARHITECTURE.md](docs/ARHITECTURE.md)  
High‑level system design, pipeline, and execution model.

**Component Architecture**  
[docs/COMPONENTS.md](docs/COMPONENTS.md)  
Module responsibilities, interfaces, and interactions.

**Security Model**  
[docs/SECURITY_MODEL.md](docs/SECURITY_MODEL.md)  
HMAC integrity, freshness protection, and audit guarantees.

**Test Strategy**  
[docs/TEST_STRATEGY.md](docs/TEST_STRATEGY.md)  
Functional tests only: unit, integration, acceptance.


---

## 🔐 License & Responsible Use

This project is distributed under the **MIT License**, a permissive open‑source license that allows reuse, modification, and redistribution with minimal restrictions.

For full legal details, see the license here:  
**[MIT License →](https://github.com/ingDin/secure-message-gateway/blob/main/LICENSE)**
