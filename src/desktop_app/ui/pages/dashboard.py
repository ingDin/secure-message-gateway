
"""
@summary
Dashboard page for the Secure Message Gateway desktop application.

Displays operational metrics, recent message activity and security
component status. All information is supplied externally.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
    QProgressBar,
)

from desktop_app.components.stat_card import StatCard


class DashboardPage(QWidget):
    """Main monitoring page for the Secure Message Gateway."""

    STATUS_COLORS = {
        "ready": "#10B981",
        "active": "#10B981",
        "responding": "#10B981",
        "available": "#10B981",
        "ok": "#10B981",
        "passed": "#10B981",

        "error": "#F87171",
        "failed": "#F87171",

        "warning": "#FBBF24",
        "pending": "#FBBF24",
        "running": "#FBBF24",

        "not initialized": "#94A3B8",
        "not checked": "#94A3B8",
        "not run": "#94A3B8",
        "unknown": "#94A3B8",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setObjectName("page")

        self._accepted = 0
        self._rejected = 0

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 26, 30, 30)
        main_layout.setSpacing(20)

        # --------------------------------------------------
        # Heading
        # --------------------------------------------------

        heading = QLabel("Gateway Overview")
        heading.setObjectName("pageTitle")

        description = QLabel(
            "Monitor message processing and security components."
        )
        description.setObjectName("pageSubtitle")

        main_layout.addWidget(heading)
        main_layout.addWidget(description)

        # --------------------------------------------------
        # Metric cards
        # --------------------------------------------------

        cards_layout = QGridLayout()
        cards_layout.setSpacing(16)

        self.accepted_card = StatCard(
            "ACCEPTED MESSAGES",
            accent="#10B981",
        )

        self.rejected_card = StatCard(
            "REJECTED MESSAGES",
            accent="#F87171",
        )

        self.success_card = StatCard(
            "VALIDATION SUCCESS",
            accent="#22D3EE",
        )

        self.audit_card = StatCard(
            "AUDIT EVENTS",
            accent="#8B5CF6",
        )

        cards_layout.addWidget(self.accepted_card, 0, 0)
        cards_layout.addWidget(self.rejected_card, 0, 1)
        cards_layout.addWidget(self.success_card, 1, 0)
        cards_layout.addWidget(self.audit_card, 1, 1)

        main_layout.addLayout(cards_layout)

        # --------------------------------------------------
        # Message activity
        # --------------------------------------------------

        activity = QFrame()
        activity.setObjectName("contentCard")

        activity_layout = QVBoxLayout(activity)
        activity_layout.setContentsMargins(22, 20, 22, 20)
        activity_layout.setSpacing(14)

        activity_title = QLabel("Message Processing Activity")
        activity_title.setObjectName("cardHeading")

        self.total_label = QLabel("Total processed messages: 0")
        self.total_label.setObjectName("cardSubtitle")

        self.activity_description = QLabel(
            "No messages have been processed yet."
        )
        self.activity_description.setObjectName("cardSubtitle")

        self.success_progress = QProgressBar()
        self.success_progress.setObjectName("successProgress")
        self.success_progress.setRange(0, 100)
        self.success_progress.setValue(0)
        self.success_progress.setTextVisible(False)
        self.success_progress.setFixedHeight(9)

        self.success_progress.setStyleSheet("""
            QProgressBar {
                background-color: #334155;
                border: none;
                border-radius: 4px;
            }

            QProgressBar::chunk {
                background-color: #10B981;
                border-radius: 4px;
            }
        """)

        activity_layout.addWidget(activity_title)
        activity_layout.addWidget(self.total_label)
        activity_layout.addWidget(self.success_progress)
        activity_layout.addWidget(self.activity_description)

        main_layout.addWidget(activity)

        # --------------------------------------------------
        # Security components
        # --------------------------------------------------

        security = QFrame()
        security.setObjectName("contentCard")

        security_layout = QVBoxLayout(security)
        security_layout.setContentsMargins(22, 20, 22, 20)
        security_layout.setSpacing(14)

        security_title = QLabel("Security Components")
        security_title.setObjectName("cardHeading")

        security_layout.addWidget(security_title)

        self.security_labels = {}

        components = [
            ("gateway", "Gateway Connection"),
            ("hmac", "HMAC Verification"),
            ("freshness", "Freshness Validation"),
            ("schema", "Schema Validation"),
        ]

        for key, title in components:
            row = QHBoxLayout()

            name_label = QLabel(title)
            name_label.setObjectName("cardSubtitle")

            status_label = QLabel("Not checked")
            status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            status_label.setStyleSheet(
                "color: #94A3B8; font-weight: normal;"
            )

            row.addWidget(name_label)
            row.addStretch()
            row.addWidget(status_label)

            security_layout.addLayout(row)

            self.security_labels[key] = status_label

        main_layout.addWidget(security)
        main_layout.addStretch()

    # ======================================================
    # Public update methods
    # ======================================================

    def update_metrics(
        self,
        accepted: int,
        rejected: int,
        audit_events: int,
    ) -> None:
        """Update message processing metrics."""

        if accepted < 0 or rejected < 0 or audit_events < 0:
            raise ValueError("Metric values cannot be negative.")

        self._accepted = accepted
        self._rejected = rejected

        total = accepted + rejected

        success_rate = (
            accepted / total * 100
            if total > 0 else None
        )

        self.accepted_card.set_value(str(accepted))
        self.rejected_card.set_value(str(rejected))
        self.audit_card.set_value(str(audit_events))

        self.success_card.set_value(
            f"{success_rate:.1f}%"
            if success_rate is not None else "N/A"
        )

        self.total_label.setText(
            f"Total processed messages: {total}"
        )

        self.success_progress.setValue(
            round(success_rate)
            if success_rate is not None else 0
        )

        if total == 0:
            self.activity_description.setText(
                "No messages have been processed yet."
            )
        else:
            self.activity_description.setText(
                f"{accepted} accepted  |  "
                f"{rejected} rejected  |  "
                f"{success_rate:.1f}% success rate"
            )

    def update_security_status(
        self,
        gateway: str = "Not checked",
        hmac: str = "Not run",
        freshness: str = "Not run",
        schema: str = "Not run",
    ) -> None:
        """Update security component statuses."""

        statuses = {
            "gateway": gateway,
            "hmac": hmac,
            "freshness": freshness,
            "schema": schema,
        }

        for key, status in statuses.items():
            label = self.security_labels[key]
            label.setText(status)

            color = self.STATUS_COLORS.get(
                status.strip().lower(),
                "#94A3B8",
            )

            label.setStyleSheet(
                f"color: {color}; font-weight: normal;"
            )

    def update_recent_activity(self, message: str) -> None:
        """Update the activity description."""

        self.activity_description.setText(message)
