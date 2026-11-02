
"""
@summary
Top navigation bar for the Secure Message Gateway desktop application.

This module implements the application's horizontal header.
It displays the title of the currently selected application section
and a textual indicator representing the application status.

The component provides a centralized presentation area for
page context and high-level application status information.

@architecture
- Extends QFrame to provide an independent header component.
- Uses QHBoxLayout for horizontal widget organization.
- Exposes public methods for updating the page title and status.
- Uses Qt object names for centralized QSS styling.

@notes
The top navigation bar is presentation-only.
It does not perform gateway health checks or determine the actual
operational state of security components.
Status information must be supplied by the application layer.
"""

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QWidget,
)


class TopBar(QFrame):
    """
    @summary
    Reusable application header displaying page context and status.

    The component contains a dynamic page title and a status label.
    It allows the main window to update both elements without
    directly manipulating the internal QLabel widgets.

    @parameters
    parent : QWidget | None
        Optional parent widget in the Qt object hierarchy.

    @examples
    >>> topbar = TopBar()
    >>> topbar.set_title("Dashboard")
    >>> topbar.set_status("Gateway connected")
    """

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        """
        @summary
        Initialize the top navigation bar and its visual components.

        @parameters
        parent : QWidget | None
            Optional parent widget in the Qt object hierarchy.

        @returns
        None
        """
        super().__init__(parent)

        self.setObjectName("topbar")
        self.setFixedHeight(76)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(28, 10, 28, 10)

        self.title = QLabel("Dashboard")
        self.title.setObjectName("topbarTitle")

        self.status = QLabel("●  UI INITIALIZED")
        self.status.setObjectName("systemStatus")

        layout.addWidget(self.title)
        layout.addStretch()
        layout.addWidget(self.status)

    def set_title(self, title: str) -> None:
        """
        @summary
        Update the title displayed in the application header.

        @parameters
        title : str
            New title identifying the currently selected application page.

        @returns
        None
        """
        self.title.setText(title)

    def set_status(self, status: str) -> None:
        """
        @summary
        Update the textual application status indicator.

        @parameters
        status : str
            Status description supplied by the application layer.

        @returns
        None

        @notes
        This method only updates the displayed text.
        It does not independently verify gateway connectivity
        or security subsystem health.
        """
        self.status.setText(status)
