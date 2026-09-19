from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json
from typing import Any, Dict


class AuditLogger:
    """
    Simple JSON-lines audit logger.

    Each event is appended as a single JSON object per line:
    {
        "timestamp": "<UTC ISO8601>",
        "event": "<event_type>",
        "payload": { ... }
    }

    This format is deterministic, easy to parse, and compatible with
    log aggregation systems (ELK, Splunk, Datadog).
    """

    def __init__(self, log_path: Path):
        self.log_path = log_path

    def log_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Append an audit event to the log file.

        :param event_type: A short identifier (e.g. "HMAC_OK", "REPLAY_FAIL")
        :param payload: Additional contextual data
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "payload": payload,
        }

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
