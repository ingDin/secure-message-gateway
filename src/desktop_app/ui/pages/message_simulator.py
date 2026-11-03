"""
@summary

Message Simulator page for the Secure Message Gateway desktop
application.

This module provides a graphical interface for submitting JSON
messages to the gateway, generating authenticated test messages,
and displaying their processing results.

@architecture

- MessageSimulatorPage implements the message submission interface.
- GatewayService provides access to the existing gateway core.
- MessageWorker executes asynchronous processing in a background thread.
- Qt signals deliver processing results and errors to the UI thread.

@design

The page is responsible exclusively for user interaction and result
presentation. Gateway validation and cryptographic operations remain
the responsibility of the existing gateway core.

@notes

Messages must contain the fields required by the gateway schema.
Generated messages use the configured cryptographic key and the
counter stored by the freshness manager.
"""

import asyncio
import json
import time

from pathlib import Path
from typing import Any

from PyQt6.QtCore import pyqtSignal

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QFrame,
)

from desktop_app.services.gateway_service import GatewayService
from desktop_app.workers.message_worker import MessageWorker

from secure_gateway.models import GatewayResponse


class MessageSimulatorPage(QWidget):
    """
    @summary

    Provides an interface for submitting messages to the secure gateway.

    Users can enter a JSON message manually or generate a test message
    using the configured cryptographic key and freshness counter.

    @architecture

    1. Read or generate the JSON payload.
    2. Parse and validate the JSON document structure.
    3. Create a MessageWorker for background execution.
    4. Connect worker signals to the corresponding UI handlers.
    5. Display the gateway response or execution error.

    @parameters

    parent : QWidget | None
        Optional parent widget in the Qt object hierarchy.

    @examples

    >>> page = MessageSimulatorPage()
    """

    validation_status_changed = pyqtSignal(str, str, str)

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        """
        @summary

        Initialize the message simulator interface.

        Creates the message editor, processing controls, result area,
        and gateway service instance.

        @parameters

        parent : QWidget | None
            Optional parent widget.

        @returns

        None
        """

        super().__init__(parent)

        self.setObjectName("page")

        # Reuse one service instance for message generation
        # and message-processing requests.
        self.service = GatewayService()

        # Keep a reference to the active worker to prevent premature
        # garbage collection while its thread is running.
        self.worker: MessageWorker | None = None

        self._create_layout()

    def _create_layout(self) -> None:
        """
        @summary

        Construct the message simulator page layout.

        Creates the page heading, JSON input editor, message generation
        and processing controls, and read-only result display.

        @returns

        None
        """

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 26, 30, 30)
        main_layout.setSpacing(20)

        # Page heading and description.
        heading = QLabel("Message Simulator")
        heading.setObjectName("pageTitle")

        description = QLabel(
            "Submit JSON messages and inspect gateway processing results."
        )
        description.setObjectName("pageSubtitle")

        main_layout.addWidget(heading)
        main_layout.addWidget(description)

        # Message input section.
        input_frame = QFrame()
        input_frame.setObjectName("contentCard")

        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(22, 20, 22, 20)
        input_layout.setSpacing(12)

        input_title = QLabel("Message Payload")
        input_title.setObjectName("cardHeading")

        input_description = QLabel(
            "Enter a JSON message containing id, counter, msg and hmac."
        )
        input_description.setObjectName("cardSubtitle")

        self.message_editor = QPlainTextEdit()
        self.message_editor.setObjectName("messageEditor")
        self.message_editor.setPlaceholderText(
            '{\n'
            '    "id": 1,\n'
            '    "counter": 1,\n'
            '    "msg": "Your message",\n'
            '    "hmac": "valid-hmac-value"\n'
            '}'
        )

        input_layout.addWidget(input_title)
        input_layout.addWidget(input_description)
        input_layout.addWidget(self.message_editor)

        main_layout.addWidget(input_frame, 2)

        # Message generation and processing controls.
        controls_layout = QHBoxLayout()

        self.generate_button = QPushButton("Generate Message")
        self.generate_button.setObjectName("secondaryButton")
        self.generate_button.clicked.connect(
            self.generate_message
        )

        self.process_button = QPushButton("Process Message")
        self.process_button.setObjectName("primaryButton")
        self.process_button.clicked.connect(
            self.process_message
        )

        controls_layout.addWidget(self.generate_button)
        controls_layout.addWidget(self.process_button)
        controls_layout.addStretch()

        main_layout.addLayout(controls_layout)

        # Gateway response section.
        result_frame = QFrame()
        result_frame.setObjectName("contentCard")

        result_layout = QVBoxLayout(result_frame)
        result_layout.setContentsMargins(22, 20, 22, 20)
        result_layout.setSpacing(12)

        result_title = QLabel("Processing Result")
        result_title.setObjectName("cardHeading")

        self.result_display = QPlainTextEdit()
        self.result_display.setObjectName("resultDisplay")
        self.result_display.setReadOnly(True)
        self.result_display.setPlaceholderText(
            "Gateway processing results will appear here."
        )

        result_layout.addWidget(result_title)
        result_layout.addWidget(self.result_display)

        main_layout.addWidget(result_frame, 1)

    async def _build_generated_message(self) -> dict[str, Any]:
        """
        @summary

        Generate a JSON message authenticated with the configured HMAC key.

        The method initializes the gateway, checks whether key rotation
        is required, loads the active key, reads the persisted freshness
        counter, and calculates the next valid counter value.

        @returns

        dict[str, Any]
            Generated message containing id, counter, msg and hmac.

        @raises

        RuntimeError
            If the gateway cannot be initialized.

        ValueError
            If the freshness counter cannot be initialized safely or
            the configured counter limits would be exceeded.
        """

        # Initialize the service. The initialize() method stores
        # the gateway instance internally.
        self.service.initialize()

        # Retrieve the initialized gateway instance.
        # initialize() does not necessarily return the instance.
        gateway = self.service._gateway

        if gateway is None:
            raise RuntimeError(
                "Gateway initialization failed. "
                "The gateway instance is unavailable."
            )

        # Apply any pending key rotation before loading the key.
        # This ensures that the generated HMAC uses the same key
        # that the gateway will use when processing the message.
        await gateway._check_key_rotation()

        config = gateway.config

        # Load the active cryptographic key.
        key = await gateway.algorithm.load_key_async(config)

        freshness_config = config["freshness"]

        counter_path = Path(
            freshness_config["counter_file"]
        )

        # Read the last persisted counter value.
        if counter_path.exists():
            with counter_path.open(
                "r",
                encoding="utf-8",
            ) as counter_file:
                counter_data = json.load(counter_file)

            current_counter = int(
                counter_data["counter"]
            )

        else:
            initial_counter = freshness_config.get(
                "initial_counter",
                "auto",
            )

            # The current FreshnessManager implementation cannot
            # safely generate the first automatic counter value:
            # bootstrap sets the counter to the incoming value,
            # which results in an increment of zero.
            if initial_counter == "auto":
                raise ValueError(
                    "The freshness counter file does not exist and "
                    "initial_counter is set to 'auto'. Initialize the "
                    "counter first or configure a numeric initial_counter."
                )

            current_counter = int(initial_counter)

        # Calculate the next counter value using the configured
        # minimum increment.
        increment = int(
            freshness_config.get("min_increment", 1)
        )

        if increment < 1:
            raise ValueError(
                "The configured min_increment must be greater than zero."
            )

        next_counter = current_counter + increment

        # Respect the optional maximum increment restriction.
        reject_out_of_range = freshness_config.get(
            "reject_out_of_range",
            False,
        )

        if reject_out_of_range:
            max_increment = freshness_config.get(
                "max_increment"
            )

            if (
                max_increment is not None
                and increment > int(max_increment)
            ):
                raise ValueError(
                    "The generated counter increment exceeds "
                    "the configured max_increment."
                )

        # Respect the maximum counter drift restriction.
        max_drift = freshness_config.get("max_drift")

        if (
            max_drift is not None
            and increment > int(max_drift)
        ):
            raise ValueError(
                "The generated counter increment exceeds "
                "the configured max_drift."
            )

        # Construct the message payload without the HMAC field.
        payload = {
            "id": int(time.time()) % 1_000_000,
            "counter": next_counter,
            "msg": (
                "Generated test message from "
                "Secure Message Gateway."
            ),
        }

        # Sign the canonical payload using the active gateway key.
        signature = gateway.algorithm.sign(
            payload,
            key,
        )

        # Return the complete message expected by the gateway schema.
        return {
            **payload,
            "hmac": signature,
        }

    def generate_message(self) -> None:
        """
        @summary

        Generate an authenticated test message and populate the editor.

        The generated message is not submitted automatically. The user
        can inspect or modify it before starting gateway processing.

        @returns

        None
        """

        if self.worker is not None:
            return

        self.generate_button.setEnabled(False)
        self.process_button.setEnabled(False)

        self.result_display.setPlainText(
            "Generating authenticated message..."
        )

        try:
            message = asyncio.run(
                self._build_generated_message()
            )

            self.message_editor.setPlainText(
                json.dumps(
                    message,
                    indent=4,
                    ensure_ascii=False,
                )
            )

            self.result_display.setPlainText(
                "Message generated successfully.\n"
                "Review the JSON payload and click "
                "'Process Message' to submit it to the gateway."
            )

        except Exception as exc:
            self.result_display.setPlainText(
                f"Message generation failed:\n{exc}"
            )

        finally:
            self.generate_button.setEnabled(True)
            self.process_button.setEnabled(True)

    def process_message(self) -> None:
        """
        @summary

        Parse the submitted JSON payload and start background processing.

        Creates a MessageWorker and connects its signals before starting
        the thread. The processing controls are disabled while the worker
        is active to prevent overlapping operations.

        @returns

        None

        @notes

        Invalid JSON documents and non-object JSON values are rejected
        before a worker is created.
        """

        # Prevent a second submission while processing is active.
        if self.worker is not None:
            return

        self._update_validation_status(
            "Not run",
            "Not run",
            "Not run",
        )

        raw_message = self.message_editor.toPlainText()

        try:
            message: Any = json.loads(raw_message)

        except json.JSONDecodeError as exc:
            self.result_display.setPlainText(
                f"Invalid JSON:\n{exc}"
            )
            return

        # The gateway expects a JSON object represented by a dictionary.
        if not isinstance(message, dict):
            self.result_display.setPlainText(
                "Invalid message: the JSON document must contain an object."
            )
            return

        # Create the worker and connect its signals before execution.
        self.worker = MessageWorker(
            self.service,
            message,
        )

        self.worker.result_ready.connect(
            self._handle_result
        )

        self.worker.error_occurred.connect(
            self._handle_error
        )

        self.worker.finished.connect(
            self._on_worker_finished
        )

        self.worker.finished.connect(
            self.worker.deleteLater
        )

        self.generate_button.setEnabled(False)
        self.process_button.setEnabled(False)

        self.result_display.setPlainText(
            "Processing message..."
        )

        # QThread.start() executes run() in the background thread.
        self.worker.start()

    def _update_validation_status(
        self,
        schema: str,
        hmac: str,
        freshness: str,
    ) -> None:
        """
        @summary

        Emit the results of the gateway security validation stages.

        @parameters

        schema : str
            JSON schema validation result.

        hmac : str
            HMAC verification result.

        freshness : str
            Freshness validation result.

        @returns

        None

        @notes

        The method communicates validation results through a Qt signal.
        It does not execute or modify gateway validation logic.
        """

        self.validation_status_changed.emit(
            schema,
            hmac,
            freshness,
        )

    def _handle_result(
        self,
        response: GatewayResponse,
    ) -> None:
        """
        @summary

        Display the gateway response and update security validation states.

        @parameters

        response : GatewayResponse
            Result returned by GatewayAsync through GatewayService.

        @returns

        None
        """

        status = str(response.status).lower()
        reason = str(response.reason or "").upper()

        # A successful response means all validation stages passed.
        if status == "ok":
            validation_states = (
                "Passed",
                "Passed",
                "Passed",
            )

        # Schema validation failed before the remaining checks.
        elif reason == "SCHEMA_FAIL":
            validation_states = (
                "Failed",
                "Not run",
                "Not run",
            )

        # Schema passed, but HMAC verification failed.
        elif reason == "HMAC_FAIL":
            validation_states = (
                "Passed",
                "Failed",
                "Not run",
            )

        # Schema and HMAC passed, but freshness validation failed.
        elif reason == "FRESHNESS_FAIL":
            validation_states = (
                "Passed",
                "Passed",
                "Failed",
            )

        # Unknown errors do not provide enough information to infer
        # the individual validation results.
        else:
            validation_states = (
                "Not run",
                "Not run",
                "Not run",
            )

        self._update_validation_status(
            *validation_states
        )

        result = [
            f"Status: {response.status}",
            f"Reason: {response.reason or 'None'}",
        ]

        self.result_display.setPlainText(
            "\n".join(result)
        )

    def _handle_error(self, error_message: str) -> None:
        """
        @summary

        Display an unexpected worker execution error.

        @parameters

        error_message : str
            Descriptive error message emitted by MessageWorker.

        @returns

        None
        """

        self._update_validation_status(
            "Not run",
            "Not run",
            "Not run",
        )

        self.result_display.setPlainText(
            f"Processing error:\n{error_message}"
        )

    def _on_worker_finished(self) -> None:
        """
        @summary

        Restore the processing controls after worker termination.

        Re-enables the generation and processing buttons and releases
        the active worker reference.

        @returns

        None
        """

        self.generate_button.setEnabled(True)
        self.process_button.setEnabled(True)

        self.worker = None