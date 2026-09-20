"""
Asynchronous audit logger for the secure gateway.

Writes structured JSON‑lines events using non‑blocking file I/O,
ensuring the gateway can log security‑critical events without
blocking the asyncio event loop.
"""

from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json
import aiofiles
from typing import Any, Dict


# ---------------------------------------------------------
# Internal helper: build a structured JSON log entry
# Reused by both sync and async loggers.
# ---------------------------------------------------------
def _make_entry(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "payload": payload,
    }


# ---------------------------------------------------------
# Async Audit Logger
# Writes one JSON object per line using aiofiles.
# ---------------------------------------------------------
class AuditLoggerAsync:
    """
    Asynchronous JSON-lines audit logger.

    Each event is stored as:
    {
        "timestamp": "<UTC ISO8601>",
        "event": "<event_type>",
        "payload": { ... }
    }
    """

    def __init__(self, log_path: Path):
        self.log_path = log_path

    # ---------------------------------------------------------
    # Append a single structured event asynchronously.
    # ---------------------------------------------------------
    async def log_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Append an audit event asynchronously.

        :param event_type: Short identifier (e.g. "HMAC_OK", "REPLAY_FAIL")
        :param payload: Contextual data relevant to the event
        """
        entry = _make_entry(event_type, payload)

        # Validate JSON serializability
        try:
            line = json.dumps(entry)
        except TypeError as exc:
            raise TypeError("Payload must be JSON-serializable") from exc

        # Append asynchronously
        async with aiofiles.open(self.log_path, "a", encoding="utf-8") as f:
            await f.write(line + "\n")
