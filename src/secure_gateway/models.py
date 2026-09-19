from dataclasses import dataclass
from typing import Dict, Any


# ---------------------------------------------------------
# Incoming message (raw JSON from client)
# ---------------------------------------------------------
@dataclass
class IncomingMessage:
    id: int
    msg: str
    counter: int
    hmac: str


# ---------------------------------------------------------
# Gateway response (final output)
# ---------------------------------------------------------
@dataclass
class GatewayResponse:
    status: str
    reason: str | None = None
