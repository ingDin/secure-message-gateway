
"""
@summary
Security validation page for the Secure Message Gateway desktop application.

This module provides a dedicated interface for displaying the
security validation stages performed by the gateway.

@architecture
- Uses QFrame containers to present individual validation stages.
- Displays schema, HMAC, and freshness validation states.
- Exposes update_validation_status() for external result updates.
- Keeps presentation logic separate from gateway business logic.

@security
The page must never display cryptographic key material or other
sensitive configuration values.

@notes
Validation states are initialized as "Not run".
Actual results must be supplied by the application controller
after gateway message processing.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
)


class SecurityValidationPage(QWidget):
    """
    @summary
    Presentation page for gateway security validation results.

    Displays the current state of the three main validation stages:
    JSON schema validation, HMAC verification, and freshness validation.

    @parameters
    parent : QWidget | None
        Optional parent widget in the Qt object hierarchy.

    @examples
    >>> page = SecurityValidationPage()
    >>> page.update_validation_status(
    ...     schema="Passed",
    ...     hmac="Passed",
    ...     freshness="Passed",
    ... )
    """

    VALIDATION_STAGES = {
        "schema": "JSON Schema Validation",
        "hmac": "HMAC Verification",
        "freshness": "Freshness Validation",
    }

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        """
        @summary
        Initialize the security validation page.

        Creates the page heading, description, and validation cards.

        @parameters
        parent : QWidget | None
            Optional parent widget in the Qt object hierarchy.

        @returns
        None
        """
        super().__init__(parent)

        self.setObjectName("page")

        self.status_labels: dict[str, QLabel] = {}

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 26, 30, 30)
        main_layout.setSpacing(22)

        heading = QLabel("Security Validation")
        heading.setObjectName("pageTitle")

        description = QLabel(
            "Inspect the security checks performed "
            "during message processing."
        )
        description.setObjectName("pageSubtitle")

        main_layout.addWidget(heading)
        main_layout.addWidget(description)

        cards_layout = QGridLayout()
        cards_layout.setSpacing(16)

        positions = {
            "schema": (0, 0),
            "hmac": (0, 1),
            "freshness": (1, 0),
        }

        for stage, title in self.VALIDATION_STAGES.items():
            card = self._create_validation_card(title)

            row, column = positions[stage]
            cards_layout.addWidget(card, row, column)

        main_layout.addLayout(cards_layout)

        information_card = QFrame()
        information_card.setObjectName("contentCard")

        information_layout = QVBoxLayout(information_card)
        information_layout.setContentsMargins(22, 20, 22, 20)
        information_layout.setSpacing(12)

        information_title = QLabel("Validation Pipeline")
        information_title.setObjectName("cardHeading")

        information_description = QLabel(
            "Incoming messages pass through the following security stages:"
        )
        information_description.setObjectName("cardSubtitle")

        pipeline = QLabel(
            "1. JSON Schema Validation\n"
            "   Checks required fields, data types, and constraints.\n\n"
            "2. HMAC Verification\n"
            "   Verifies message authenticity and integrity.\n\n"
            "3. Freshness Validation\n"
            "   Checks the message counter to prevent replay attacks."
        )
        pipeline.setObjectName("cardSubtitle")
        pipeline.setWordWrap(True)

        information_layout.addWidget(information_title)
        information_layout.addWidget(information_description)
        information_layout.addWidget(pipeline)

        main_layout.addWidget(information_card)
        main_layout.addStretch()

        # Initialize all validation stages without assuming success.
        self.update_validation_status(
            schema="Not run",
            hmac="Not run",
            freshness="Not run",
        )

    def _create_validation_card(self, title: str) -> QFrame:
        """
        @summary
        Create a reusable card for an individual validation stage.

        @parameters
        title : str
            Human-readable validation stage title.

        @returns
        QFrame
            Card containing the stage title and its status label.
        """
        card = QFrame()
        card.setObjectName("contentCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("cardHeading")

        status_label = QLabel("Not run")

        stage_key = next(
            key
            for key, stage_title in self.VALIDATION_STAGES.items()
            if stage_title == title
        )

        status_label.setObjectName(f"{stage_key}Status")

        status_label.setStyleSheet("""
            color: #94A3B8;
            font-size: 14px;
            font-weight: normal;
            padding: 4px 0;
        """)

        self.status_labels[stage_key] = status_label

        # Use a stable object name for future styling and UI tests.
        stage_key = next(
            key
            for key, stage_title in self.VALIDATION_STAGES.items()
            if stage_title == title
        )
        status_label.setObjectName(f"{stage_key}Status")

        self.status_labels[stage_key] = status_label

        layout.addWidget(title_label)
        layout.addWidget(status_label)
        layout.addStretch()

        return card

    def update_validation_status(
        self,
        schema: str,
        hmac: str,
        freshness: str,
    ) -> None:
        """
        @summary
        Update the displayed status of each security validation stage.

        @parameters
        schema : str
            Result of JSON schema validation.
        hmac : str
            Result of HMAC verification.
        freshness : str
            Result of freshness validation.

        @returns
        None

        @notes
        The method only updates presentation labels.
        It does not execute or independently verify security checks.
        """
        statuses = {
            "schema": schema,
            "hmac": hmac,
            "freshness": freshness,
        }

        for stage, status in statuses.items():
            self.status_labels[stage].setText(status)
