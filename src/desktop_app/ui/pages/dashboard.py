
"""
@summary
Dashboard page for the Secure Message Gateway desktop application.

This module implements the main monitoring interface, providing
a visual overview of message processing metrics and security
component status.

The dashboard is responsible exclusively for presenting operational
information. It does not execute message processing, perform
cryptographic validation, or retrieve audit events directly.

@architecture
- Uses reusable StatCard components for metric presentation.
- Organizes dashboard sections using Qt layouts.
- Separates metric presentation from gateway business logic.
- Exposes update_metrics() as a public interface for updating
  accepted messages, rejected messages, and audit event counts.

@security
The dashboard must display only non-sensitive operational information.
Cryptographic keys and other secret configuration values must never
be presented through dashboard components.

@notes
Metric values are initially displayed as unavailable.
They must be supplied by an application service or controller
when gateway integration is implemented.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
)

from desktop_app.components.stat_card import StatCard


class DashboardPage(QWidget):
    """
    @summary
    Main monitoring page for the Secure Message Gateway application.

    The dashboard provides a centralized presentation of message
    processing statistics, validation success rate, audit activity,
    and security component status.

    All displayed information is supplied externally. The widget
    does not directly interact with gateway internals.

    @parameters
    parent : QWidget | None
        Optional parent widget in the Qt object hierarchy.

    @examples
    >>> dashboard = DashboardPage()
    >>> dashboard.update_metrics(
    ...     accepted=100,
    ...     rejected=5,
    ...     audit_events=105,
    ... )
    """

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        """
        @summary
        Initialize the dashboard and construct its visual sections.

        Creates the page heading, metric cards, message activity
        section, and security component status section.

        @parameters
        parent : QWidget | None
            Optional parent widget in the Qt object hierarchy.

        @returns
        None
        """
        super().__init__(parent)

        self.setObjectName("page")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 26, 30, 30)
        main_layout.setSpacing(22)

        heading = QLabel("Gateway Overview")
        heading.setObjectName("pageTitle")

        description = QLabel(
            "Monitor message processing and security components."
        )
        description.setObjectName("pageSubtitle")

        main_layout.addWidget(heading)
        main_layout.addWidget(description)

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

        activity = QFrame()
        activity.setObjectName("contentCard")

        activity_layout = QVBoxLayout(activity)
        activity_layout.setContentsMargins(22, 20, 22, 20)
        activity_layout.setSpacing(12)

        activity_title = QLabel("Message Processing Activity")
        activity_title.setObjectName("cardHeading")

        activity_description = QLabel(
            "Processing metrics will appear here "
            "after gateway integration."
        )
        activity_description.setObjectName("cardSubtitle")

        activity_layout.addWidget(activity_title)
        activity_layout.addWidget(activity_description)
        activity_layout.addStretch()

        main_layout.addWidget(activity, 1)

        security = QFrame()
        security.setObjectName("contentCard")

        security_layout = QVBoxLayout(security)
        security_layout.setContentsMargins(22, 18, 22, 18)

        security_title = QLabel("Security Components")
        security_title.setObjectName("cardHeading")

        security_status = QLabel(
            "Gateway connection: Not initialized\n"
            "HMAC verification: Awaiting gateway data\n"
            "Freshness validation: Awaiting gateway data\n"
            "Schema validation: Awaiting gateway data"
        )
        security_status.setObjectName("cardSubtitle")

        security_layout.addWidget(security_title)
        security_layout.addWidget(security_status)

        main_layout.addWidget(security)

    def update_metrics(
        self,
        accepted: int,
        rejected: int,
        audit_events: int,
    ) -> None:
        """
        @summary
        Update the dashboard with externally supplied gateway metrics.

        Updates accepted message count, rejected message count,
        audit event count, and calculated validation success rate.

        @parameters
        accepted : int
            Number of successfully accepted messages.
        rejected : int
            Number of rejected messages.
        audit_events : int
            Total number of audit events.

        @returns
        None

        @notes
        The validation success rate is calculated as:

            accepted / (accepted + rejected) * 100

        When no messages have been processed, the success rate
        is displayed as "N/A".

        The method does not retrieve statistics directly from
        the gateway or audit log.
        """
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
