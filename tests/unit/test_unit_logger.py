"""
Unit test suite for AuditLogger.

@resume
    Validates the correctness, stability, and failure behaviour of the audit
    logging subsystem responsible for producing append-only, JSON-lines
    structured audit events.

@scope
    - successful event logging
    - invalid payload serialization failures
    - I/O failures during async writes
    - correct append behaviour for multiple sequential events

@ensures
    Upstream gateway components relying on AuditLogger receive predictable,
    safe, and contract‑respecting behaviour, with reliable forensic traceability.
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
    @resume
        Provides an isolated temporary audit.log path.

    @scope
        - deterministic filesystem behaviour
        - isolated audit state
        - reproducible append-only semantics

    @returns
        Path to a temporary audit.log file.
    """
    return tmp_path / "audit.log"


@pytest.fixture
def audit_logger(log_path):
    """
    @resume
        Provides an AuditLogger instance bound to the temporary log file.

    @scope
        - isolated logging context
        - predictable event ordering
        - clean state for each test

    @returns
        A fresh AuditLogger instance.
    """
    return AuditLogger(log_path)


# ============================================================================
# Test suite
# ============================================================================

class TestAuditLogger:
    """
    @resume
        Contract validation suite for AuditLogger.

    @scope
        - deterministic JSON-lines serialization
        - strict failure signalling for invalid payloads
        - reliable async write semantics
        - correct append-only ordering

    @ensures
        The audit subsystem behaves predictably and supports forensic
        traceability across the gateway pipeline.
    """

    # ----------------------------------------------------------------------
    # Successful logging
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_log_event_success(self, audit_logger, log_path):
        """
        @resume
            Validates successful event logging.
        """

        # --- Arrange ---
        # audit_logger + log_path fixtures already provide isolated state

        # --- Act ---
        await audit_logger.log_event("TEST", {"x": 1})

        # --- Assert ---
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
        @resume
            Validates deterministic rejection of non‑serializable payloads.
        """

        # --- Arrange ---
        class NotSerializable:
            pass

        # --- Act / Assert ---
        with pytest.raises(TypeError):
            await audit_logger.log_event("BAD", {"obj": NotSerializable()})

    # ----------------------------------------------------------------------
    # I/O failures
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_log_event_io_error(self, audit_logger):
        """
        @resume
            Validates deterministic propagation of underlying I/O failures.
        """

        # --- Arrange ---
        # Patch aiofiles.open to simulate I/O failure

        # --- Act / Assert ---
        with patch("aiofiles.open", side_effect=OSError("boom")):
            with pytest.raises(OSError):
                await audit_logger.log_event("X", {"y": 2})

    # ----------------------------------------------------------------------
    # Multiple append behaviour
    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_log_event_multiple(self, audit_logger, log_path):
        """
        @resume
            Validates correct append-only behaviour for sequential events.
        """

        # --- Arrange ---
        # audit_logger + log_path fixtures already provide isolated state

        # --- Act ---
        await audit_logger.log_event("E1", {"a": 1})
        await audit_logger.log_event("E2", {"b": 2})

        # --- Assert ---
        lines = log_path.read_text().splitlines()
        assert len(lines) == 2

        e1 = json.loads(lines[0])
        e2 = json.loads(lines[1])

        assert e1["event"] == "E1"
        assert e2["event"] == "E2"
