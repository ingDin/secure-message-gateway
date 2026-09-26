# Architecture Overview

The architecture of `secure-message-gateway` is defined by a combined
Top‑Down (system‑level) and Bottom‑Up (component‑level) design.  
This document describes the structural organization, execution pipeline,
module responsibilities, and deterministic behavior of the gateway.

---

## 1. System-Level Architecture (Top‑Down)

At the system level, the gateway enforces a deterministic validation pipeline
designed for embedded and safety‑critical environments. The pipeline consists of
four major functional domains:

1. **Structural Validation**  
   Ensures message correctness using strict schema rules.

2. **Cryptographic Verification**  
   Applies deterministic HMAC-SHA256 signing and constant‑time verification.

3. **Freshness Enforcement**  
   Validates monotonic counters, increment rules, and drift constraints.

4. **Audit & Observability**  
   Records all events using structured JSON Lines logging.

These domains form a fixed execution sequence:

validation → crypto → freshness → logging → response


The system-level design guarantees:

- deterministic behavior  
- reproducible test vectors  
- predictable error taxonomy  
- extensibility for REST API, monitoring dashboards, and alternative crypto backends  

---

## 2. Component-Level Architecture (Bottom‑Up)

The Bottom‑Up design defines the concrete modules that implement each stage of
the pipeline. Each module is isolated, testable, and replaceable.

### Core Modules

- **crypto.py**  
  Implements HMAC-SHA256 signing and verification.  
  Provides deterministic signing via sorted JSON payloads.

- **freshness.py**  
  Enforces monotonic counters, increment rules, drift limits, and replay
  protection.  
  Persists freshness state using async I/O.

- **logger.py**  
  Writes structured JSON Lines audit entries.  
  Ensures non-blocking logging and strict serializability.

- **gateway.py**  
  Orchestrates the full pipeline.  
  Defines deterministic stage ordering and async execution model.

### Supporting Modules

- **key_manager.py**  
  Handles interval-based key rotation and archival.

- **key_loader.py**  
  Provides async JSON loading/writing for key files.

- **schema.py**  
  Implements strict JSON Schema validation.

- **exceptions.py**  
  Defines deterministic error taxonomy.

- **models.py**  
  Provides standardized DTOs for pipeline output.

---

## 3. Architectural Snapshot

<div align="center">
  <img src="assets/secure_gateway_image.png" width="340">
</div>

The snapshot illustrates the separation between:

- validation layer  
- cryptographic layer  
- freshness subsystem  
- audit subsystem  
- orchestration layer  

Each layer is independent and communicates through deterministic interfaces.

---

## 4. Execution Model

The gateway operates under an asynchronous execution model:

- key loading → async I/O  
- audit logging → async I/O  
- freshness persistence → async I/O  
- crypto operations → sync or executor offload  

This ensures high throughput and non-blocking behavior in embedded or
industrial deployments.

---

## 5. Determinism Guarantees

The architecture enforces determinism through:

- sorted JSON payloads for signing  
- constant-time HMAC verification  
- stable error codes  
- strict schema enforcement  
- atomic freshness updates  
- structured audit events  

No component introduces nondeterministic behavior.

---

## 6. Extensibility

The architecture supports:

- alternative crypto algorithms (via AlgorithmRegistry)  
- custom key rotation policies  
- extended freshness rules  
- alternative audit backends (file → syslog → Kafka)  
- schema extensions for new message types  

All extensions preserve pipeline determinism.

---

## 7. Summary

This architecture defines a deterministic, modular, and auditable message
gateway suitable for embedded, industrial, and safety‑critical systems. 

The combined Top‑Down and Bottom‑Up design ensures both conceptual clarity and
low-level control over each stage of the validation pipeline.
