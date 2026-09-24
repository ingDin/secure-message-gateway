"""
Unit tests for AuditLogger.

Covers:
- successful logging
- invalid payload handling
- I/O failures
- multiple append behavior
"""

import pytest
import json
from unittest.mock import patch

from secure_gateway.logger import AuditLogger


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def log_path(tmp_path):
    """Return a temporary audit.log path."""
    return tmp_path / "audit.log"


@pytest.fixture
def audit_logger(log_path):
    """Return an AuditLogger bound to the temporary log file."""
    return AuditLogger(log_path)


# ============================================================================
# Test suite
# ============================================================================

class TestAuditLogger:
    """Minimal test suite for AuditLogger."""

    # ----------------------------------------------------------------------
    # Successful logging
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_log_event_success(self, audit_logger, log_path):
        """Valid payload should be logged as JSON-lines."""
        await audit_logger.log_event("TEST", {"x": 1})

        entry = json.loads(log_path.read_text())
        assert entry["event"] == "TEST"
        assert entry["payload"] == {"x": 1}
        assert "timestamp" in entry

    # ----------------------------------------------------------------------
    # Invalid payload
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_log_event_invalid_payload(self, audit_logger):
        """Non-serializable payloads should raise TypeError."""
        class NotSerializable:
            pass

        with pytest.raises(TypeError):
            await audit_logger.log_event("BAD", {"obj": NotSerializable()})

    # ----------------------------------------------------------------------
    # I/O failures
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_log_event_io_error(self, audit_logger):
        """I/O errors from aiofiles.open should propagate."""
        with patch("aiofiles.open", side_effect=OSError("boom")):
            with pytest.raises(OSError):
                await audit_logger.log_event("X", {"y": 2})

    # ----------------------------------------------------------------------
    # Multiple append behavior
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_log_event_multiple(self, audit_logger, log_path):
        """Multiple events should append correctly in order."""
        await audit_logger.log_event("E1", {"a": 1})
        await audit_logger.log_event("E2", {"b": 2})

        lines = log_path.read_text().splitlines()
        assert len(lines) == 2

        e1 = json.loads(lines[0])
        e2 = json.loads(lines[1])

        assert e1["event"] == "E1"
        assert e2["event"] == "E2"
