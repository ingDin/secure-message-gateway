"""
Asynchronous audit logger for the secure gateway.

Writes structured JSON-lines events using non-blocking file I/O,
ensuring the gateway can log security-critical events without
blocking the asyncio event loop.
"""

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import aiofiles
from typing import Any, Dict


class AuditLogger:
    """
    Asynchronous JSON-lines audit logger.

    Writes one JSON object per line using aiofiles.

    Example log entry:
    {
        "timestamp": "2025-01-01T12:00:00Z",
        "event": "HMAC_OK",
        "payload": {"id": 42, "counter": 100}
    }
    """

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path

    # ---------------------------------------------------------
    # Internal helper: build a structured JSON log entry
    # ---------------------------------------------------------
    @staticmethod
    def _make_entry(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "payload": payload,
        }

    # ---------------------------------------------------------
    # Append a single structured event asynchronously.
    # ---------------------------------------------------------
    async def log_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Append a structured JSON log entry to the audit log file.

        :param event_type: Short identifier (e.g. "HMAC_OK", "REPLAY_FAIL")
        :param payload: Contextual data relevant to the event
        """
        entry = self._make_entry(event_type, payload)

        # Validate JSON serializability
        try:
            serialized = json.dumps(entry)
        except TypeError as exc:
            raise TypeError(f"Payload not JSON-serializable: {payload}") from exc

        # Write asynchronously
        async with aiofiles.open(self.log_path, "a", encoding="utf-8") as f:
            await f.write(serialized + "\n")
