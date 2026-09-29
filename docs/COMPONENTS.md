# Component Architecture — secure-message-gateway
Module-level architecture with explicit separation of **Public APIs** and **Internal APIs**.

---

## 1. Component Overview

`secure-message-gateway` is composed of deterministic, isolated components that cooperate through stable interfaces.  
Pipeline:

**schema → key rotation → key loading → HMAC → freshness → audit → response**

Design principles:
- strict separation of concerns  
- deterministic behavior  
- async I/O for stateful subsystems  
- replaceable components via stable interfaces  

---

## 1.1 gateway_async.py — Asynchronous Message‑Processing Pipeline

### Role
Central orchestrator coordinating the full security pipeline.

### Public API
- `process(raw: dict) -> GatewayResponse`

### Internal API
- `_check_key_rotation() -> None`

### Responsibilities
- schema validation  
- key rotation  
- key loading  
- HMAC verification  
- freshness enforcement  
- audit logging  
- deterministic response generation  

---

## 1.2 schema.py — Strict JSON Schema Validation

### Role
Ensures incoming messages conform to the gateway’s structural contract.

### Public API
- `SchemaValidator.validate(message: dict) -> None`

### Internal API
*(none — fully public validator)*

### Responsibilities
- enforce required fields  
- reject extra fields  
- validate types and constraints  
- raise `SchemaError`  

---

## 1.3 hmac.py — Deterministic HMAC‑SHA256 Backend

### Role
Implements the cryptographic backend used for signing and verifying messages.

### Public API
- `generate_key(min_len: int) -> str`
- `load_key_async(config) -> bytes`
- `sign(payload, key) -> str`
- `verify(payload, key, expected_hmac) -> None`
- `sign_async(payload, key) -> str`
- `verify_async(payload, key, expected_hmac) -> None`

### Internal API
- `_validate_algorithm(config) -> None`

### Responsibilities
- secure key generation  
- async key loading  
- deterministic signing (sorted JSON)  
- constant-time verification  
- algorithm policy enforcement  

---

## 1.4 algorithm_base.py / algorithms.py — Crypto Abstraction Layer

### Role
Defines unified interface for cryptographic backends and provides algorithm registry.

### Public API

#### Algorithm
- `generate_key(min_len)`
- `load_key_async(config)`
- `sign(payload, key)`
- `verify(payload, key, expected_hmac)`
- `sign_async(payload, key)`
- `verify_async(payload, key, expected_hmac)`

#### AlgorithmRegistry
- `get(name: str) -> Algorithm`
- `supports(name: str) -> bool`

### Internal API
*(none — registry is fully public)*

### Responsibilities
- abstract crypto interface  
- deterministic backend lookup  
- global singleton registry  

---

## 1.5 key_manager.py — Key Lifecycle Management

### Role
Handles enterprise-grade key rotation and archival.

### Public API
- `rotation_needed(config, last_rotation) -> bool`
- `rotate_async() -> None`

### Internal API
- `_generate_new_key() -> str`

### Responsibilities
- load active keys  
- archive old keys  
- generate new keys  
- interval-based rotation  
- async persistence  

---

## 1.6 key_loader.py — Async Key File Loader

### Role
Dedicated asynchronous loader/writer for key-related JSON files.

### Public API
- `load_async(path: Path) -> Dict[str, Any]`
- `write_async(path: Path, content: Dict[str, Any]) -> None`

### Internal API
*(none — both methods are public)*

### Responsibilities
- async read/write of key files  
- deterministic `KeyError` signaling  
- strict specialization (not a generic JSON loader)  

---

## 1.7 freshness.py — Monotonic Counter Enforcement

### Role
Provides replay protection using a monotonic counter stored in `freshness.json`.

### Public API
- `bootstrap_async(incoming: int) -> None`
- `validate_rules(incoming: int) -> None`
- `validate_and_update_async(incoming: int) -> None`

### Internal API
- `_load_counter() -> int`
- `_write_counter(value: int) -> None`

### Responsibilities
- config-driven bootstrap  
- monotonic progression  
- min increment  
- max increment (optional rejection)  
- drift constraints  
- async persistence  
- deterministic `FreshnessError` signaling  

---

## 1.8 logger.py — Asynchronous Audit Logging

### Role
Records security-critical events using non-blocking JSON-lines logging.

### Public API
- `log_event(event_type: str, payload: dict) -> None`

### Internal API
- `_make_entry(event_type: str, payload: dict) -> dict`

### Responsibilities
- structured log entries  
- UTC timestamps  
- async append  
- JSON serializability validation  

---

## 1.9 exceptions.py — Deterministic Error Hierarchy

### Role
Defines structured exception types used across the gateway.

### Public API
- `GatewayError`
- `SchemaError`
- `HMACError`
- `FreshnessError`
- `KeyError`

### Internal API
*(none — pure type definitions)*

### Responsibilities
- deterministic error signaling  
- stable hierarchy  
- domain-specific error categories  

---

## 1.10 models.py — Standardized Gateway Response DTO

### Role
Defines the minimal, deterministic response object returned by the gateway.

### Public API
- `GatewayResponse(status: str, reason: Optional[str])`

### Internal API
*(none — pure DTO)*

### Responsibilities
- encapsulate success/failure  
- stable structure for integrations  

---

## 2. Component Interaction Model

The gateway follows a strict interaction pattern:

    SchemaValidator.validate()
    ↓
    KeyManager.rotate_async() (if needed)
    ↓
    Algorithm.load_key_async()
    ↓
    Algorithm.verify_async()
    ↓
    FreshnessManager.validate_and_update_async()
    ↓
    AuditLogger.log_event()
    ↓
    GatewayResponse


---

## 3. Determinism and Isolation

- deterministic signing (sorted JSON)  
- deterministic freshness progression  
- deterministic error codes  
- deterministic audit event structure  

---

## 4. Extensibility

The gateway architecture supports targeted, version‑based evolution.  
Future releases can introduce new capabilities without altering the core pipeline:

- **monotonic buffer (parallel‑safe freshness model)**  
  A v2.0 enhancement enabling out‑of‑order message handling, atomic counter commits, and high‑throughput parallel processing. Replaces sequential freshness validation with a buffer‑based commit mechanism.  
  *Subsequent releases will introduce performance and load testing to validate parallel behavior under high message throughput.*

- **web-based UI for gateway interaction (Playwright-tested)**  
  A lightweight frontend for submitting messages, inspecting responses, and visualizing audit/freshness state. Enables automated end‑to‑end testing using Playwright to validate the full pipeline.

- **external rotation triggers**  
  Support for rotation signals originating outside the gateway (e.g., control systems, orchestration services, or environment-driven triggers), while preserving deterministic key lifecycle behavior.

---

## 5. Summary

This document defines the complete component-level architecture of `secure-message-gateway`, with explicit separation of **Public APIs** and **Internal APIs**, fully aligned with the current implementation.

