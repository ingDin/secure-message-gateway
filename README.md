# 🚀 secure-message-gateway

⚡ Ultra‑Secure, Ultra‑Fast Message Validation & Protection  
HMAC • Freshness • Deterministic Pipeline • Full Test Suite

![Python](https://img.shields.io/badge/Python-3.10+-yellow.svg)
![Asyncio](https://img.shields.io/badge/Asyncio-Ready-green.svg)
![Security](https://img.shields.io/badge/Security-HMAC%20%2B%20Freshness-critical.svg)
![Coverage](https://img.shields.io/badge/pytest-Full%20Coverage-brightgreen.svg)
![Architecture](https://img.shields.io/badge/Architecture-Clean%20Design-blue.svg)

---

## 🔧 Architecture Snapshot

<br>
<p align="center">
  <img src="assets/secure_gateway_image.png" width="300">
</p>
<br>

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

## ⚡ Key Features

- 🔐 **HMAC‑SHA256 signing & verification**  
- 🕒 **Monotonic freshness counters (anti‑replay)**  
- 📜 **Deterministic validation pipeline**  
- 🔄 **Config‑driven key rotation**  
- 📝 **Structured audit logging (JSON lines)**  
- ⚡ **Async gateway for high‑throughput systems**  
- 📦 **Strict schema validation (DTO models)**  
- 🧪 **Full test suite: unit, integration, BDD**  
- 📁 **Reproducible JSON test vectors**  
- 🧱 **Clean, extensible architecture**  

Designed to be **fast**, **predictable**, and **production‑ready**. 

---

## 🚀 Use Cases

Perfect for systems that require **trustworthy, verifiable communication**:

- 🔌 **Embedded systems** needing message integrity  
- 🏭 **Industrial controllers** exchanging PDUs  
- 📡 **IoT devices** requiring secure communication  
- 🤖 **Robotics pipelines** with deterministic messaging  
- 🛫 **Safety‑critical systems** (automotive, aerospace, medical)  
- 🐍 **Python microservices** validating external input  
- 📜 **Secure audit logging**  
- 🔐 **HMAC‑based authentication layers**  

If your system can’t afford replay attacks or tampered messages, this gateway fits.

---

## 🧠 Technical Highlights

- ⚡ **Async Python gateway (`asyncio`)**  
- 🔐 **Cryptographic backend (`HMACAlgorithm`)**  
- 🔄 **Key rotation (`KeyFileStore`)**  
- 🕒 **Freshness persistence (`FreshnessStore`)**  
- 📝 **Structured audit logging (`AuditLogger`)**  
- 📦 **Schema validation (`models.py`)**  
- ⚠️ **Deterministic error handling (`exceptions.py`)**  
- 📁 **Reproducible test vectors (`examples.json`)**  

Every component is built for clarity, determinism, and extensibility.

---

## ▶️ Quick Example

```python
from secure_gateway.gateway import GatewayAsync

gateway = GatewayAsync("config/config.json")

msg = {
    "id": 1,
    "counter": 1001,
    "msg": "hello",
    "hmac": "..."
}

response = await gateway.process(msg)
print(response.status, response.reason)
```

---

## ⭐ 6. **Keywords**

```md
## 🔍 Keywords

🔐 HMAC  
🔒 SHA256  
📡 message gateway  
🕒 freshness counter  
🛡️ anti‑replay  
📝 audit logging  
📜 deterministic pipeline  
🐍 Python security  
🔌 embedded messaging  
📦 secure PDU  
🔐 crypto validation  
🔄 key rotation  
⚡ async gateway  
🧱 structured logging  
📏 schema validation  
🔐 secure communication  

