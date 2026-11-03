
"""
@summary

Database-style audit log viewer for Secure Message Gateway.

The page reads only the latest 100 valid records from the
gateway JSON Lines audit log.

@architecture

- AuditLogWorker reads the file backwards in binary blocks.
- Only the latest 100 valid JSON records are retained.
- File reading and JSON parsing run in a background thread.
- AuditViewerPage displays records in a searchable table.
- Double-clicking a row displays its complete JSON payload.
- Timestamps are converted to the Europe/Bucharest timezone.
"""

import json

from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QBrush

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QPlainTextEdit,
    QSplitter,
)


class AuditLogWorker(QThread):
    """
    @summary

    Read the latest audit records without blocking the GUI.

    @architecture

    1. Open the JSON Lines file in binary mode.
    2. Read the file backwards in fixed-size blocks.
    3. Stop after finding the requested number of valid records.
    4. Parse only the selected records.
    5. Emit the records and their search index.

    @signals

    records_loaded(object)
        Emits the loaded records and searchable text.

    error_occurred(str)
        Emits an error if the audit file cannot be read.
    """

    records_loaded = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    BLOCK_SIZE = 8192

    def __init__(
        self,
        log_path: str | Path,
        limit: int = 100,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the audit loading worker."""

        super().__init__(parent)

        self.log_path = Path(log_path)
        self.limit = limit

    def _read_last_lines(self) -> list[bytes]:
        """
        Read the latest non-empty lines without loading the file.

        The file is traversed backwards in fixed-size blocks.
        Memory usage depends primarily on the selected records,
        rather than on the total audit file size.

        Returns
        -------
        list[bytes]
            Latest lines in newest-first order.
        """

        lines: list[bytes] = []
        buffer = b""

        with self.log_path.open("rb") as log_file:
            log_file.seek(0, 2)
            position = log_file.tell()

            while position > 0 and len(lines) < self.limit:
                read_size = min(
                    self.BLOCK_SIZE,
                    position,
                )

                position -= read_size
                log_file.seek(position)

                chunk = log_file.read(read_size)
                buffer = chunk + buffer

                parts = buffer.split(b"\n")

                # Keep the incomplete line at the beginning.
                buffer = parts[0]

                # Remaining complete lines are newest first.
                for line in reversed(parts[1:]):
                    if line.strip():
                        lines.append(line)

                    if len(lines) >= self.limit:
                        break

            # Include the first line if the file does not start
            # with a newline and fewer than limit lines were found.
            if (
                len(lines) < self.limit
                and buffer.strip()
            ):
                lines.append(buffer)

        return lines

    def run(self) -> None:
        """
        Load and parse the latest audit records.

        Malformed JSON records are skipped. The worker does not
        read or parse the older part of the audit file.
        """

        if not self.log_path.exists():
            self.error_occurred.emit(
                f"Audit log file not found: {self.log_path}"
            )
            return

        try:
            raw_lines = self._read_last_lines()

            records: list[dict[str, Any]] = []

            for line in raw_lines:
                try:
                    decoded_line = line.decode("utf-8")
                    record = json.loads(decoded_line)

                    if isinstance(record, dict):
                        records.append(record)

                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue

            # The lines were already collected newest first.
            search_index = [
                json.dumps(
                    record,
                    ensure_ascii=False,
                    default=str,
                ).lower()
                for record in records
            ]

            self.records_loaded.emit(
                (records, search_index)
            )

        except OSError as exc:
            self.error_occurred.emit(
                f"Unable to read audit log: {exc}"
            )


class AuditViewerPage(QWidget):
    """
    @summary

    Displays the latest gateway audit events in a searchable table.

    @parameters

    log_path : str | Path
        Path to the JSON Lines audit log file.

    parent : QWidget | None
        Optional parent widget.
    """

    MAX_RECORDS = 100

    TABLE_COLUMNS = [
        "Timestamp",
        "Event",
        "Message ID",
        "Counter",
    ]

    EVENT_COLORS = {
        "MESSAGE_ACCEPTED": "#22C55E",
        "ROTATION": "#60A5FA",
        "SCHEMA_FAIL": "#EF4444",
        "HMAC_FAIL": "#EF4444",
        "FRESHNESS_FAIL": "#EF4444",
        "GATEWAY_ERROR": "#EF4444",
        "UNKNOWN_ERROR": "#EF4444",
    }

    def __init__(
        self,
        log_path: str | Path,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the audit viewer."""

        super().__init__(parent)

        self.log_path = Path(log_path)

        self.records: list[dict[str, Any]] = []
        self.search_index: list[str] = []

        self.refresh_worker: AuditLogWorker | None = None

        self._build_ui()
        self.refresh_logs()

    def _build_ui(self) -> None:
        """Create the audit viewer interface."""

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 30, 32, 30)
        main_layout.setSpacing(18)

        # Page heading.
        heading = QLabel("Audit Viewer")
        heading.setObjectName("pageTitle")

        subtitle = QLabel(
            "Browse and inspect the latest gateway audit records."
        )
        subtitle.setObjectName("pageSubtitle")

        main_layout.addWidget(heading)
        main_layout.addWidget(subtitle)

        # Search and refresh toolbar.
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Search within the latest 100 records..."
        )
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(
            self._filter_records
        )

        self.records_label = QLabel("Records: 0")
        self.records_label.setObjectName("pageSubtitle")

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(
            self.refresh_logs
        )

        toolbar.addWidget(self.search_input, 1)
        toolbar.addWidget(self.records_label)
        toolbar.addWidget(self.refresh_button)

        main_layout.addLayout(toolbar)

        # Audit records table.
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.TABLE_COLUMNS))
        self.table.setHorizontalHeaderLabels(
            self.TABLE_COLUMNS
        )

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()

        for column in range(4):
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.ResizeToContents,
            )

        # Double-clicking a row displays its complete record.
        self.table.cellDoubleClicked.connect(
            self._show_record_details
        )

        # Record details panel.
        details_title = QLabel("Record Details")
        details_title.setObjectName("pageSubtitle")

        self.details_view = QPlainTextEdit()
        self.details_view.setReadOnly(True)
        self.details_view.setPlaceholderText(
            "Double-click a record to inspect its details."
        )
        self.details_view.setMaximumHeight(190)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.table)

        details_container = QWidget()
        details_layout = QVBoxLayout(details_container)
        details_layout.setContentsMargins(0, 8, 0, 0)
        details_layout.addWidget(details_title)
        details_layout.addWidget(self.details_view)

        splitter.addWidget(details_container)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter, 1)

    def _format_timestamp(self, timestamp: str) -> str:
        """
        Convert an ISO timestamp to Romanian local time.

        Naive timestamps are interpreted as UTC.

        Format: DD.MM.YYYY HH:MM:SS
        """

        try:
            parsed_timestamp = datetime.fromisoformat(
                timestamp.replace("Z", "+00:00")
            )

            if parsed_timestamp.tzinfo is None:
                parsed_timestamp = parsed_timestamp.replace(
                    tzinfo=ZoneInfo("UTC")
                )

            romanian_timestamp = parsed_timestamp.astimezone(
                ZoneInfo("Europe/Bucharest")
            )

            return romanian_timestamp.strftime(
                "%d.%m.%Y %H:%M:%S"
            )

        except (ValueError, TypeError, OverflowError):
            return timestamp

    def refresh_logs(self) -> None:
        """
        Reload only the latest 100 audit records.

        The file is read in a background thread. Older records
        are not loaded into memory or displayed.

        The current search query is preserved.
        """

        if (
            self.refresh_worker is not None
            and self.refresh_worker.isRunning()
        ):
            return

        self.refresh_button.setEnabled(False)
        self.records_label.setText("Loading latest records...")

        self.details_view.clear()
        self.details_view.setPlaceholderText(
            "Loading audit records..."
        )

        worker = AuditLogWorker(
            log_path=self.log_path,
            limit=self.MAX_RECORDS,
        )

        self.refresh_worker = worker

        worker.records_loaded.connect(
            self._on_records_loaded
        )

        worker.error_occurred.connect(
            self._on_load_error
        )

        worker.finished.connect(
            self._on_refresh_finished
        )

        worker.finished.connect(
            worker.deleteLater
        )

        worker.start()

    def _on_records_loaded(
        self,
        result: tuple[
            list[dict[str, Any]],
            list[str],
        ],
    ) -> None:
        """Receive the latest records from the background worker."""

        self.records, self.search_index = result

        # Apply the current search query to the new records.
        self._filter_records(
            self.search_input.text()
        )

    def _on_load_error(self, error_message: str) -> None:
        """Display a loading error without blocking the interface."""

        self.details_view.clear()
        self.details_view.setPlaceholderText(
            error_message
        )

        self.records_label.setText(
            "Unable to load audit records"
        )

    def _on_refresh_finished(self) -> None:
        """Restore the Refresh button after loading completes."""

        self.refresh_button.setEnabled(True)
        self.refresh_worker = None

    def _filter_records(
        self,
        search_text: str = "",
    ) -> None:
        """
        Filter the latest loaded records.

        Search is limited to the records currently held in memory,
        which are at most MAX_RECORDS.
        """

        query = search_text.strip().lower()

        filtered_records = [
            (record, searchable_text)
            for record, searchable_text in zip(
                self.records,
                self.search_index,
            )
            if not query or query in searchable_text
        ]

        self._populate_table(
            [record for record, _ in filtered_records]
        )

        self.records_label.setText(
            f"Showing {len(filtered_records)} / {len(self.records)}"
        )

    def _populate_table(
        self,
        records: list[dict[str, Any]],
    ) -> None:
        """Populate the table with the selected audit records."""

        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(0)

        for record in records:
            row = self.table.rowCount()
            self.table.insertRow(row)

            timestamp = self._format_timestamp(
                str(record.get("timestamp", "N/A"))
            )

            event = str(
                record.get("event", "UNKNOWN")
            )

            payload = record.get("payload", {})

            if not isinstance(payload, dict):
                payload = {"value": payload}

            message_id = str(
                payload.get("id", "—")
            )

            counter = str(
                payload.get("counter", "—")
            )

            values = [
                timestamp,
                event,
                message_id,
                counter,
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)

                item.setFlags(
                    item.flags()
                    & ~Qt.ItemFlag.ItemIsEditable
                )

                if column in (2, 3):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )

                if column == 1:
                    color = self.EVENT_COLORS.get(
                        event,
                        "#94A3B8",
                    )

                    item.setForeground(
                        QBrush(QColor(color))
                    )

                self.table.setItem(
                    row,
                    column,
                    item,
                )

            # Store the complete record for the details panel.
            self.table.item(row, 0).setData(
                Qt.ItemDataRole.UserRole,
                record,
            )

        self.table.setUpdatesEnabled(True)
        self.table.viewport().update()

        self.details_view.clear()
        self.details_view.setPlaceholderText(
            "Double-click a record to inspect its details."
        )

    def _show_record_details(
        self,
        row: int,
        column: int,
    ) -> None:
        """
        Display the complete JSON record associated with a row.

        This method is triggered by double-clicking a table cell.
        """

        if not 0 <= row < self.table.rowCount():
            return

        timestamp_item = self.table.item(row, 0)

        if timestamp_item is None:
            return

        record = timestamp_item.data(
            Qt.ItemDataRole.UserRole
        )

        if not isinstance(record, dict):
            return

        formatted_record = json.dumps(
            record,
            indent=4,
            ensure_ascii=False,
        )

        self.details_view.setPlainText(
            formatted_record
        )
