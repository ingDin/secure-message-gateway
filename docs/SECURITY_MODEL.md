# SECURITY_MODEL.md
The security model outlines the core guarantees that make the gateway secure, deterministic, and auditable.

---

## 1. Overview

The secure-message-gateway is designed for safety‑critical and audit‑driven environments where **message integrity**, **freshness**, and **deterministic behavior** are mandatory.

The security model is built around:

- strict **schema validation** as the first immutable gate  
- **HMAC‑based integrity** with controlled key lifecycle  
- **freshness enforcement** via monotonic counters and drift limits  
- **append‑only audit logging** with deterministic timestamps  
- **fail‑fast pipeline semantics** and explicit error signaling  

---

## 2. Assets and Trust Boundaries

### 2.1 Protected Assets
- Message payloads (`id`, `counter`, `msg`)  
- Cryptographic keys (`keys.json`, `keys_archive.json`)  
- Freshness state (`freshness.json`)  
- Audit logs (`audit.log`)  
- Gateway logs (`gateway.log`)  

### 2.2 Trust Boundaries
- **Inbound messages**: untrusted, must pass schema + crypto + freshness.  
- **Persistence layer**: trusted but monitored; corruption is treated as a security‑relevant failure.  
- **Key material**: highly sensitive; rotation and archival are strictly controlled.  

---

## 3. Pipeline Security Invariants

The gateway enforces a fixed, deterministic pipeline:

1. **Schema Validation**  
2. **Cryptographic Verification (HMAC)**  
3. **Freshness Enforcement**  
4. **Key Rotation (if required)**  
5. **Audit Logging**  
6. **GatewayResponse Generation**

### 3.1 Fail‑Fast Semantics
- If schema fails → no crypto, no freshness, no rotation.  
- If HMAC fails → no freshness, no rotation (except rotation triggered by invalid key).  
- If freshness fails → no rotation, no acceptance.  
- Any failure → explicit error reason (`SCHEMA_FAIL`, `HMAC_FAIL`, `FRESHNESS_FAIL`) and a single audit event.

---

## 4. Schema Validation Layer

### 4.1 Role
`SchemaValidator` is the **first immutable gate**:

- rejects malformed or structurally invalid messages  
- enforces required fields (`id`, `counter`, `msg`, `hmac`)  
- enforces types and constraints  
- blocks any malformed payload from reaching crypto or freshness subsystems  

### 4.2 Security Guarantees
- No cryptographic or stateful logic is executed for invalid schema.  
- Prevents injection of malformed structures into security‑critical code paths.  

---

## 5. Cryptographic Layer

### 5.1 HMAC Integrity

- Messages are authenticated using **HMAC‑SHA256** over the structured payload.  
- Keys are hex‑encoded and validated for length and algorithm compatibility.  
- Verification is deterministic: valid MAC → accept, invalid MAC → `HMAC_FAIL`.

### 5.2 Key Management and Rotation

- Active key stored in `keys.json`.  
- Old keys archived in `keys_archive.json`.  
- Rotation is triggered when:
  - key material is outdated or invalid, or  
  - rotation policy requires it.  

Rotation guarantees:

- new key generated and persisted atomically  
- old key archived  
- `ROTATION` event logged before any subsequent failure or acceptance  
- sequence enforced: `ROTATION → HMAC_FAIL → MESSAGE_ACCEPTED` in rotation scenarios  

### 5.3 Corruption Handling

- Invalid or unreadable `keys.json` → deterministic `HMAC_FAIL`, pipeline halt, audit event.  
- No silent recovery; corruption is treated as a security failure.

---

## 6. Freshness Layer

### 6.1 Monotonic Counter

`FreshnessManager` enforces:

- **replay protection**: same counter → `FRESHNESS_FAIL`  
- **increment bounds**: too small or too large → `FRESHNESS_FAIL`  
- **drift limits**: excessive jumps → `FRESHNESS_FAIL`  

### 6.2 Persistence

- Counter stored in `freshness.json`.  
- Successful validation → counter updated and persisted deterministically.  
- Corrupted freshness state → pipeline halt, `FRESHNESS_FAIL`, audit event.

### 6.3 Security Guarantees

- Prevents replay attacks and uncontrolled counter drift.  
- Ensures stateful behavior remains predictable and auditable.

---

## 7. Audit and Logging

### 7.1 Append‑Only Audit Log

- Each security‑relevant event is recorded as a JSON line in `audit.log`.  
- Events include: `MESSAGE_ACCEPTED`, `SCHEMA_FAIL`, `HMAC_FAIL`, `FRESHNESS_FAIL`, `ROTATION`.  
- Behavior is strictly append‑only; ordering is deterministic and validated in tests.

### 7.2 Timestamp Determinism

- Timestamps are generated via an injected clock (e.g., freezegun in tests).  
- No direct reliance on system time in the security model.  
- Ensures reproducible, compliance‑grade temporal metadata.

### 7.3 Forensic Traceability

- Every failure path produces a single, well‑defined audit event.  
- Rotation scenarios produce a fully ordered sequence:
  - `ROTATION`  
  - `HMAC_FAIL`  
  - `MESSAGE_ACCEPTED`  

---

## 8. Error Signaling and Determinism

### 8.1 Explicit Reasons

Gateway responses use:

- `status: "ok"` for accepted messages  
- `status: "error"` with:
  - `reason: "SCHEMA_FAIL"`  
  - `reason: "HMAC_FAIL"`  
  - `reason: "FRESHNESS_FAIL"`  

No generic or ambiguous errors; each failure is domain‑specific.

### 8.2 Deterministic Behavior

- Identical valid messages → identical responses and audit entries.  
- Failure paths are stable and reproducible.  
- No hidden retries, no fallback keys, no silent recovery.

---

## 9. Security Posture Summary

The secure-message-gateway’s security model is built on:

- **strict input validation**  
- **cryptographic integrity with controlled key lifecycle**  
- **freshness enforcement and replay protection**  
- **append‑only, ordered, timestamp‑deterministic audit logging**  
- **explicit, domain‑specific error signaling**  
- **fail‑fast, deterministic pipeline behavior**

Together, these guarantees make the gateway suitable for **safety‑critical, industrial, and audit‑driven deployments** where correctness, observability, and determinism are non‑negotiable.
