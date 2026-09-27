

```md
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
```
<div align="center">

<!-- BADGES CENTERED -->
![Python](https://img.shields.io/badge/Python-3.10+-yellow.svg)
![Asyncio](https://img.shields.io/badge/Asyncio-Ready-green.svg)
![Security](https://img.shields.io/badge/Security-HMAC%20%2B%20Freshness-critical.svg)
![Coverage](https://img.shields.io/badge/pytest-Full%20Coverage-brightgreen.svg)
![Architecture](https://img.shields.io/badge/Architecture-Clean%20Design-blue.svg)

</div>

---

## ⚡Quickstart

```bash
git clone ...
cd secure-message-gateway
python src/main.py
```

---

## 🔥 Why This Exists

Most embedded systems still exchange raw PDUs with **zero cryptographic guarantees**, **zero freshness protection**, and **zero auditability**.  
That’s a huge attack surface — replay attacks, tampered messages, silent failures.

`secure-message-gateway` fixes this with a **deterministic, cryptographically‑verified, fully‑audited message pipeline** designed for real‑world, safety‑critical environments.

It exists because developers need:

- 🔐 **HMAC‑SHA256 integrity**  
- 🛡️ **Replay‑proof freshness counters**  
- 📏 **Strict schema validation**  
- ⚠️ **Predictable error taxonomy**  
- 📝 **Structured audit logging**  
- 🧪 **Full test coverage (unit + integration + BDD)**  

Built for **embedded**, **industrial**, **IoT**, **robotics**, and **secure messaging** systems that demand trust.

---

# 🚀 Overview

`secure-message-gateway` is an asynchronous, deterministic message‑validation pipeline
designed for embedded, industrial, IoT, and robotics systems that require strict
integrity, anti‑replay protection, and full auditability.

Core components:
- GatewayAsync — orchestrates the full validation pipeline
- SchemaValidator — strict JSON Schema enforcement
- AlgorithmRegistry + HMACAlgorithm — pluggable cryptographic backend
- KeyManager + KeyFileStore — enterprise key rotation & archival
- FreshnessManager — monotonic counter & anti‑replay rules
- AuditLogger — structured JSON Lines audit logging
- GatewayResponse — standardized output DTO
- Exceptions — deterministic error taxonomy

The entire pipeline is asynchronous and non‑blocking.

---

# 🧱 Architecture Overview

The gateway processes every incoming message through a deterministic 7‑step pipeline:

1. **Schema Validation**  
2. **Key Rotation Check**  
3. **Key Loading**  
4. **HMAC Verification**  
5. **Freshness Validation**  
6. **Audit Logging**  
7. **Structured Response**

Each component is modular, testable, and cryptographically agnostic.

---

# 🔐 Cryptographic Backend (HMACAlgorithm)

The HMAC-SHA256 backend provides:

- secure random key generation
- asynchronous key loading from `keys.json`
- minimum key length enforcement
- algorithm allow‑list validation
- deterministic signing (sorted JSON payload)
- constant‑time verification (`hmac.compare_digest`)
- synchronous + asynchronous variants for CPU-bound operations

Deterministic signing ensures reproducible test vectors and predictable behavior.

---

# 🔑 Key Management (KeyManager + KeyFileStore)

## KeyManager
Enterprise-grade key lifecycle management:
- interval-based key rotation
- timestamped archival in `keys_archive.json`
- new key generation via AlgorithmRegistry
- atomic writes to `keys.json`
- audit events for every rotation

Archive naming format:
`<env>_key_archived_<ISO8601 timestamp>`

## KeyFileStore
Asynchronous JSON loader/writer for:
- `keys.json`
- `keys_archive.json`

Provides safe, non-blocking file I/O with structured error handling.

---

# 🕒 Freshness & Anti‑Replay (FreshnessManager)

Configurable rules from `config.json`:
- monotonic counter enforcement
- minimum increment
- maximum increment
- maximum drift
- reject_out_of_range flag

Validation pipeline:
1. Load last counter from `freshness.json`
2. Compute increment
3. Apply all freshness rules
4. Persist updated counter asynchronously

Replay attacks, drift violations, and abnormal increments raise `FreshnessError`.

---

# 📝 Audit Logging (AuditLogger)

AuditLogger writes structured JSON Lines entries:

{
  "timestamp": "2026-09-26T18:00:00Z",
  "event": "HMAC_FAIL",
  "payload": {"id": 42, "counter": 1001}
}

Features:
- non-blocking asynchronous writes
- one JSON object per line
- UTC ISO8601 timestamps
- strict JSON serializability
- used for all success/failure events, including key rotations

---


# 📏 Schema Validation (SchemaValidator)

Strict JSON Schema:

    {
      "id": integer >= 0,
      "msg": string non-empty,
      "counter": integer >= 0,
      "hmac": string non-empty
    }

Rules:
- all fields required
- no additional properties allowed
- raises SchemaError on any violation

Schema validation is always the first step in the pipeline.

---

# ⚠️ Error Taxonomy (exceptions.py)

Deterministic exception hierarchy:

    GatewayError
     ├── SchemaError
     ├── HMACError
     └── FreshnessError

Mapped to gateway response codes:

    SCHEMA_FAIL  
    HMAC_FAIL  
    FRESHNESS_FAIL  
    GATEWAY_ERROR  
    UNKNOWN_ERROR  

All errors are logged via AuditLogger.

---

# 📦 Gateway Response (GatewayResponse)

Standardized DTO:

    @dataclass
    class GatewayResponse:
        status: str        # "ok" | "error"
        reason: str | None # error code

Examples:
- GatewayResponse(status="ok")
- GatewayResponse(status="error", reason="HMAC_FAIL")

---

# 🔍 Technical Keywords

### Cryptography
- HMAC-SHA256
- deterministic signing
- constant-time verification

### Key Lifecycle
- async key loading
- rotation
- archival

### Security
- freshness counters
- anti-replay protection
- schema validation
- error taxonomy

### Async Architecture
- asyncio non-blocking I/O
- JSON Lines audit logging
- structured responses

### Industrial Context
- embedded messaging
- secure PDU validation


---

# 🔐 Security Guarantees

### Message Integrity
- deterministic HMAC-SHA256
- constant-time verification

### Anti-Replay Protection
- monotonic counter
- increment rules
- drift control

### Key Lifecycle Security
- interval-based rotation
- archival with timestamps
- environment-scoped keys

### Input Validation
- strict JSON Schema
- no extra fields allowed

### Auditability
- JSON Lines
- UTC timestamps
- structured events

### Deterministic Error Handling
- stable error codes
- full audit trail

---

# 🧪 Testing Strategy

## Unit Tests
- HMACAlgorithm
- KeyManager
- FreshnessManager
- SchemaValidator
- AuditLogger

## Integration Tests
- full pipeline execution
- crypto + freshness + audit + rotation
- fixture-based message injection
- deterministic counter progression

## BDD Scenarios
- valid message → ok
- invalid schema → SCHEMA_FAIL
- wrong HMAC → HMAC_FAIL
- replay → FRESHNESS_FAIL
- rotation interval expired → ROTATION event

## Reproducible Test Vectors
- sorted JSON payloads
- deterministic HMAC
- predictable counter progression

---

# 🛡️ Threat Model

Protected against:

- Replay Attacks
- Message Tampering
- Partial Key Compromise
- Input Injection
- Silent Failures

All events are logged and auditable.

---

# ⚡ Performance Characteristics

### Async I/O
- non-blocking key loading
- non-blocking audit logging
- non-blocking freshness persistence

### CPU-bound crypto offloading
- async executor for sign/verify

### Deterministic JSON encoding
- compact, sorted payloads

### Throughput
- hundreds to thousands of messages/sec depending on hardware

---

# 🧱 Extensibility Hooks

### Crypto Backends
- implement Algorithm
- register in AlgorithmRegistry

### Key Management
- custom rotation policies
- custom archival strategies

### Freshness Rules
- extend config.json
- extend FreshnessManager

### Audit Logging
- switch backend (file → syslog → Kafka)

### Schema Validation
- extend MESSAGE_SCHEMA

---

# ✅ How to Run (Gateway + Tests)
**Run the gateway (main entry point in src/main.py)**
```bash
python src/main.py
```

This will:

- load config.json
- initialize the full pipeline
- start processing incoming messages (depending on your integration layer)

**Run all tests**

**Unit + Integration**

```bash
pytest -q
```

**BDD (behave acceptance tests)**
```bash
behave
```

Specific test modules

```bash
pytest tests/unit/test_unit_hmac.py -q
pytest tests/unit/test_unit_freshness.py -q
pytest tests/unit/test_unit_gateway.py -q
```

---

# 📁 Directory Structure

    src/
      main.py
      secure_gateway/
        gateway_async.py
        hmac.py
        algorithm_base.py
        algorithms.py
        key_manager.py
        key_loader.py
        freshness.py
        schema.py
        logger.py
        models.py
        exceptions.py
    
    tests/
      unit/
      integration/
      bdd/
        features/
        steps/

---

# 🧾 Summary
This README provides a **full enterprise-level overview** of the gateway, including
**architecture**, **crypto backend**, **key rotation**, **freshness rules**, **audit logging**,
**error taxonomy**, **testing strategy**, **threat model**, **performance characteristics**,
**extensibility hooks**, and **execution instructions**.

The system is **fully modular**, **deterministic**, **auditable**, and suitable for
**industrial-grade deployments**.


## 📄 License
This project is licensed under the MIT License.
See the `LICENSE` file for details.
