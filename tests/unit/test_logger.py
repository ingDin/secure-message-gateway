"""
Unit tests for secure_gateway.logger.

These tests ensure deterministic, structured, and ingestion-friendly
audit logging compatible with ELK / Splunk / Datadog.
"""

import json


# ---------------------------------------------------------
# Tests for single log event
# ---------------------------------------------------------

class TestSingleEvent:
    """Tests for logging a single audit event."""

    def test_log_event_creates_file(self, logger_env):
        """Logging one event should create a file with one JSON line."""
        logger_env.logger.log_event("TEST_EVENT", {"x": 1})

        lines = logger_env.read_lines()
        assert len(lines) == 1

    def test_log_event_json_structure(self, logger_env):
        """Logged event should contain correct fields and ISO8601 timestamp."""
        logger_env.logger.log_event("HMAC_OK", {"id": 123})

        data = logger_env.read_json_lines()[0]

        assert data["event"] == "HMAC_OK"
        assert data["payload"] == {"id": 123}
        assert "timestamp" in data
        assert data["timestamp"].endswith("+00:00")


# ---------------------------------------------------------
# Tests for multiple events
# ---------------------------------------------------------

class TestMultipleEvents:
    """Tests for logging multiple audit events."""

    def test_multiple_events(self, logger_env):
        """Multiple events should append line-by-line and preserve order."""
        logger_env.logger.log_event("A", {"n": 1})
        logger_env.logger.log_event("B", {"n": 2})

        entries = logger_env.read_json_lines()

        assert len(entries) == 2
        assert entries[0]["event"] == "A"
        assert entries[1]["event"] == "B"
