# secure-message-gateway
Security-focused Python gateway designed for safety‑critical environments (railway, automotive).  
Implements message integrity, freshness protection, secure logging and full pytest coverage.  
Built using a combined **Top‑Down Architecture** and **Bottom‑Up Implementation** approach.

---

## 🏗️ Architectural Approach

### Top‑Down (System-Level Design)
- Define the system responsibilities: validate → verify → protect → log.
- Establish the main components:
  - Gateway Core (message pipeline)
  - Security Layer (HMAC + freshness)
  - Audit Layer (secure logging)
  - Configuration Layer (JSON key store)
- Define data flow:
  - Input JSON → Validation → Crypto → Freshness → Logging → Response
- Ensure extensibility for:
  - REST API
  - Selenium monitoring dashboard
  - CI/CD integration

### Bottom‑Up (Component-Level Construction)
1. **crypto.py** – HMAC-SHA256 signing & verification.
2. **freshness.py** – monotonic counter validation (anti-replay).
3. **logger.py** – rotating audit logs.
4. **gateway.py** – orchestrates validation, crypto, freshness, logging.
5. **config.json** – key store & security parameters.
6. **tests/** – unit, integration, BDD scenarios, mocks, JSON test vectors.

---

## 🔐 Security Features
- Message integrity via HMAC-SHA256.
- Replay protection using freshness counters.
- Secure audit logging with rotation.
- Configurable security parameters (JSON).
- Deterministic behavior suitable for safety-critical systems.

---

## 🧪 Testing Strategy

### Unit Tests (Bottom‑Up)
- crypto: HMAC correctness
- freshness: counter monotonicity
- logger: audit events
- gateway: validation pipeline

### Integration Tests (Top‑Down)
- full message flow from input → validation → crypto → freshness → logging
- invalid HMAC, malformed messages, replay attempts

### BDD (Given–When–Then)
- **Given** a valid message  
- **When** the gateway processes it  
- **Then** it is accepted and logged  

### Mocking & Test Vectors
- mock crypto failures
- JSON-based deterministic test vectors

---

## 📁 Project Structure

    secure-message-gateway/
    │
    ├── src/
    │   └── secure_gateway/          # Python package (import secure_gateway)
    │       ├── __init__.py
    │       ├── gateway.py           # System orchestrator (top‑down)
    │       ├── crypto.py            # HMAC-SHA256 integrity module (bottom‑up)
    │       ├── freshness.py         # Anti-replay monotonic counter (bottom‑up)
    │       ├── logger.py            # Secure audit logging (bottom‑up)
    │       ├── exceptions.py        # Custom exception types
    │       └── models.py            # Data models / DTOs
    │
    ├── config/
    │   ├── config.json              # Security parameters
    │   └── keys.json                # HMAC / future AES-GCM keys
    │
    ├── tests/
    │   ├── unit/                    # Bottom‑up unit tests
    │   │   ├── test_crypto.py
    │   │   ├── test_freshness.py
    │   │   ├── test_logger.py
    │   │   └── __init__.py
    │   │
    │   ├── integration/             # Top‑down integration tests
    │   │   ├── test_gateway_flow.py
    │   │   └── __init__.py
    │   │
    │   ├── bdd/                     # Given / When / Then scenarios
    │   │   ├── test_message_acceptance.py
    │   │   └── __init__.py
    │   │
    │   ├── conftest.py              # Global fixtures & mocks
    │   └── __init__.py
    │
    ├── examples/
    │   ├── valid_message.json       # Test vectors
    │   ├── invalid_hmac.json
    │   └── replay_attack.json
    │
    ├── scripts/
    │   ├── generate_hmac.py         # Key generation utilities
    │   ├── simulate_gateway.py      # Message simulation tool
    │   └── export_logs.py           # Audit log exporter
    │
    ├── logs/
    │   └── gateway.log              # Rotating audit logs
    │
    ├── docs/
    │   ├── architecture.md          # Top‑down architecture documentation
    │   ├── components.md            # Bottom‑up component documentation
    │   ├── security_model.md        # HMAC, freshness, threat model
    │   └── testing_strategy.md      # Unit, integration, BDD testing
    │
    ├── ci/
    │   └── github-actions.yml       # CI/CD pipeline (pytest + lint)
    │
    ├── .gitignore
    ├── README.md
    ├── requirements.txt
    └── LICENSE

---

## ▶️ Getting Started
    git clone https://github.com/ingDin/secure-message-gateway
    cd secure-message-gateway
    pip install -r requirements.txt
    pytest -v

---

## 📌 Roadmap
- REST API interface  
- Selenium monitoring dashboard  
- AES-GCM encryption layer  
- CI/CD pipeline  
- Performance & stress tests  

---

## 📄 License
MIT
