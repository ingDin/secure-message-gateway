"""
Async unit tests for secure_gateway.logger.

These tests validate asynchronous JSON‑Lines logging using aiofiles,
ensuring that audit events are appended correctly with UTC timestamps,
structured payloads, and proper error propagation.
"""

import json
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from pathlib import Path

from secure_gateway.logger import AuditLoggerAsync


class TestAuditLoggerAsync:
    """Tests for asynchronous JSON‑Lines audit logging."""

    @pytest.mark.asyncio
    async def test_log_event_creates_file(self, logger_env):
        """Async logger should create the log file if missing."""
        await logger_env.logger.log_event("TEST_EVENT", {"msg": "hello"})

        assert logger_env.log_path.exists()
        assert logger_env.read_lines() != []

    @pytest.mark.asyncio
    async def test_log_event_writes_valid_json_line(self, logger_env):
        """Each async event should be a valid JSON object on one line."""
        await logger_env.logger.log_event("LOGIN_OK", {"user": "alice"})

        entry = logger_env.read_json_lines()[0]

        assert entry["event"] == "LOGIN_OK"
        assert entry["payload"] == {"user": "alice"}
        assert "timestamp" in entry

    @pytest.mark.asyncio
    async def test_timestamp_is_utc_iso8601(self, logger_env):
        """Timestamp should be UTC ISO8601."""
        await logger_env.logger.log_event("TIME_TEST", {"x": 1})

        entry = logger_env.read_json_lines()[0]
        ts = datetime.fromisoformat(entry["timestamp"])

        assert ts.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_multiple_events_append_correctly(self, logger_env):
        """Async logger should append multiple events as separate lines."""
        await logger_env.logger.log_event("EV1", {"a": 1})
        await logger_env.logger.log_event("EV2", {"b": 2})

        entries = logger_env.read_json_lines()
        assert len(entries) == 2

        assert entries[0]["event"] == "EV1"
        assert entries[1]["event"] == "EV2"

    @pytest.mark.asyncio
    async def test_payload_must_be_json_serializable(self, logger_env):
        """Non‑serializable payloads should raise TypeError."""
        class NotSerializable:
            pass

        with pytest.raises(TypeError):
            await logger_env.logger.log_event("BAD", {"obj": NotSerializable()})

    @pytest.mark.asyncio
    async def test_io_error_propagates(self, logger_env, monkeypatch):
        """I/O errors should propagate in async logger."""

        class FakeContextManager:
            async def __aenter__(self):
                raise OSError("disk full")

            async def __aexit__(self, exc_type, exc, tb):
                return False

        def fake_open(*args, **kwargs):
            return FakeContextManager()

        monkeypatch.setattr("aiofiles.open", fake_open)

        with pytest.raises(OSError):
            await logger_env.logger.log_event("EV", {"x": 1})
