# Testing Strategy — secure-message-gateway

This document defines the testing strategy for `secure-message-gateway`,
covering unit, integration, BDD, determinism guarantees, fixture design,
test vectors, and coverage expectations. The goal is to ensure correctness,
predictability, and auditability across all components of the gateway.

---

## 1. Testing Objectives

The testing strategy ensures:

- deterministic behavior across all pipeline stages  
- reproducible cryptographic outputs  
- strict enforcement of freshness rules  
- correct key lifecycle transitions  
- complete audit logging for success/failure paths  
- predictable error taxonomy  
- isolation of components and stable interfaces  

Testing is designed for embedded, industrial, and safety‑critical environments
where message validation must be fully deterministic.

---

## 2. Test Categories

The gateway uses three complementary test layers:

### 2.1 Unit Tests
Unit tests validate individual components in isolation.

**Targets:**
- crypto backend (HMACAlgorithm)
- freshness subsystem (FreshnessManager)
- schema validator (SchemaValidator)
- key lifecycle logic (KeyManager)
- audit logging (AuditLogger)
- deterministic DTOs (GatewayResponse)
- error taxonomy (exceptions.py)

**Characteristics:**
- no external I/O except controlled fixtures  
- deterministic inputs and outputs  
- strict assertion of error codes and messages  

---

### 2.2 Integration Tests
Integration tests validate the full pipeline end‑to‑end.

**Targets:**
- validation → crypto → freshness → logging → response  
- key rotation during pipeline execution  
- freshness state persistence  
- audit log generation for all events  

**Characteristics:**
- use realistic message payloads  
- simulate replay, drift, and abnormal increments  
- verify audit entries and timestamps  
- ensure deterministic ordering of pipeline stages  

---

### 2.3 BDD Acceptance Tests
Behavior‑driven tests validate system behavior from an external perspective.

**Targets:**
- valid message → `ok`  
- invalid schema → `SCHEMA_FAIL`  
- wrong HMAC → `HMAC_FAIL`  
- replay → `FRESHNESS_FAIL`  
- rotation interval expired → rotation event logged  

**Characteristics:**
- human‑readable scenarios  
- stable Given/When/Then structure  
- reproducible test vectors  

---

## 3. Deterministic Test Vectors

Determinism is enforced through:

- sorted JSON payloads for signing  
- fixed keys for crypto tests  
- controlled freshness state fixtures  
- stable timestamps via mock clock  
- constant-time HMAC verification  

Test vectors include:

- known‑answer HMAC tests  
- monotonic counter sequences  
- drift violation sequences  
- replay sequences  
- rotation boundary conditions  

---

## 4. Fixture Design

Fixtures are designed to isolate state and ensure reproducibility.

### 4.1 Crypto Fixtures
- static test keys  
- deterministic payloads  
- known HMAC outputs  

### 4.2 Freshness Fixtures
- controlled `freshness.json` state  
- monotonic sequences  
- drift and increment edge cases  

### 4.3 Key Lifecycle Fixtures
- synthetic rotation intervals  
- archived key snapshots  
- atomic write simulation  

### 4.4 Audit Fixtures
- temporary JSON Lines log files  
- timestamp injection via mock clock  
- structured event validation  

---

## 5. Coverage Model

Coverage expectations:

- **100%** for crypto, freshness, schema, error taxonomy  
- **90%+** for key lifecycle and audit logging  
- **full path coverage** for pipeline execution  
- **all error codes exercised**  
- **all replay and drift rules tested**  

Coverage is measured using `pytest --cov` and validated per module.

---

## 6. Failure Mode Testing

The gateway includes explicit tests for:

- malformed payloads  
- missing fields  
- extra fields  
- invalid types  
- wrong HMAC  
- replay attempts  
- abnormal increments  
- drift violations  
- corrupted key files  
- corrupted freshness state  
- audit write failures  

Each failure mode must produce:

- deterministic error code  
- structured audit entry  
- stable `GatewayResponse`  

---

## 7. Performance & Async Testing

Async behavior is validated through:

- non‑blocking key loading  
- non‑blocking audit logging  
- non‑blocking freshness persistence  
- executor offload for crypto operations  

Performance tests simulate:

- high‑frequency message bursts  
- concurrent validation tasks  
- rotation under load  

---

## 8. Test Directory Structure

    tests/
        unit/
            test_crypto.py
            test_freshness.py
            test_schema.py
            test_key_manager.py
            test_logger.py
            test_models.py
            test_exceptions.py
        
        integration/
            test_gateway.py
            test_rotation.py
            test_audit_flow.py
        
        bdd/
            features/
                steps/

---

## 9. Summary

The testing strategy ensures deterministic, reproducible, and auditable behavior
across all components of `secure-message-gateway`. The combination of unit,
integration, and BDD tests provides full coverage of the validation pipeline,
freshness subsystem, crypto backend, key lifecycle, and audit infrastructure.
