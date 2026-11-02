
"""
@summary
Application entry point for the Secure Message Gateway desktop interface.

This module initializes the PyQt6 application, configures the application
metadata and centralized visual theme, and creates the main application
window.

The desktop application is responsible exclusively for presentation and
user interaction. Gateway business logic remains isolated in the
secure_gateway package.

@architecture
- QApplication manages the application event loop.
- MainWindow provides the primary application interface.
- QSS centralizes application-wide visual styling.
- Application startup is separated from gateway processing logic.

@notes
The application stylesheet is loaded from the desktop_app package.
No cryptographic material or sensitive gateway configuration is
loaded or exposed by this module.
"""

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from desktop_app.ui.main_window import MainWindow


def main() -> None:
    """
    @summary
    Initialize and execute the Secure Message Gateway desktop application.

    Creates the QApplication instance, configures application metadata,
    loads the centralized QSS stylesheet, initializes the main window,
    and starts the Qt event loop.

    @returns
    None

    @raises
    FileNotFoundError
        If the application stylesheet cannot be found.
    OSError
        If the stylesheet cannot be read.
    """
    app = QApplication(sys.argv)

    app.setApplicationName("Secure Message Gateway")

    # Resolve the project root independently of the current working directory.
    project_root = Path(__file__).resolve().parents[2]

    stylesheet_path = (
        project_root
        / "src"
        / "desktop_app"
        / "styles"
        / "dark_theme.qss"
    )

    stylesheet = stylesheet_path.read_text(
        encoding="utf-8"
    )

    app.setStyleSheet(stylesheet)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
