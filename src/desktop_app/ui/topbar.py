
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
)


class TopBar(QFrame):
    def __init__(self, parent=None):
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

    def set_title(self, title: str):
        self.title.setText(title)

    def set_status(self, status: str):
        self.status.setText(status)
