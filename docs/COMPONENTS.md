# Component Architecture — secure-message-gateway
This document describes the internal components of `secure-message-gateway`,
their responsibilities, interfaces, and interactions. It complements the
high-level architecture by detailing the module-level design.

---

## 1. Module Map — secure-message-gateway

Gateway-ul este format din module independente, fiecare cu responsabilitate unică.
Structura reflectă pipeline-ul determinist:

    [ schema ] → [ key_manager ] → [ crypto ] → [ freshness ] → [ logger ] → [ gateway ]

Fiecare modul comunică prin interfețe stabile și poate fi înlocuit fără a afecta
logica pipeline-ului, atâta timp cât semnăturile rămân compatibile.

---

## 2. Component Overview

The system is composed of independent modules. Each module performs one well‑defined
task and exposes a stable interface. Modules can be replaced or extended without
modifying the pipeline logic, as long as their interfaces remain compatible.

### 2.1 gateway.py — Asynchronous Message‑Processing Pipeline

**Role:** Orchestrates the full security pipeline for incoming messages.

**Responsibilities:**
- Validates message structure using `SchemaValidator`.
- Performs key rotation when required by configuration.
- Loads the active cryptographic key asynchronously.
- Verifies HMAC signatures using the selected algorithm backend.
- Enforces freshness rules via `FreshnessManager`.
- Logs all outcomes (success or failure) using `AuditLogger`.
- Produces standardized `GatewayResponse` objects.

**Key Interfaces (actual):**
- `process(raw: dict) -> GatewayResponse`
- `_check_key_rotation() -> None`


---

### 2.2 schema.py — Strict JSON Schema Validation

**Role:** Enforces structural correctness of incoming gateway messages.

**Responsibilities:**
- Validates message structure using a predefined JSON Schema.
- Ensures all required fields (`id`, `msg`, `counter`, `hmac`) are present.
- Rejects messages with missing fields, extra fields, or invalid types.
- Raises `SchemaError` when validation fails.

**Key Interfaces (actual):**
- `SchemaValidator.validate(message: dict) -> None`


---

### 2.3 hmac.py — Deterministic HMAC‑SHA256 Backend

**Role:** Implements the HMAC‑SHA256 cryptographic backend used by the gateway.

**Responsibilities:**
- Generates secure random keys using `os.urandom`.
- Loads and validates keys from `keys.json` asynchronously.
- Performs deterministic signing using sorted JSON serialization.
- Verifies signatures using constant‑time comparison.
- Provides async wrappers for CPU‑bound signing and verification.

**Key Interfaces (actual):**
- `generate_key(min_len: int) -> str`
- `load_key_async(config) -> bytes`
- `sign(payload, key) -> str`
- `verify(payload, key, expected_hmac) -> None`
- `sign_async(payload, key) -> str`
- `verify_async(payload, key, expected_hmac) -> None`

---

### 2.4 algorithm_base.py / algorithms.py — Crypto Abstraction Layer

**Role:** Provides a unified interface for all cryptographic backends and a registry
for selecting the active algorithm.

**Responsibilities:**
- Defines the abstract `Algorithm` base class that all crypto backends must implement.
- Ensures consistent method signatures for key generation, signing, and verification.
- Exposes a centralized `AlgorithmRegistry` that maps algorithm names to instances.
- Validates algorithm names and raises `HMACError` for unknown algorithms.
- Supplies a global singleton (`ALGORITHM_REGISTRY`) for easy access across the gateway.

**Key Interfaces (actual):**
- `Algorithm.generate_key(min_len: int)`
- `Algorithm.load_key_async(config)`
- `Algorithm.sign(payload, key)`
- `Algorithm.verify(payload, key, expected_hmac)`
- `Algorithm.sign_async(payload, key)`
- `Algorithm.verify_async(payload, key, expected_hmac)`

- `AlgorithmRegistry.get(name: str) -> Algorithm`
- `AlgorithmRegistry.supports(name: str) -> bool`


---

### 2.5 ## key_manager.py — Key Lifecycle Management

**Role:** Handles enterprise-grade key rotation and archival.

**Responsibilities:**
- Loads active keys from `keys.json`.
- Archives old keys into `keys_archive.json` with timestamped names.
- Generates new keys using the configured algorithm from `AlgorithmRegistry`.
- Performs interval-based rotation checks.
- Writes updated key material asynchronously via `KeyFileStore`.

**Key Interfaces (actual):**
- `rotation_needed(config, last_rotation) -> bool`
- `_generate_new_key() -> str`
- `rotate_async() -> None`

---

### 2.6 key_loader.py — Async Key File Loader

**Role:** Provides asynchronous read/write operations for key-related JSON files.

**Responsibilities:**
- Loads `keys.json` and `keys_archive.json` asynchronously.
- Writes updated key material using async file I/O.
- Ensures errors are surfaced as `HMACError`.
- Restricts usage to key files only (not a generic JSON loader).

**Key Interfaces (actual):**
- `load_async(path: Path) -> Dict[str, Any]`
- `write_async(path: Path, content: Dict[str, Any]) -> None`

---

### 2.7 freshness.py — Monotonic Counter Enforcement

**Role:** Enforces replay protection using a monotonic counter stored in `freshness.json`.

**Responsibilities:**
- Loads the current counter asynchronously.
- Validates incoming counter values against all freshness rules:
  - monotonic progression
  - minimum increment
  - maximum increment
  - maximum drift
  - optional out‑of‑range rejection
- Stores updated counter values asynchronously.
- Raises `FreshnessError` for replay attempts or abnormal increments.

**Key Interfaces (actual):**
- `load_async() -> int`
- `store_async(value: int) -> None`
- `validate_and_update_async(incoming: int) -> None`

---

### 2.8 logger.py — Asynchronous Audit Logging

**Role:** Records security‑critical events using non‑blocking JSON‑Lines logging.

**Responsibilities:**
- Builds structured log entries containing timestamp, event type, and payload.
- Validates JSON serializability before writing.
- Appends each entry asynchronously to the audit log file.
- Ensures logging never blocks the asyncio event loop.

**Key Interfaces (actual):**
- `_make_entry(event_type: str, payload: dict) -> dict`
- `log_event(event_type: str, payload: dict) -> None`

---

### 2.9 ## exceptions.py — Deterministic Error Hierarchy

**Role:** Defines the structured exception types used across the gateway.

**Responsibilities:**
- Provides a stable base error (`GatewayError`) for all gateway failures.
- Specializes error categories for schema validation, HMAC verification, and
  freshness enforcement.
- Ensures deterministic error signaling across all pipeline components.

**Hierarchy (actual implementation):**
- `GatewayError` — Base class for all gateway-related errors.
  - `SchemaError` — Raised when a message violates structural schema rules.
  - `HMACError` — Raised when HMAC verification fails or cannot be performed.
  - `FreshnessError` — Raised when monotonic counter validation fails.

---

### 2.10 models.py — Standardized Gateway Response DTO

**Role:** Defines the minimal, deterministic response object returned by the gateway.

**Responsibilities:**
- Encapsulates the final outcome of message processing.
- Provides a stable structure for both success and failure responses.
- Ensures predictable fields for embedded and industrial integrations.

**Key Interfaces (actual):**
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
detailing **module responsibilities**, **interfaces**, and **interactions**. The design is
**modular**, **deterministic**, and suitable for **embedded**, **industrial**, and
**safety-critical deployments**.
