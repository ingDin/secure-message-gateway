
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QStackedWidget,
    QLabel,
)

from desktop_app.ui.sidebar import Sidebar
from desktop_app.ui.topbar import TopBar
from desktop_app.ui.pages.dashboard import DashboardPage


class PlaceholderPage(QWidget):

    def __init__(self, title, description):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 30, 32, 30)

        heading = QLabel(title)
        heading.setObjectName("pageTitle")

        subtitle = QLabel(description)
        subtitle.setObjectName("pageSubtitle")

        layout.addWidget(heading)
        layout.addWidget(subtitle)
        layout.addStretch()


class MainWindow(QMainWindow):

    PAGE_TITLES = [
        "Dashboard",
        "Message Simulator",
        "Security Validation",
        "Audit Viewer",
        "Test Execution",
        "Configuration",
    ]

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Secure Message Gateway")
        self.setMinimumSize(1200, 760)

        self.sidebar = Sidebar()
        self.topbar = TopBar()
        self.stack = QStackedWidget()

        self._create_pages()
        self._create_layout()

        self.sidebar.navigation_changed.connect(
            self.navigate
        )

        self.navigate(0)

    def _create_pages(self):
        self.dashboard = DashboardPage()

        self.stack.addWidget(self.dashboard)

        descriptions = [
            "Submit and validate secure JSON messages.",
            "Monitor HMAC, freshness and schema validation.",
            "Inspect structured gateway audit events.",
            "Execute automated tests and inspect results.",
            "Manage safe application configuration.",
        ]

        for title, description in zip(
            self.PAGE_TITLES[1:],
            descriptions,
        ):
            page = PlaceholderPage(title, description)
            self.stack.addWidget(page)

    def _create_layout(self):
        central = QWidget()
        central.setObjectName("centralWidget")

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        content = QWidget()

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        content_layout.addWidget(self.topbar)
        content_layout.addWidget(self.stack)

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(content, 1)

        self.setCentralWidget(central)

    def navigate(self, index: int):
        if not 0 <= index < self.stack.count():
            return

        self.stack.setCurrentIndex(index)
        self.sidebar.set_active(index)

        self.topbar.set_title(
            self.PAGE_TITLES[index]
        )
