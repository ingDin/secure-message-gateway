"""
Main application window.

@summary
Coordinates the main Secure Message Gateway desktop interface,
including navigation, page registration, operational status and
dashboard synchronization.

@architecture
- MainWindow coordinates the application-level interface.
- Sidebar provides navigation between registered pages.
- TopBar displays the current page title and gateway status.
- QStackedWidget manages page registration and navigation.
- MessageSimulatorPage delegates processing to GatewayService.
- SecurityValidationPage displays individual validation results.
- DashboardPage displays operational metrics and security status.
- AuditViewerPage displays records from the configured audit log.
- ConfigurationPage provides access to application settings.
- TestExecutionPage provides the automated test execution interface.

@design
MainWindow follows a coordinator-based design.

Individual pages manage their own presentation and specialized
interactions. MainWindow coordinates navigation, communication
between pages and synchronization of shared application state.

Gateway processing, cryptographic operations and message validation
remain delegated to the existing gateway architecture.

@notes
- Audit records are stored in JSON Lines format.
- Dashboard metrics are calculated from valid audit records.
- Dashboard synchronization is performed periodically.
- Gateway status is based on actual message validation results.
- Successful interface initialization does not imply that the
  gateway has been verified or is operational.
- TopBar is a presentation component and does not perform
  independent gateway health checks.
"""

import json

from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QStackedWidget
)

from desktop_app.ui.sidebar import Sidebar
from desktop_app.ui.topbar import TopBar

from desktop_app.ui.pages.dashboard import DashboardPage
from desktop_app.ui.pages.message_simulator import MessageSimulatorPage
from desktop_app.ui.pages.security_validation import SecurityValidationPage
from desktop_app.ui.pages.audit_viewer import AuditViewerPage
from desktop_app.ui.pages.test_execution import TestExecutionPage
from desktop_app.ui.pages.configuration import ConfigurationPage


