
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt


class StatCard(QFrame):
    def __init__(
        self,
        title: str,
        value: str = "N/A",
        subtitle: str = "Waiting for gateway data",
        accent: str = "#8B5CF6",
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName("statCard")
        self.setMinimumHeight(145)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(9)

        self.accent_bar = QFrame()
        self.accent_bar.setFixedSize(34, 4)
        self.accent_bar.setStyleSheet(
            f"background-color: {accent}; border-radius: 2px;"
        )

        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("cardValue")

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("cardSubtitle")
        self.subtitle_label.setWordWrap(True)

        layout.addWidget(self.accent_bar)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.subtitle_label)
        layout.addStretch()

    def set_value(self, value: str, subtitle: str = ""):
        self.value_label.setText(value)

        if subtitle:
            self.subtitle_label.setText(subtitle)
