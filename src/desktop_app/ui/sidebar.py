
"""
@summary
Navigation sidebar for the Secure Message Gateway desktop application.

This module implements the application's vertical navigation panel.
It provides navigation buttons for the main application sections
and communicates navigation requests through a Qt signal.

@architecture
- Extends QFrame to provide an independent navigation component.
- Uses QVBoxLayout for vertical widget organization.
- Uses pyqtSignal to communicate navigation events.
- Keeps navigation presentation separate from page management.
- MainWindow is responsible for handling navigation requests.

@notes
The sidebar does not manage application pages directly.
It emits the index of the selected navigation destination,
allowing the main window to coordinate the QStackedWidget.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class Sidebar(QFrame):
    """
    @summary
    Reusable vertical navigation component for the desktop application.

    The sidebar displays the application identity, workspace navigation
    options, and application version information.

    Navigation requests are communicated through the
    navigation_changed signal. The component does not directly
    manipulate the application's page stack.

    @signals
    navigation_changed(int)
        Emitted when a navigation button is clicked.
        The emitted integer identifies the selected destination.

    @examples
    >>> sidebar = Sidebar()
    >>> sidebar.navigation_changed.connect(handle_navigation)
    """

    navigation_changed = pyqtSignal(int)

    NAVIGATION: list[tuple[str, str]] = [
        ("▦", "Dashboard"),
        ("✉", "Message Simulator"),
        ("⬡", "Security Validation"),
        ("▤", "Audit Viewer"),
        ("▷", "Test Execution"),
        ("⚙", "Configuration"),
    ]

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        """
        @summary
        Initialize the navigation sidebar and its visual components.

        @parameters
        parent : QWidget | None
            Optional parent widget in the Qt object hierarchy.

        @returns
        None
        """
        super().__init__(parent)

        self.setObjectName("sidebar")
        self.setFixedWidth(245)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 24, 16, 20)
        layout.setSpacing(8)

        logo = QLabel("SMG")
        logo.setObjectName("logo")

        subtitle = QLabel("SECURE GATEWAY")
        subtitle.setObjectName("logoSubtitle")

        layout.addWidget(logo)
        layout.addWidget(subtitle)
        layout.addSpacing(35)

        section = QLabel("WORKSPACE")
        section.setObjectName("sectionLabel")
        layout.addWidget(section)

        self.buttons: list[QPushButton] = []

        for index, (icon, name) in enumerate(self.NAVIGATION):
            button = QPushButton(f"  {icon}     {name}")
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setMinimumHeight(46)

            # Emit navigation requests instead of managing pages internally.
            button.clicked.connect(
                lambda checked, i=index:
                    self.navigation_changed.emit(i)
            )

            layout.addWidget(button)
            self.buttons.append(button)

        layout.addStretch()

        footer = QLabel(
            "SECURE MESSAGE GATEWAY\nVersion 1.0.0"
        )
        footer.setObjectName("sidebarFooter")
        layout.addWidget(footer)

        self.set_active(0)

    def set_active(self, index: int) -> None:
        """
        @summary
        Update the visual selection of the active navigation button.

        The method synchronizes the checked state of all navigation
        buttons with the selected page index.

        @parameters
        index : int
            Zero-based index of the active navigation destination.

        @returns
        None

        @notes
        Page index validation is handled by MainWindow before this
        method is called.
        """
        for i, button in enumerate(self.buttons):
            button.setChecked(i == index)
