
from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)
from PyQt6.QtCore import pyqtSignal


class Sidebar(QFrame):
    navigation_changed = pyqtSignal(int)

    NAVIGATION = [
        ("▦", "Dashboard"),
        ("✉", "Message Simulator"),
        ("⬡", "Security Validation"),
        ("▤", "Audit Viewer"),
        ("▷", "Test Execution"),
        ("⚙", "Configuration"),
    ]

    def __init__(self, parent=None):
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

        self.buttons = []

        for index, (icon, name) in enumerate(self.NAVIGATION):
            button = QPushButton(f"  {icon}     {name}")
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setMinimumHeight(46)

            button.clicked.connect(
                lambda checked, i=index:
                    self.navigation_changed.emit(i)
            )

            layout.addWidget(button)
            self.buttons.append(button)

        layout.addStretch()

        footer = QLabel("SECURE MESSAGE GATEWAY\nVersion 1.0.0")
        footer.setObjectName("sidebarFooter")
        layout.addWidget(footer)

        self.set_active(0)

    def set_active(self, index: int):
        for i, button in enumerate(self.buttons):
            button.setChecked(i == index)
