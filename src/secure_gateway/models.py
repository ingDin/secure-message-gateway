"""
@summary
Minimal dataclasses used by the secure‑message‑gateway. Defines the standardized
response structure returned after message processing, ensuring consistent and
machine‑readable output for all gateway operations.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class GatewayResponse:
    """
    @summary
    Structured response object returned by the gateway after processing an
    incoming message. Encapsulates both success and deterministic failure states.

    @parameters
    status : str
        Processing result. Expected values:
        - "ok"     → message accepted
        - "error"  → message rejected
    reason : str | None
        Optional error code describing the failure reason. Present only when
        `status="error"`.

    @examples
    >>> GatewayResponse(status="ok")
    GatewayResponse(status='ok', reason=None)

    >>> GatewayResponse(status="error", reason="HMAC_FAIL")
    GatewayResponse(status='error', reason='HMAC_FAIL')
    """

    status: str
    reason: str | None = None
