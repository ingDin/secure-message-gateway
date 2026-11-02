
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from desktop_app.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Secure Message Gateway")

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
