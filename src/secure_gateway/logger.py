from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json
from typing import Any, Dict


# ---------------------------------------------------------
# Audit Logger
# Writes one JSON object per line for lightweight, structured logging.
# Designed for fast append-only operations and easy ingestion by log tools.
# ---------------------------------------------------------
class AuditLogger:
    """
    Minimal JSON-lines audit logger.

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
    # Append a single structured event to the audit log.
    # Timestamp is always UTC for consistency across systems.
    # ---------------------------------------------------------
    def log_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Append an audit event.

        :param event_type: Short identifier (e.g. "HMAC_OK", "REPLAY_FAIL")
        :param payload: Contextual data relevant to the event
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "payload": payload,
        }

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
