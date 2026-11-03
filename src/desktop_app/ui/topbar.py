"""
@summary
Top navigation bar for the Secure Message Gateway desktop application.

Displays the current page title and application status.
Status information is supplied externally by the application layer.

@architecture
This component belongs to the presentation layer.
It is responsible only for displaying information and does not
perform gateway initialization, connectivity checks, or health checks.

@notes
The application layer is responsible for updating the title and
status through the public methods provided by this component.
"""

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QWidget,
)


class TopBar(QFrame):
    """
    Application header displaying the current page title and system status.

    The component provides a consistent header across the desktop
    application. It separates visual presentation from application
    logic by receiving status updates externally.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        """
        Initialize the application top navigation bar.

        @parameters
        parent:
            Optional parent widget in the Qt widget hierarchy.

        @returns
        None
        """

        super().__init__(parent)

        self.setObjectName("topbar")
        self.setFixedHeight(76)

        # Configure the horizontal layout used by the header.
        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 10, 28, 10)

        # Page title displayed on the left side of the header.
        self.title = QLabel("Dashboard")
        self.title.setObjectName("topbarTitle")

        # Neutral initial status: no application health check has
        # been performed at this stage.
        self.status = QLabel("●  NOT CHECKED")
        self.status.setObjectName("systemStatus")

        # Keep the page title on the left and the status indicator
        # aligned to the right.
        layout.addWidget(self.title)
        layout.addStretch()
        layout.addWidget(self.status)

    def set_title(self, title: str) -> None:
        """
        Update the page title displayed in the header.

        @parameters
        title:
            Text identifying the currently selected application page.

        @returns
        None
        """

        self.title.setText(title)

    def set_status(self, status: str) -> None:
        """
        Update the application status indicator.

        The method only changes the displayed text. It does not
        perform health checks or determine the actual gateway state.

        @parameters
        status:
            Status text supplied by the application layer.

        @returns
        None
        """

        self.status.setText(status)