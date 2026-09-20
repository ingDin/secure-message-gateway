"""
Minimal dataclasses used by the secure gateway.

Defines the standardized gateway response structure returned
after message processing.
"""

from dataclasses import dataclass
from typing import Dict, Any

# ---------------------------------------------------------
# Gateway response (final output)
# ---------------------------------------------------------
@dataclass
class GatewayResponse:
    status: str
    reason: str | None = None
