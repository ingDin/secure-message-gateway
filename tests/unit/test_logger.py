"""
Unit test suite for AuditLogger.

This module validates the correctness, stability, and failure behavior of the
audit logging subsystem responsible for producing append-only, JSON-lines
structured audit events. It ensures deterministic handling of:

- successful event logging
- invalid payload serialization failures
- I/O failures during async writes
- correct append behavior for multiple sequential events

These tests guarantee that upstream gateway components relying on AuditLogger
receive predictable, safe, and contract-respecting behavior, with reliable
forensic traceability.
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
    """
    Provide an isolated temporary audit.log path.

    Ensures:
    - deterministic filesystem behavior
    - no shared audit state across tests
    - reproducible append-only semantics
    """
    return tmp_path / "audit.log"


@pytest.fixture
def audit_logger(log_path):
    """
    Provide an AuditLogger instance bound to the temporary log file.

    Guarantees:
    - isolated logging context
    - predictable event ordering
    - clean state for each test
    """
    return AuditLogger(log_path)


# ============================================================================
# Test suite
# ============================================================================

class TestAuditLogger:
    """
    Unit test suite validating the correctness, stability,
    and contract guarantees of AuditLogger.

    This suite ensures that:
    - valid events are serialized and persisted correctly
    - invalid payloads fail deterministically with TypeError
    - I/O failures propagate without silent corruption
    - multiple events append in strict order, preserving audit integrity

    These checks validate the reliability of the audit subsystem, which forms
    the backbone of observability and forensic traceability in the gateway.
    """

    # ----------------------------------------------------------------------
    # Successful logging
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_log_event_success(self, audit_logger, log_path):
        """
        log_event must serialize and persist valid payloads as JSON-lines.
        """
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
        """
        log_event must raise TypeError when payload is not JSON-serializable.

        This ensures deterministic failure behavior and prevents malformed
        audit entries from being written.
        """
        class NotSerializable:
            pass

        with pytest.raises(TypeError):
            await audit_logger.log_event("BAD", {"obj": NotSerializable()})

    # ----------------------------------------------------------------------
    # I/O failures
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_log_event_io_error(self, audit_logger):
        """
        log_event must propagate underlying I/O failures without masking them.

        Guarantees that audit corruption cannot occur silently.
        """
        with patch("aiofiles.open", side_effect=OSError("boom")):
            with pytest.raises(OSError):
                await audit_logger.log_event("X", {"y": 2})

    # ----------------------------------------------------------------------
    # Multiple append behavior
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_log_event_multiple(self, audit_logger, log_path):
        """
        log_event must append multiple events in strict order, preserving
        append-only semantics.
        """
        await audit_logger.log_event("E1", {"a": 1})
        await audit_logger.log_event("E2", {"b": 2})

        lines = log_path.read_text().splitlines()
        assert len(lines) == 2

        e1 = json.loads(lines[0])
        e2 = json.loads(lines[1])

        assert e1["event"] == "E1"
        assert e2["event"] == "E2"