class MainWindow(QMainWindow):
    """
    @summary
    Creates and manages the main application window, registers
    application pages, coordinates navigation and synchronizes
    operational information between the dashboard and TopBar.

    @architecture
    1. Initialize shared navigation and presentation components.
    2. Create and register application pages.
    3. Load the configured audit log location.
    4. Establish communication between page signals and handlers.
    5. Initialize dashboard metrics and security indicators.
    6. Start periodic dashboard synchronization.
    7. Display the initial application page.

    @design
    MainWindow acts as the integration boundary between individual
    desktop pages.

    It does not directly implement:
    - Message schema validation.
    - HMAC authentication.
    - Message freshness verification.
    - Cryptographic key management.
    - Gateway audit record generation.

    These responsibilities remain within the existing gateway
    processing architecture.

    @notes
    Page registration order must remain synchronized with PAGE_TITLES
    and the navigation indexes exposed by Sidebar.
    """

    PAGE_TITLES = [
        "Dashboard",
        "Message Simulator",
        "Security Validation",
        "Audit Viewer",
        "Test Execution",
        "Configuration",
    ]

    ACCEPTED_EVENTS = {
        "MESSAGE_ACCEPTED",
    }

    REJECTED_EVENTS = {
        "SCHEMA_FAIL",
        "HMAC_FAIL",
        "FRESHNESS_FAIL",
        "GATEWAY_ERROR",
        "UNKNOWN_ERROR",
    }

    STATUS_STYLES = {
        "connected": (
            "color: #10B981; font-weight: bold;"
        ),
        "error": (
            "color: #F87171; font-weight: bold;"
        ),
        "unchecked": (
            "color: #94A3B8; font-weight: bold;"
        ),
    }

    STATUS_LABELS = {
        "connected": "●  GATEWAY CONNECTED",
        "error": "●  GATEWAY ERROR",
        "unchecked": "●  NOT CHECKED",
    }

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        """
        Initialize the main application window.

        @summary
        Creates shared interface components, registers application
        pages, establishes signal connections and initializes
        dashboard synchronization.

        @parameters
        parent : QWidget | None
            Optional parent widget in the Qt object hierarchy.

        @returns
        None

        @notes
        The initial gateway status is explicitly set to Not checked.
        Creating the desktop interface does not verify gateway
        connectivity or successful message processing.
        """

        super().__init__(parent)

        self.setWindowTitle("Secure Message Gateway")
        self.setMinimumSize(1200, 760)

        # Create shared navigation and presentation components.
        self.sidebar = Sidebar()
        self.topbar = TopBar()
        self.stack = QStackedWidget()

        # Instantiate and register the application pages.
        self._create_pages()

        # Initialize security indicators without assuming that
        # the gateway has already processed a message.
        self.dashboard.update_security_status(
            gateway="Not checked",
            schema="Not run",
            hmac="Not run",
            freshness="Not run",
        )

        self._set_topbar_status("unchecked")

        # Assemble the sidebar and central content area.
        self._create_layout()

        # Forward validation results to the dedicated security page.
        self.message_simulator.validation_status_changed.connect(
            self.security_validation.update_validation_status
        )

        # Synchronize validation results with the dashboard
        # and the global gateway status indicator.
        self.message_simulator.validation_status_changed.connect(
            self._handle_dashboard_validation
        )

        # Connect navigation requests to the page controller.
        self.sidebar.navigation_changed.connect(self.navigate)

        # Load the initial operational metrics.
        self.refresh_dashboard()

        # Periodically refresh audit-derived dashboard metrics.
        self.dashboard_timer = QTimer(self)
        self.dashboard_timer.setInterval(5000)
        self.dashboard_timer.timeout.connect(
            self.refresh_dashboard
        )
        self.dashboard_timer.start()

        # Display the Dashboard as the initial application page.
        self.navigate(0)

    def _create_pages(self) -> None:
        """
        Create and register all application pages.

        @summary
        Instantiates each page and adds it to the central
        QStackedWidget in the order defined by PAGE_TITLES.

        @architecture
        - DashboardPage provides operational monitoring.
        - MessageSimulatorPage provides message processing controls.
        - SecurityValidationPage displays validation results.
        - AuditViewerPage displays gateway audit records.
        - TestExecutionPage provides automated test execution.
        - ConfigurationPage provides configuration management.

        @returns
        None

        @raises
        FileNotFoundError
            If the required application configuration cannot be loaded.

        json.JSONDecodeError
            If the application configuration contains invalid JSON.

        @notes
        The audit log path is obtained from the configuration loaded
        by the GatewayService instance owned by MessageSimulatorPage.
        """

        # Register the Dashboard as the first application page.
        self.dashboard = DashboardPage()
        self.stack.addWidget(self.dashboard)

        # Register the message submission and processing interface.
        self.message_simulator = MessageSimulatorPage()
        self.stack.addWidget(self.message_simulator)

        # Register the individual security validation results page.
        self.security_validation = SecurityValidationPage()
        self.stack.addWidget(self.security_validation)

        # Load the normalized audit log location from the gateway
        # configuration instead of duplicating its path in the UI.
        config = self.message_simulator.service.load_config()

        self.audit_log_path = Path(
            config["audit"]["path"]
        )

        self.audit_viewer = AuditViewerPage(
            log_path=self.audit_log_path
        )
        self.stack.addWidget(self.audit_viewer)

        # Register the automated test execution interface.
        self.test_execution = TestExecutionPage()
        self.stack.addWidget(self.test_execution)

        # Register the application configuration interface.
        self.configuration = ConfigurationPage()
        self.stack.addWidget(self.configuration)

    def _create_layout(self) -> None:
        """
        Assemble the main application interface.

        @summary
        Combines the navigation sidebar with the central content area.
        The central area contains the persistent TopBar and the
        QStackedWidget used to display application pages.

        @architecture
        Main layout:
            Central Widget
            ├── Sidebar
            └── Content Area
                ├── TopBar
                └── QStackedWidget

        @returns
        None

        @notes
        The TopBar remains visible while the selected page changes.
        The stacked widget occupies the remaining content area.
        """

        central = QWidget()
        central.setObjectName("centralWidget")

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        content = QWidget()

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Keep the application header visible across all pages.
        content_layout.addWidget(self.topbar)

        # Display the currently selected application page.
        content_layout.addWidget(self.stack)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(content, 1)

        self.setCentralWidget(central)

    def navigate(self, index: int) -> None:
        """
        Navigate to the requested application page.

        @summary
        Updates the central page stack, sidebar selection and
        contextual title displayed by the TopBar.

        @parameters
        index : int
            Zero-based index of the requested application page.

        @returns
        None

        @notes
        Invalid indexes are ignored.

        Dashboard metrics are refreshed when the Dashboard opens.
        Audit records are refreshed when the Audit Viewer opens.
        """

        if not 0 <= index < self.stack.count():
            return

        self.stack.setCurrentIndex(index)
        self.sidebar.set_active(index)

        self.topbar.set_title(
            self.PAGE_TITLES[index]
        )

        # Refresh operational metrics when opening the Dashboard.
        if index == 0:
            self.refresh_dashboard()

        # Reload audit records when opening the Audit Viewer.
        elif index == 3:
            self.audit_viewer.refresh_logs()

    def _set_topbar_status(self, state: str) -> None:
        """
        Update the global gateway status indicator.

        @summary
        Selects the appropriate status text and visual style
        according to the current gateway validation state.

        @parameters
        state : str
            Gateway status identifier.

            Supported values:
            - connected
            - checking
            - error
            - unchecked

        @returns
        None

        @notes
        This method updates presentation only. It does not perform
        gateway initialization, network checks or message processing.

        Unsupported state values are replaced with unchecked.
        """

        if state not in self.STATUS_LABELS:
            state = "unchecked"

        self.topbar.set_status(
            self.STATUS_LABELS[state]
        )

        self.topbar.status.setStyleSheet(
            self.STATUS_STYLES[state]
        )

    def refresh_dashboard(self) -> None:
        """
        Read audit records and update dashboard statistics.

        @summary
        Parses the configured JSON Lines audit log and calculates
        the number of accepted messages, rejected messages and
        recorded audit events.

        @architecture
        1. Verify that the configured audit log exists.
        2. Read audit records sequentially.
        3. Parse each non-empty JSON record.
        4. Ignore malformed or unsupported records.
        5. Classify recognized event types.
        6. Update DashboardPage through its public interface.

        @returns
        None

        @notes
        - The Dashboard does not access the audit filesystem directly.
        - Only valid JSON objects are considered audit records.
        - Unknown events contribute to the total audit event count.
        - File access errors do not interrupt the desktop application.
        - Existing dashboard values are preserved if the file cannot
          be accessed during a refresh operation.
        """

        if not self.audit_log_path.exists():
            self.dashboard.update_metrics(
                accepted=0,
                rejected=0,
                audit_events=0,
            )
            return

        accepted = 0
        rejected = 0
        audit_events = 0

        try:
            with self.audit_log_path.open(
                "r",
                encoding="utf-8",
            ) as log_file:

                for line in log_file:
                    line = line.strip()

                    # Empty lines are not valid audit records.
                    if not line:
                        continue

                    # Ignore malformed JSON records and continue
                    # processing the remaining audit log entries.
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # The audit format is expected to contain JSON objects.
                    if not isinstance(record, dict):
                        continue

                    event = str(
                        record.get("event", "")
                    ).upper()

                    audit_events += 1

                    # Count successfully accepted gateway messages.
                    if event in self.ACCEPTED_EVENTS:
                        accepted += 1

                    # Count known rejection events and other failure events.
                    elif (
                        event in self.REJECTED_EVENTS
                        or event.endswith("_FAIL")
                        or event.endswith("_ERROR")
                    ):
                        rejected += 1

            # Publish the calculated metrics through the Dashboard API.
            self.dashboard.update_metrics(
                accepted=accepted,
                rejected=rejected,
                audit_events=audit_events,
            )

        except OSError:
            # Do not interrupt the interface if the audit log is
            # temporarily unavailable.
            return

    def _handle_dashboard_validation(
        self,
        schema: str,
        hmac: str,
        freshness: str,
    ) -> None:
        """
        Synchronize validation results with dashboard and TopBar status.

        @summary
        Receives validation stage updates emitted by
        MessageSimulatorPage and forwards the results to the
        dashboard and global application status indicator.

        @parameters
        schema : str
            Result of the message schema validation stage.

        hmac : str
            Result of the HMAC authentication stage.

        freshness : str
            Result of the message freshness validation stage.

        @returns
        None

        @architecture
        Signal argument order:
            schema, hmac, freshness

        @notes
        MessageSimulatorPage may emit initial states such as
        "Not run" before background processing begins.

        Receiving a signal alone does not confirm that the gateway
        successfully processed a message.

        The global status is determined by the validation results:
        - All stages Passed: gateway connected.
        - At least one stage Failed: gateway error.
        - At least one stage completed: gateway checking.
        - No stage completed: gateway not checked.
        """

        statuses = {
            "schema": str(schema).strip(),
            "hmac": str(hmac).strip(),
            "freshness": str(freshness).strip(),
        }

        # Normalize values to make comparisons case-insensitive.
        normalized = {
            key: value.lower()
            for key, value in statuses.items()
        }

        # Successful gateway validation requires all three stages
        # to report Passed.
        all_passed = all(
            value == "passed"
            for value in normalized.values()
        )

        # A failed stage takes precedence over partial completion.
        any_failed = any(
            value == "failed"
            for value in normalized.values()
        )

        # Determine the dashboard gateway status from the results.
        if all_passed:
            gateway_status = "Ready"

        elif any_failed:
            gateway_status = "Error"

        else:
            gateway_status = "Not checked"

        # Synchronize the individual validation indicators.
        self.dashboard.update_security_status(
            gateway=gateway_status,
            schema=statuses["schema"],
            hmac=statuses["hmac"],
            freshness=statuses["freshness"],
        )

        # Update the global status indicator using the same results.
        if all_passed:
            self._set_topbar_status("connected")

        elif any_failed:
            self._set_topbar_status("error")

        else:
            self._set_topbar_status("unchecked")

        # Refresh audit-derived operational counters.
        self.refresh_dashboard()