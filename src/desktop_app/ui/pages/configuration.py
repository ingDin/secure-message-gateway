
"""
Configuration page.

Provides a graphical interface for viewing, editing and saving
the Secure Message Gateway configuration.

Configuration is loaded from config/config.json and saved back
to the same file.
"""

import json
from pathlib import Path
from typing import Any

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QFrame,
    QScrollArea,
    QMessageBox,
)


class ConfigurationPage(QWidget):
    """Page for managing gateway configuration."""

    FIXED_CRYPTO_ALGORITHM = "HMAC"
    FIXED_HMAC_ALGORITHM = "SHA256"
    FIXED_ALLOWED_ALGORITHMS = ["SHA256"]
    FIXED_MIN_KEY_LENGTH = 32

    def __init__(self, parent=None):
        super().__init__(parent)

        self.project_root = self._find_project_root()
        self.config_path = self.project_root / "config" / "config.json"

        self.config: dict[str, Any] = {}

        self._build_ui()
        self.load_configuration()

    def _find_project_root(self) -> Path:
        """Locate the project root."""

        current_file = Path(__file__).resolve()

        # pages -> ui -> desktop_app -> src -> project
        return current_file.parents[4]

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 28)
        main_layout.setSpacing(18)

        title = QLabel("Configuration")
        title.setStyleSheet("""
            QLabel {
                color: #F8FAFC;
                background: transparent;
                font-size: 24px;
                font-weight: 700;
                border: none;
            }
        """)

        subtitle = QLabel(
            "Manage Secure Message Gateway application settings."
        )
        subtitle.setStyleSheet("""
            QLabel {
                color: #94A3B8;
                background: transparent;
                font-size: 13px;
                border: none;
            }
        """)

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #1E293B;
                width: 8px;
                margin: 0;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #475569;
                min-height: 25px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        scroll_content = QWidget()
        self.sections_layout = QVBoxLayout(scroll_content)
        self.sections_layout.setContentsMargins(0, 8, 8, 8)
        self.sections_layout.setSpacing(16)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, 1)

        # General Settings
        self.general_section = self._create_section(
            "General Settings"
        )

        self.version_input = QLineEdit()

        self.environment_input = QComboBox()
        self.environment_input.addItems([
            "dev",
            "test",
            "staging",
            "production",
        ])

        self._add_field(
            self.general_section,
            "Version",
            self.version_input,
        )

        self._add_field(
            self.general_section,
            "Environment",
            self.environment_input,
        )

        # Cryptography Settings
        self.crypto_section = self._create_section(
            "Cryptography Settings"
        )

        self.crypto_algorithm = QLineEdit()
        self.crypto_algorithm.setReadOnly(True)

        self.keys_file = QLineEdit()
        self.keys_archive = QLineEdit()

        self.hmac_algorithm = QComboBox()
        self.hmac_algorithm.addItem("SHA256")
        self.hmac_algorithm.setEnabled(False)

        self.allowed_algorithms = QLineEdit()
        self.allowed_algorithms.setReadOnly(True)

        self.min_key_length = self._create_spinbox(32, 32)
        self.min_key_length.setEnabled(False)

        self.rotation_required = QCheckBox()
        self.rotation_interval_days = self._create_spinbox(1, 3650)

        self._add_field(
            self.crypto_section,
            "Algorithm",
            self.crypto_algorithm,
        )

        self._add_field(
            self.crypto_section,
            "Keys File",
            self.keys_file,
        )

        self._add_field(
            self.crypto_section,
            "Keys Archive",
            self.keys_archive,
        )

        self._add_field(
            self.crypto_section,
            "HMAC Algorithm",
            self.hmac_algorithm,
        )

        self._add_field(
            self.crypto_section,
            "Allowed Algorithms",
            self.allowed_algorithms,
        )

        self._add_field(
            self.crypto_section,
            "Minimum Key Length (bytes)",
            self.min_key_length,
        )

        self._add_field(
            self.crypto_section,
            "Rotation Required",
            self.rotation_required,
        )

        self._add_field(
            self.crypto_section,
            "Rotation Interval (days)",
            self.rotation_interval_days,
        )

        # Freshness Settings
        self.freshness_section = self._create_section(
            "Freshness Settings"
        )

        self.counter_file = QLineEdit()
        self.initial_counter = self._create_spinbox(0, 2147483647)
        self.reset_on_start = QCheckBox()
        self.min_increment = self._create_spinbox(0, 2147483647)
        self.max_increment = self._create_spinbox(0, 2147483647)
        self.max_drift = self._create_spinbox(0, 2147483647)
        self.reject_out_of_range = QCheckBox()

        self._add_field(
            self.freshness_section,
            "Counter File",
            self.counter_file,
        )

        self._add_field(
            self.freshness_section,
            "Initial Counter",
            self.initial_counter,
        )

        self._add_field(
            self.freshness_section,
            "Reset On Start",
            self.reset_on_start,
        )

        self._add_field(
            self.freshness_section,
            "Minimum Increment",
            self.min_increment,
        )

        self._add_field(
            self.freshness_section,
            "Maximum Increment",
            self.max_increment,
        )

        self._add_field(
            self.freshness_section,
            "Maximum Drift",
            self.max_drift,
        )

        self._add_field(
            self.freshness_section,
            "Reject Out Of Range",
            self.reject_out_of_range,
        )

        # Logging Settings
        self.logging_section = self._create_section(
            "Logging Settings"
        )

        self.logging_path = QLineEdit()

        self._add_field(
            self.logging_section,
            "Log File Path",
            self.logging_path,
        )

        # Audit Settings
        self.audit_section = self._create_section(
            "Audit Settings"
        )

        self.audit_enabled = QCheckBox()
        self.audit_path = QLineEdit()

        self._add_field(
            self.audit_section,
            "Audit Enabled",
            self.audit_enabled,
        )

        self._add_field(
            self.audit_section,
            "Audit File Path",
            self.audit_path,
        )

        # Action Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.reload_button = QPushButton("Reload")
        self.reload_button.setStyleSheet(
            self._button_style("#334155")
        )
        self.reload_button.clicked.connect(
            self.load_configuration
        )

        self.save_button = QPushButton("Save Configuration")
        self.save_button.setStyleSheet(
            self._button_style("#2563EB")
        )
        self.save_button.clicked.connect(
            self.save_configuration
        )

        buttons_layout.addWidget(self.reload_button)
        buttons_layout.addWidget(self.save_button)

        main_layout.addLayout(buttons_layout)

        self.status_label = QLabel("Configuration not loaded")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #94A3B8;
                background: transparent;
                font-size: 12px;
                border: none;
            }
        """)

        main_layout.addWidget(self.status_label)

    def _create_section(self, title: str) -> QFrame:
        """Create a styled configuration section."""

        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 10px;
            }
        """)

        layout = QVBoxLayout(section)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        section_title = QLabel(title)
        section_title.setStyleSheet("""
            QLabel {
                color: #F8FAFC;
                background: transparent;
                font-size: 16px;
                font-weight: 600;
                border: none;
            }
        """)

        layout.addWidget(section_title)

        form_layout = QFormLayout()
        form_layout.setHorizontalSpacing(24)
        form_layout.setVerticalSpacing(12)

        layout.addLayout(form_layout)

        self.sections_layout.addWidget(section)

        section.form_layout = form_layout

        return section

    def _add_field(
        self,
        section: QFrame,
        label_text: str,
        widget: QWidget,
    ):
        """Add a labeled field to a section."""

        label = QLabel(label_text)
        label.setStyleSheet("""
            QLabel {
                color: #CBD5E1;
                background: transparent;
                font-size: 13px;
                border: none;
            }
        """)

        widget.setStyleSheet(self._field_style())

        section.form_layout.addRow(label, widget)

    def _create_spinbox(
        self,
        minimum: int,
        maximum: int,
    ) -> QSpinBox:
        """Create a styled integer input."""

        spinbox = QSpinBox()
        spinbox.setRange(minimum, maximum)

        return spinbox

    def _field_style(self) -> str:
        """Return the style used by configuration inputs."""

        return """
            QLineEdit,
            QSpinBox,
            QComboBox {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 7px 9px;
                font-size: 13px;
                min-height: 20px;
            }

            QLineEdit:focus,
            QSpinBox:focus,
            QComboBox:focus {
                border: 1px solid #3B82F6;
            }

            QLineEdit:read-only,
            QSpinBox:disabled,
            QComboBox:disabled {
                background-color: #1E293B;
                color: #94A3B8;
                border: 1px solid #334155;
            }

            QCheckBox {
                color: #E2E8F0;
                spacing: 8px;
                background: transparent;
            }

            QCheckBox::indicator {
                width: 17px;
                height: 17px;
            }

            QCheckBox:disabled {
                color: #94A3B8;
            }
        """

    def _button_style(self, background: str) -> str:
        """Return a styled button stylesheet."""

        return f"""
            QPushButton {{
                background-color: {background};
                color: #FFFFFF;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 9px 16px;
                font-size: 13px;
                font-weight: 600;
            }}

            QPushButton:hover {{
                background-color: #1D4ED8;
            }}

            QPushButton:disabled {{
                background-color: #475569;
                color: #CBD5E1;
            }}
        """

    def load_configuration(self):
        """Load configuration values from config.json."""

        try:
            with self.config_path.open(
                "r",
                encoding="utf-8",
            ) as config_file:
                loaded_config = json.load(config_file)

            if not isinstance(loaded_config, dict):
                raise ValueError(
                    "Configuration root must be a JSON object."
                )

            self.config = loaded_config
            self._populate_fields()

            self.status_label.setText(
                f"Loaded configuration: {self.config_path}"
            )

        except FileNotFoundError:
            self.status_label.setText(
                "Configuration file not found."
            )
            QMessageBox.critical(
                self,
                "Configuration Error",
                f"File not found:\n{self.config_path}",
            )

        except (json.JSONDecodeError, ValueError) as exc:
            self.status_label.setText(
                "Invalid configuration."
            )
            QMessageBox.critical(
                self,
                "Configuration Error",
                str(exc),
            )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Configuration Error",
                str(exc),
            )

    def _populate_fields(self):
        """Populate all inputs using the loaded configuration."""

        crypto = self.config.get("crypto", {})
        freshness = self.config.get("freshness", {})
        logging = self.config.get("logging", {})
        audit = self.config.get("audit", {})

        self.version_input.setText(
            str(self.config.get("version", ""))
        )

        self.environment_input.setCurrentText(
            str(self.config.get("environment", "dev"))
        )

        # Fixed cryptographic settings.
        self.crypto_algorithm.setText(
            self.FIXED_CRYPTO_ALGORITHM
        )

        self.hmac_algorithm.setCurrentText(
            self.FIXED_HMAC_ALGORITHM
        )

        self.allowed_algorithms.setText(
            ", ".join(self.FIXED_ALLOWED_ALGORITHMS)
        )

        self.min_key_length.setValue(
            self.FIXED_MIN_KEY_LENGTH
        )

        self.keys_file.setText(
            str(crypto.get("keys_file", "config/keys.json"))
        )

        self.keys_archive.setText(
            str(crypto.get(
                "keys_archive",
                "config/keys_archive.json",
            ))
        )

        self.rotation_required.setChecked(
            bool(crypto.get("rotation_required", True))
        )

        self.rotation_interval_days.setValue(
            int(crypto.get("rotation_interval_days", 30))
        )

        self.counter_file.setText(
            str(freshness.get(
                "counter_file",
                "config/freshness.json",
            ))
        )

        self.initial_counter.setValue(
            int(freshness.get("initial_counter", 0))
        )

        self.reset_on_start.setChecked(
            bool(freshness.get("reset_on_start", False))
        )

        self.min_increment.setValue(
            int(freshness.get("min_increment", 1))
        )

        self.max_increment.setValue(
            int(freshness.get("max_increment", 5))
        )

        self.max_drift.setValue(
            int(freshness.get("max_drift", 10))
        )

        self.reject_out_of_range.setChecked(
            bool(freshness.get("reject_out_of_range", True))
        )

        self.logging_path.setText(
            str(logging.get("path", "logs/gateway.log"))
        )

        self.audit_enabled.setChecked(
            bool(audit.get("enabled", True))
        )

        self.audit_path.setText(
            str(audit.get("path", "logs/audit.log"))
        )

    def _collect_configuration(self) -> dict[str, Any]:
        """Collect edited values while preserving other JSON fields."""

        updated_config = json.loads(
            json.dumps(self.config)
        )

        updated_config["version"] = (
            self.version_input.text().strip()
        )

        updated_config["environment"] = (
            self.environment_input.currentText()
        )

        crypto = updated_config.setdefault("crypto", {})

        # Keep cryptographic options fixed to implemented features.
        crypto["algorithm"] = self.FIXED_CRYPTO_ALGORITHM
        crypto["hmac_algorithm"] = self.FIXED_HMAC_ALGORITHM
        crypto["allowed_algorithms"] = (
            self.FIXED_ALLOWED_ALGORITHMS.copy()
        )
        crypto["min_key_length"] = self.FIXED_MIN_KEY_LENGTH

        # These paths and rotation settings remain configurable.
        crypto["keys_file"] = self.keys_file.text().strip()
        crypto["keys_archive"] = self.keys_archive.text().strip()

        crypto["rotation_required"] = (
            self.rotation_required.isChecked()
        )

        crypto["rotation_interval_days"] = (
            self.rotation_interval_days.value()
        )

        freshness = updated_config.setdefault("freshness", {})

        freshness["counter_file"] = (
            self.counter_file.text().strip()
        )

        freshness["initial_counter"] = (
            self.initial_counter.value()
        )

        freshness["reset_on_start"] = (
            self.reset_on_start.isChecked()
        )

        freshness["min_increment"] = (
            self.min_increment.value()
        )

        freshness["max_increment"] = (
            self.max_increment.value()
        )

        freshness["max_drift"] = (
            self.max_drift.value()
        )

        freshness["reject_out_of_range"] = (
            self.reject_out_of_range.isChecked()
        )

        logging = updated_config.setdefault("logging", {})
        logging["path"] = self.logging_path.text().strip()

        audit = updated_config.setdefault("audit", {})
        audit["enabled"] = self.audit_enabled.isChecked()
        audit["path"] = self.audit_path.text().strip()

        return updated_config

    def save_configuration(self):
        """Validate and save edited configuration to config.json."""

        try:
            updated_config = self._collect_configuration()

            if not updated_config.get("version"):
                raise ValueError("Version cannot be empty.")

            if updated_config["crypto"]["algorithm"] != "HMAC":
                raise ValueError(
                    "Only HMAC is currently supported."
                )

            if updated_config["crypto"]["hmac_algorithm"] != "SHA256":
                raise ValueError(
                    "Only HMAC SHA256 is currently supported."
                )

            if updated_config["crypto"]["min_key_length"] != 32:
                raise ValueError(
                    "Minimum key length must remain 32 bytes."
                )

            if not updated_config["crypto"]["keys_file"]:
                raise ValueError("Keys file path cannot be empty.")

            if not updated_config["crypto"]["keys_archive"]:
                raise ValueError("Keys archive path cannot be empty.")

            if not updated_config["freshness"]["counter_file"]:
                raise ValueError("Counter file path cannot be empty.")

            if not updated_config["logging"]["path"]:
                raise ValueError("Logging path cannot be empty.")

            if (
                not updated_config["audit"]["path"]
            ):
                raise ValueError("Audit file path cannot be empty.")

            if (
                updated_config["freshness"]["min_increment"]
                > updated_config["freshness"]["max_increment"]
            ):
                raise ValueError(
                    "Minimum increment cannot exceed maximum increment."
                )

            if (
                updated_config["crypto"]["rotation_interval_days"] < 1
            ):
                raise ValueError(
                    "Rotation interval must be at least 1 day."
                )

            serialized_config = json.dumps(
                updated_config,
                indent=2,
                ensure_ascii=False,
            )

            temporary_path = self.config_path.with_suffix(".tmp")

            temporary_path.write_text(
                serialized_config + "\n",
                encoding="utf-8",
            )

            temporary_path.replace(self.config_path)

            self.config = updated_config

            self.status_label.setText(
                "Configuration saved successfully."
            )

            QMessageBox.information(
                self,
                "Configuration Saved",
                "Configuration was saved successfully.",
            )

        except (ValueError, OSError, TypeError) as exc:
            QMessageBox.critical(
                self,
                "Save Error",
                str(exc),
            )
