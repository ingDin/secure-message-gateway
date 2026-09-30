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

[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-blue.svg)](https://github.com/ingDin/secure-message-gateway/actions)
[![License](https://img.shields.io/badge/License-MIT-red.svg)](https://github.com/ingDin/secure-message-gateway?tab=MIT-1-ov-file)
[![Release v1.0.0](https://img.shields.io/badge/release-v1.0.0-green.svg)](https://github.com/ingDin/secure-message-gateway/releases/tag/v1.0.0)


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
### 🔑 Key Material & Environment Binding

Before running the gateway, users must create a file named **`keys.json`** in the project directory. This file **must be created by the user** and populated with environment‑specific keys in **hexadecimal format**. All keys must be **32 bytes (64 hex characters)** because the gateway uses HMAC‑SHA256.

The required `keys.json` structure is:

```json
{
  "dev_key":   "<64-hex-dev-key>",
  "stage_key": "<64-hex-stage-key>",
  "prod_key":  "<64-hex-prod-key>"
}
```

### 🔧 Environment Selection

The active key is selected based on the environment field inside `config.json`:
```json
{
  "environment": "dev"
}
```

Valid values are:

- `"dev"` → loads dev_key
- `"stage"` → loads stage_key
- `"prod"` → loads prod_key

This mechanism ensures deterministic key selection, **strict environment separation**, and predictable behavior during validation and rotation.

---

## 🔄 Freshness Counter Basics

The freshness subsystem stores its monotonic counter in:

`config/freshness.json`

At startup, the gateway decides which counter value to use based on:

- the config (`initial_counter`)
- the stored file (`freshness.json`)
- the reset policy (`reset_on_start`)

This directly affects the behaviour of `python src/main`.


## 🔍 Freshness Initialization Rules

The gateway enforces increment-based freshness validation as soon as a counter value exists, regardless of how that value was established (loaded or bootstrapped).

### When freshness.json Exists

If `freshness.json` exists, the stored counter is loaded and the very first incoming message must respect the increment rules:
- min_increment = 1
- max_increment = 5

Any violation results in `FRESHNESS_FAIL`.

### When freshness.json Does NOT Exist (Bootstrap)

If the file does not exist:
- `initial_counter = "auto"` → the first message defines the counter.
- `initial_counter = <numeric>` → the counter is set from config.

After bootstrap, increment rules apply immediately to the next message.

### When freshness.json Exists AND reset_on_start = true

If `freshness.json` exists but `reset_on_start = true`, the file MUST be deleted at startup.
After deletion, the gateway behaves exactly as if no counter file ever existed:
- Bootstrap is triggered.
- The initial counter is taken from config (`initial_counter = "auto"` or numeric).
- After bootstrap, increment rules apply immediately.

## Examples

1. File Exists

`freshness.json`:

```json
{"counter": 37}
```

The first incoming message must have a counter between 38 and 42.
Otherwise → `FRESHNESS_FAIL`.

2. Bootstrap Case

`config.json`:
```json
{
  "initial_counter": "auto",
  "min_increment": 1,
  "max_increment": 5
}
```

Message 1: incoming = 100 → bootstrap sets counter = 100  
Message 2: must be between 101 and 105 → otherwise `FRESHNESS_FAIL`

### Final Statement

Freshness rules apply immediately after the counter is established — whether loaded from `freshness.json` or created via bootstrap.

---

## 📈 Runtime Execution and Audit Logging

Running the gateway benchmark with:

`python src/main.py`

executes the full processing pipeline and prints performance statistics to the console. A typical output looks like:

- **Total messages processed:** 5000  
- **Total time:** 14.0653 seconds  
- **Throughput:** 355.48 messages/sec  

This reflects the end‑to‑end processing speed of the gateway, including HMAC validation, freshness checks, rotation logic, and audit logging.

### 📝 Audit Log Entries

All processed messages are recorded in `logs/audit.log`.  
Each entry is stored as a single JSON line, making the log easy to parse, stream, or export.

### Example

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
