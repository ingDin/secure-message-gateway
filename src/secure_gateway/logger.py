"""
@summary
Asynchronous audit logger for the secure‑message‑gateway. Writes structured
JSON‑lines events using non‑blocking file I/O, ensuring that security‑critical
events are logged without blocking the asyncio event loop.

Each log entry is a single JSON object written on its own line, enabling
efficient streaming, tailing, and external ingestion.
"""

from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json
import aiofiles
from typing import Any, Dict


class AuditLogger:
    """
    @summary
    Asynchronous JSON‑lines audit logger. Produces deterministic, structured,
    timestamped log entries suitable for compliance, monitoring, and forensic
    analysis.

    Example log entry:
    {
        "timestamp": "2025-01-01T12:00:00Z",
        "event": "HMAC_OK",
        "payload": {"id": 42, "counter": 100}
    }

    @parameters
    log_path : Path
        Filesystem path to the audit log file.

    @examples
    >>> logger = AuditLogger(Path("audit.log"))
    >>> await logger.log_event("MESSAGE_ACCEPTED", {"id": 1})
    """

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path

    @staticmethod
    def _make_entry(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        @summary
        Build a structured audit log entry with a UTC timestamp.

        @parameters
        event_type : str
            Short identifier describing the event (e.g., "HMAC_OK", "REPLAY_FAIL").
        payload : dict
            Contextual data relevant to the event.

        @returns
        dict
            Structured log entry containing timestamp, event type, and payload.

        @examples
        >>> entry = AuditLogger._make_entry("TEST", {"x": 1})
        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "payload": payload,
        }

    async def log_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        @summary
        Append a structured JSON log entry to the audit log file asynchronously.

        @parameters
        event_type : str
            Event identifier (e.g., "HMAC_OK", "REPLAY_FAIL").
        payload : dict
            Additional contextual information about the event.

        @returns
        None

        @raises
        TypeError
            If the payload is not JSON‑serializable.

        @examples
        >>> await logger.log_event("MESSAGE_ACCEPTED", {"id": 42})
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
