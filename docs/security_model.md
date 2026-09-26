# Security Model — secure-message-gateway

This document describes the security model of `secure-message-gateway`, including
trust boundaries, threat assumptions, protection mechanisms, and guarantees
related to integrity, freshness, key lifecycle, input validation, and auditability.

---

## 1. Threat Assumptions

The gateway is designed for environments where:

- **Transport channels may be observable or modifiable**  
  (e.g., fieldbus, CAN, RS‑485, UDP, custom industrial protocols).
- **Attackers can replay previously captured messages.**
- **Attackers can tamper with message payloads.**
- **Attackers may gain partial access to configuration files**  
  (e.g., keys, freshness state), but not full control over runtime.

Out of scope:

- physical attacks on hardware
- side‑channel attacks beyond timing (e.g., power analysis)
- full host compromise (OS/root level)

---

## 2. Trust Boundaries

The security model assumes:

- The **gateway process** is trusted to execute code as designed.
- The **key files** (`keys.json`, `keys_archive.json`) are stored in a
  controlled environment with restricted access.
- The **freshness state** (`freshness.json`) is protected against arbitrary
  modification.
- The **audit logs** are append‑only and not silently truncated or rewritten.

External systems (clients, networks, buses) are considered **untrusted**.

---

## 3. Core Security Properties

### 3.1 Message Integrity

- HMAC-SHA256 is used to authenticate message payloads.
- Signing is deterministic via sorted JSON payloads.
- Verification uses constant‑time comparison to mitigate timing attacks.

**Guarantee:**  
Any modification of the payload or HMAC field is detected and results in
`HMAC_FAIL` and an error `GatewayResponse`.

---

### 3.2 Anti-Replay Protection

- A monotonic counter is enforced per message stream.
- Minimum and maximum increment rules detect abnormal jumps.
- Drift limits prevent delayed or reordered messages from being accepted.
- Replay attempts reuse old counters and are rejected.

**Guarantee:**  
Previously accepted messages cannot be replayed without detection.  
Violations result in `FreshnessError` and `FRESHNESS_FAIL`.

---

### 3.3 Key Lifecycle Security

- Keys are rotated based on configured intervals.
- Old keys are archived with timestamps in `keys_archive.json`.
- Active keys are stored in `keys.json` with controlled access.
- Key operations are atomic to avoid partial writes.

**Guarantee:**  
Key material follows a defined lifecycle, reducing exposure time and enabling
forensic analysis of past states.

---

### 3.4 Input Validation

- Strict JSON Schema is applied before any crypto or freshness logic.
- All required fields must be present and correctly typed.
- No additional properties are allowed.

**Guarantee:**  
Malformed or unexpected input is rejected early with `SchemaError` and
`SCHEMA_FAIL`, preventing undefined behavior in downstream components.

---

### 3.5 Auditability

- All significant events (success, failure, rotation, freshness updates) are
  logged as JSON Lines.
- Each entry includes a UTC ISO8601 timestamp and structured payload