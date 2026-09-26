# Component Architecture — secure-message-gateway

This document describes the internal components of `secure-message-gateway`,
their responsibilities, interfaces, and interactions. It complements the
high-level architecture by detailing the module-level design.

---

## 1. Architectural Snapshot

<div align="center">
  <img src="assets/secure_gateway_image.png" width="340">
</div>

The diagram illustrates the separation between validation, cryptographic
processing, freshness enforcement, audit logging, and orchestration layers.

---

## 2. Component Overview

The gateway is composed of isolated, deterministic modules. Each module has a
single responsibility and communicates through stable interfaces.

### 2.1 gateway.py — Pipeline Orchestrator
**Role:** Coordinates the full message-processing pipeline.  
**Responsibilities:**
- Executes validation → crypto → freshness → logging in fixed order.
- Ensures deterministic behavior for safety-critical systems.
- Provides async entrypoints for external integrations (REST, IPC, embedded).

**Key Interfaces:**
- `process_message(payload: dict) -> GatewayResponse`
- Calls into schema, crypto, freshness, and audit subsystems.

---

### 2.2 schema.py — Structural Validation
**Role:** Enforces strict JSON Schema rules.  
**Responsibilities:**
- Validates message structure before any cryptographic or freshness operations.
- Rejects malformed PDUs (missing fields, extra fields, invalid types).
- Produces `SchemaError` on violation.

**Key Interfaces:**
- `validate(payload: dict) -> None`

---

### 2.3 crypto.py — Cryptographic Backend (HMAC-SHA256)
**Role:** Provides deterministic message authentication.  
**Responsibilities:**
- Deterministic signing using sorted JSON payloads.
- Constant-time verification (`compare_digest`).
- Enforces minimum key length and algorithm allow-list.

**Key Interfaces:**
- `sign(payload: dict, key: bytes) -> str`
- `verify(payload: dict, key: bytes, hmac: str) -> bool`

---

### 2.4 algorithm_base.py / algorithms.py — Crypto Abstraction Layer
**Role:** Defines pluggable cryptographic algorithms.  
**Responsibilities:**
- Abstracts signing/verification operations.
- Allows future algorithms (e.g., HMAC-SHA512, CMAC, Blake2).

**Key Interfaces:**
- `Algorithm.sign(...)`
- `Algorithm.verify(...)`
- `AlgorithmRegistry.get(name: str)`

---

### 2.5 key_manager.py — Key Lifecycle Management
**Role:** Controls key rotation and archival.  
**Responsibilities:**
- Interval-based rotation using configuration rules.
- Timestamped archival of old keys.
- Atomic writes to `keys.json`.

**Key Interfaces:**
- `get_active_key() -> bytes`
- `rotate_if_needed() -> None`

---

### 2.6 key_loader.py — Async Key Storage
**Role:** Provides non-blocking access to key files.  
**Responsibilities:**
- Async read/write for `keys.json` and `keys_archive.json`.
- Structured error handling for corrupted or missing files.

**Key Interfaces:**
- `load_keys() -> dict`
- `write_keys(data: dict) -> None`

---

### 2.7 freshness.py — Monotonic Counter Enforcement
**Role:** Prevents replay attacks and abnormal counter jumps.  
**Responsibilities:**
- Enforces monotonicity, increment rules, drift limits.
- Persists updated counter state asynchronously.
- Raises `FreshnessError` on replay or abnormal increments.

**Key Interfaces:**
- `validate(counter: int) -> None`
- `update(counter: int) -> None`

---

### 2.8 logger.py — Structured Audit Logging
**Role:** Records all pipeline events.  
**Responsibilities:**
- Writes JSON Lines entries with UTC timestamps.
- Non-blocking async logging.
- Logs success, failure, rotation events, freshness updates.

**Key Interfaces:**
- `log(event: str, payload: dict) -> None`

---

### 2.9 exceptions.py — Deterministic Error Taxonomy
**Role:** Defines stable error categories.  
**Responsibilities:**
- Provides predictable error codes for external systems.
- Ensures consistent mapping to `GatewayResponse`.

**Hierarchy:**
- `GatewayError`
  - `SchemaError`
  - `HMACError`
  - `FreshnessError`

---

### 2.10 models.py — Structured Response DTOs
**Role:** Defines deterministic output objects.  
**Responsibilities:**
- Standardized response format for all pipeline outcomes.
- Ensures stable fields for embedded/industrial integrations.

**Key Interfaces:**
- `GatewayResponse(status: str, reason: Optional[str])`

---

## 3. Component Interaction Model

The gateway follows a strict interaction pattern:

    schema.validate()
    ↓
    key_manager.rotate_if_needed()
    ↓
    crypto.verify()
    ↓
    freshness.validate()
    ↓
    audit.log()
    ↓
    GatewayResponse


Each component is independent and can be replaced without modifying pipeline
logic, as long as interfaces remain stable.

---

## 4. Determinism and Isolation

The component architecture enforces:

- deterministic signing (sorted JSON)
- deterministic freshness progression
- deterministic error codes
- deterministic audit event structure

No component introduces nondeterministic behavior.

---

## 5. Extensibility

Components are designed for extension:

- new crypto algorithms via `AlgorithmRegistry`
- custom rotation policies in `KeyManager`
- extended freshness rules in `FreshnessManager`
- alternative audit backends (file → syslog → Kafka)
- schema extensions for new message types

All extensions preserve pipeline determinism.

---

## 6. Summary

This document defines the component-level architecture of `secure-message-gateway`,
detailing module responsibilities, interfaces, and interactions. The design is
modular, deterministic, and suitable for embedded, industrial, and safety-critical
deployments.
