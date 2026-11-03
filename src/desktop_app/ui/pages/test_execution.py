"""
Test Execution page.

@summary
Runs the project's automated pytest suite in a background thread
and displays execution statistics and individual test results.

@architecture
TestExecutionWorker runs pytest and collects structured results
through a temporary pytest plugin. The worker emits the complete
result collection to TestExecutionPage, which creates result rows
on the GUI thread.

@notes
The interface is updated exclusively from the GUI thread.
Console output is intentionally disabled.
The results list has a constrained height and independent scrollbars.
"""

import json
import os
import subprocess
import sys
import tempfile
import time

from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QGridLayout,
    QScrollArea,
    QSizePolicy,
)


class TestExecutionWorker(QThread):
    __test__ = False
    """Run pytest and collect individual test outcomes."""

    results_ready = pyqtSignal(list)
    execution_finished = pyqtSignal(int, float)
    execution_error = pyqtSignal(str)

    def __init__(self, project_root: Path, parent=None):
        super().__init__(parent)
        self.project_root = project_root

    @staticmethod
    def _get_plugin_source() -> str:
        """Return the source code for the temporary pytest plugin."""
        return r"""
import json
import os

_gateway_config = None


def pytest_configure(config):
    global _gateway_config
    _gateway_config = config
    config._gateway_items = []
    config._gateway_results = {}


def pytest_collection_finish(session):
    session.config._gateway_items = list(session.items)


def pytest_runtest_logreport(report):
    if _gateway_config is None:
        return

    results = _gateway_config._gateway_results
    node_id = report.nodeid

    if report.failed:
        results[node_id] = "FAIL"
    elif report.skipped:
        if results.get(node_id) != "FAIL":
            results[node_id] = "SKIPPED"
    elif report.when == "call":
        if results.get(node_id) != "FAIL":
            results[node_id] = "PASS"


def pytest_sessionfinish(session, exitstatus):
    output_path = os.environ.get("GATEWAY_TEST_RESULTS")
    if not output_path:
        return

    items = getattr(session.config, "_gateway_items", [])
    results = getattr(session.config, "_gateway_results", {})
    records = []

    for item in items:
        node_id = item.nodeid
        records.append({
            "node_id": node_id,
            "status": results.get(node_id, "SKIPPED"),
        })

    with open(output_path, "w", encoding="utf-8") as output_file:
        json.dump(records, output_file, ensure_ascii=False)
"""

    def run(self):
        """Execute pytest and emit the collected test results."""
        start_time = time.perf_counter()

        try:
            tests_directory = self.project_root / "tests"
            if not tests_directory.is_dir():
                raise FileNotFoundError(
                    f"Tests directory not found: {tests_directory}"
                )

            with tempfile.TemporaryDirectory(
                prefix="gateway_tests_"
            ) as temporary_directory:
                temporary_path = Path(temporary_directory)
                plugin_path = temporary_path / "gateway_pytest_plugin.py"
                results_path = temporary_path / "test_results.json"

                plugin_path.write_text(
                    self._get_plugin_source(),
                    encoding="utf-8",
                )

                environment = os.environ.copy()
                python_paths = [
                    str(temporary_path),
                    str(self.project_root / "src"),
                ]

                existing_pythonpath = environment.get("PYTHONPATH")
                if existing_pythonpath:
                    python_paths.append(existing_pythonpath)

                environment["PYTHONPATH"] = os.pathsep.join(python_paths)
                environment["GATEWAY_TEST_RESULTS"] = str(results_path)

                command = [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "gateway_pytest_plugin",
                    "tests",
                ]

                process = subprocess.run(
                    command,
                    cwd=str(self.project_root),
                    env=environment,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                test_results = []
                if results_path.exists():
                    with results_path.open("r", encoding="utf-8") as result_file:
                        test_results = json.load(result_file)

                self.results_ready.emit(test_results)
                duration = time.perf_counter() - start_time
                self.execution_finished.emit(process.returncode, duration)

        except Exception as exc:
            self.execution_error.emit(str(exc))


class TestStatCard(QFrame):
    __test__ = False
    """Display one test execution statistic."""

    def __init__(
        self,
        title: str,
        value: str = "0",
        accent_color: str = "#60A5FA",
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("testStatCard")
        self.setMinimumHeight(104)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.setStyleSheet("""
            QFrame#testStatCard {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {accent_color};
                background: transparent;
                border: none;
                font-size: 12px;
                font-weight: 600;
            }}
        """)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("""
            QLabel {
                color: #F8FAFC;
                background: transparent;
                border: none;
                font-size: 27px;
                font-weight: 700;
            }
        """)

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: str):
        """Update the statistic value."""
        self.value_label.setText(value)


class TestResultCard(QFrame):
    """Display the test name and its parameter details on separate lines."""

    __test__ = False

    STATUS_COLORS = {
        "PASS": ("#14532D", "#86EFAC"),
        "FAIL": ("#7F1D1D", "#FCA5A5"),
        "SKIPPED": ("#713F12", "#FDE68A"),
    }

    def __init__(
        self,
        sequence: int,
        test_name: str,
        status: str,
        parameter_text: str = "",
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName("testResultCard")
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )
        self.setStyleSheet("""
            QFrame#testResultCard {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(6)

        sequence_label = QLabel(f"{sequence:02d}")
        sequence_label.setFixedWidth(30)
        sequence_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        sequence_label.setStyleSheet("""
            QLabel {
                color: #94A3B8;
                background: transparent;
                border: none;
                font-size: 11px;
                font-weight: 600;
            }
        """)

        details_layout = QVBoxLayout()
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(2)

        name_label = QLabel(test_name)
        name_label.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Preferred,
        )
        name_label.setStyleSheet("""
            QLabel {
                color: #F8FAFC;
                background: transparent;
                border: none;
                font-size: 12px;
                font-weight: 700;
            }
        """)
        details_layout.addWidget(name_label)

        if parameter_text:
            parameter_label = QLabel(f"({parameter_text})")
            parameter_label.setSizePolicy(
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Preferred,
            )
            parameter_label.setToolTip(parameter_text)
            parameter_label.setStyleSheet("""
                QLabel {
                    color: #94A3B8;
                    background: transparent;
                    border: none;
                    font-size: 10px;
                    font-weight: 400;
                }
            """)
            details_layout.addWidget(parameter_label)

        status_label = QLabel(status)
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_label.setFixedWidth(78)
        status_label.setContentsMargins(6, 5, 6, 5)

        background, foreground = self.STATUS_COLORS.get(
            status,
            ("#334155", "#E2E8F0"),
        )
        status_label.setStyleSheet(f"""
            QLabel {{
                color: {foreground};
                background-color: {background};
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 700;
            }}
        """)

        layout.addWidget(sequence_label)
        layout.addLayout(details_layout)
        layout.addStretch(1)
        layout.addWidget(status_label, 0, Qt.AlignmentFlag.AlignVCenter)

        # Preserve the full parameter identifier; the scroll area handles
        # horizontal overflow when a parameter string is especially long.
        self.setMinimumWidth(layout.sizeHint().width())


class TestExecutionPage(QWidget):
    __test__ = False
    """Main page for automated test execution."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_root = self._find_project_root()
        self.worker = None

        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        self.result_cards = []

        self._build_ui()

    def _find_project_root(self) -> Path:
        """Locate the repository root."""
        current_file = Path(__file__).resolve()
        return current_file.parents[4]

    def _build_ui(self):
        """Build the Test Execution page."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 24, 32, 16)
        main_layout.setSpacing(16)

        summary_title = QLabel("Execution Summary")
        summary_title.setStyleSheet("""
            QLabel {
                color: #F8FAFC;
                background: transparent;
                border: none;
                font-size: 17px;
                font-weight: 700;
            }
        """)
        main_layout.addWidget(summary_title)

        stats_layout = QGridLayout()
        stats_layout.setSpacing(14)

        self.total_card = TestStatCard("Total Tests", accent_color="#93C5FD")
        self.passed_card = TestStatCard("Passed", accent_color="#86EFAC")
        self.failed_card = TestStatCard("Failed", accent_color="#FCA5A5")
        self.skipped_card = TestStatCard("Skipped", accent_color="#FDE68A")

        stats_layout.addWidget(self.total_card, 0, 0)
        stats_layout.addWidget(self.passed_card, 0, 1)
        stats_layout.addWidget(self.failed_card, 0, 2)
        stats_layout.addWidget(self.skipped_card, 0, 3)
        main_layout.addLayout(stats_layout)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)

        self.run_button = QPushButton("Run Tests")
        self.run_button.setObjectName("primaryButton")
        self.run_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.run_button.clicked.connect(self.run_tests)

        self.status_label = QLabel("Not started")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #CBD5E1;
                background: transparent;
                border: none;
                font-size: 12px;
                font-weight: 600;
            }
        """)

        controls_layout.addWidget(self.run_button)
        controls_layout.addWidget(self.status_label)
        controls_layout.addStretch()
        main_layout.addLayout(controls_layout)

        results_header = QHBoxLayout()

        results_title = QLabel("Individual Test Results")
        results_title.setStyleSheet("""
            QLabel {
                color: #F8FAFC;
                background: transparent;
                border: none;
                font-size: 17px;
                font-weight: 700;
            }
        """)

        self.results_count_label = QLabel("0 tests")
        self.results_count_label.setStyleSheet("""
            QLabel {
                color: #CBD5E1;
                background: transparent;
                border: none;
                font-size: 12px;
            }
        """)

        results_header.addWidget(results_title)
        results_header.addStretch()
        results_header.addWidget(self.results_count_label)
        main_layout.addLayout(results_header)

        # Keep the results area compact and allow scrolling in both directions.
        self.results_scroll = QScrollArea()
        self.results_scroll.setObjectName("testResultsScroll")
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.results_scroll.setMinimumHeight(180)
        self.results_scroll.setMaximumHeight(340)
        self.results_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.results_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.results_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #111827;
                width: 10px;
                border-radius: 5px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: #475569;
                min-height: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #64748B;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background: #111827;
                height: 10px;
                border-radius: 5px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal {
                background: #475569;
                min-width: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #64748B;
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)

        self.results_container = QWidget()
        self.results_container.setObjectName("testResultsContainer")
        self.results_container.setStyleSheet("background: transparent;")

        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(2, 4, 8, 4)
        self.results_layout.setSpacing(8)

        self.empty_results_label = QLabel(
            "No test results yet. Select Run Tests to begin."
        )
        self.empty_results_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_results_label.setStyleSheet("""
            QLabel {
                color: #CBD5E1;
                background: transparent;
                border: none;
                padding: 24px;
                font-size: 12px;
            }
        """)

        self.results_layout.addWidget(self.empty_results_label)
        self.results_layout.addStretch(1)
        self.results_scroll.setWidget(self.results_container)
        main_layout.addWidget(self.results_scroll, 1)

        self.bottom_bar = QFrame()
        self.bottom_bar.setObjectName("testExecutionBottomBar")
        self.bottom_bar.setFixedHeight(34)
        self.bottom_bar.setStyleSheet("""
            QFrame#testExecutionBottomBar {
                background-color: #111C30;
                border: 1px solid #25334A;
                border-radius: 6px;
            }
        """)

        bottom_layout = QHBoxLayout(self.bottom_bar)
        bottom_layout.setContentsMargins(12, 4, 12, 4)

        self.bottom_status_label = QLabel("Ready")
        self.bottom_status_label.setStyleSheet("""
            QLabel {
                color: #94A3B8;
                background: transparent;
                border: none;
                font-size: 11px;
            }
        """)
        bottom_layout.addWidget(self.bottom_status_label)
        bottom_layout.addStretch()

        self.bottom_count_label = QLabel("0 tests")
        self.bottom_count_label.setStyleSheet("""
            QLabel {
                color: #CBD5E1;
                background: transparent;
                border: none;
                font-size: 11px;
            }
        """)
        bottom_layout.addWidget(self.bottom_count_label)
        main_layout.addWidget(self.bottom_bar)

    def run_tests(self):
        """Start pytest execution."""
        if self.worker is not None and self.worker.isRunning():
            return

        tests_directory = self.project_root / "tests"
        if not tests_directory.is_dir():
            message = f"Tests directory not found: {tests_directory}"
            self.status_label.setText(message)
            self.bottom_status_label.setText(message)
            return

        self._reset_results()
        self._reset_statistics()

        self.status_label.setText("Running tests...")
        self.bottom_status_label.setText("Test execution in progress...")
        self.run_button.setEnabled(False)

        self.worker = TestExecutionWorker(self.project_root, self)
        self.worker.results_ready.connect(self._handle_results)
        self.worker.execution_finished.connect(self._handle_finished)
        self.worker.execution_error.connect(self._handle_error)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()

    def _handle_results(self, results: list):
        """Create result rows and update the summary."""
        self._reset_results()

        for sequence, result in enumerate(results, start=1):
            node_id = result.get("node_id", "")
            status = result.get("status", "SKIPPED")
            if not node_id:
                continue

            # Separate the parametrized test name from its parameter details.
            test_identifier = node_id.split("::")[-1]
            if "[" in test_identifier and test_identifier.endswith("]"):
                test_name, parameter_text = test_identifier.split("[", 1)
                parameter_text = parameter_text[:-1]
            else:
                test_name = test_identifier
                parameter_text = ""

            card = TestResultCard(
                sequence=sequence,
                test_name=test_name,
                status=status,
                parameter_text=parameter_text,
                parent=self.results_container,
            )
            self.results_layout.insertWidget(
                self.results_layout.count() - 1,
                card,
            )
            self.result_cards.append(card)

            if status == "PASS":
                self.passed_tests += 1
            elif status == "FAIL":
                self.failed_tests += 1
            elif status == "SKIPPED":
                self.skipped_tests += 1

        self.total_tests = len(self.result_cards)
        self.empty_results_label.setVisible(self.total_tests == 0)

        self.results_count_label.setText(f"{self.total_tests} tests")
        self.bottom_count_label.setText(f"{self.total_tests} tests")

        # Force the scrollable child to accommodate its widest result row.
        widest_row = max(
            (card.minimumWidth() for card in self.result_cards),
            default=0,
        )
        self.results_container.setMinimumWidth(
            max(self.results_scroll.viewport().width(), widest_row + 12)
        )

        self._update_statistics()

    def _handle_finished(self, return_code: int, duration: float):
        """Update execution status after pytest finishes."""
        if return_code == 0:
            message = f"Completed successfully • {duration:.2f}s"
            color = "#86EFAC"
        elif return_code == 1:
            message = f"Completed with test failures • {duration:.2f}s"
            color = "#FCA5A5"
        elif return_code == 5:
            message = "No tests collected"
            color = "#FDE68A"
        else:
            message = f"Execution error ({return_code})"
            color = "#FCA5A5"

        self.status_label.setText(message)
        self.bottom_status_label.setText(message)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background: transparent;
                border: none;
                font-size: 12px;
                font-weight: 600;
            }}
        """)

    def _handle_error(self, error: str):
        """Display an execution error in both status areas."""
        message = f"Execution error: {error}"
        self.status_label.setText(message)
        self.bottom_status_label.setText(message)
        self.status_label.setToolTip(error)
        self.bottom_status_label.setToolTip(error)

    def _worker_finished(self):
        """Restore the Run Tests button."""
        self.run_button.setEnabled(True)
        self.worker = None

    def _reset_results(self):
        """Remove old result rows and restore the empty state."""
        for card in self.result_cards:
            self.results_layout.removeWidget(card)
            card.deleteLater()

        self.result_cards.clear()
        self.results_container.setMinimumWidth(0)
        self.empty_results_label.setVisible(True)
        self.results_count_label.setText("0 tests")
        self.bottom_count_label.setText("0 tests")

    def _reset_statistics(self):
        """Reset all test counters."""
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        self._update_statistics()

    def _update_statistics(self):
        """Refresh the execution statistics."""
        self.total_card.set_value(str(self.total_tests))
        self.passed_card.set_value(str(self.passed_tests))
        self.failed_card.set_value(str(self.failed_tests))
        self.skipped_card.set_value(str(self.skipped_tests))
