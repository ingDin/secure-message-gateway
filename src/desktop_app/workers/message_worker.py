
"""
@summary
Background worker responsible for executing asynchronous gateway
message processing without blocking the desktop application's UI thread.

This module provides a Qt thread wrapper around the asynchronous
GatewayService interface.

@architecture
- MessageWorker inherits from QThread.
- The run() method executes in a separate operating system thread.
- asyncio.run() creates and manages an event loop in that thread.
- GatewayService performs the actual message processing.
- Qt signals communicate the processing result or an unexpected
  execution error back to the application.

@design
The worker isolates potentially time-consuming gateway operations
from the graphical interface.

The worker does not implement gateway security logic. It delegates
message processing to GatewayService and reports the outcome through
Qt signals.

@notes
Each worker instance is intended to process one message.
The UI should connect to the worker signals before calling start().
"""

import asyncio
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

from desktop_app.services.gateway_service import GatewayService
from secure_gateway.models import GatewayResponse


class MessageWorker(QThread):
    """
    @summary
    Executes one asynchronous gateway message-processing operation
    in a dedicated background thread.

    The worker communicates with the main application through
    Qt signals, avoiding direct UI updates from the background thread.

    @signals
    result_ready : pyqtSignal(object)
        Emitted when gateway processing returns a GatewayResponse.

    error_occurred : pyqtSignal(str)
        Emitted when an unexpected exception occurs during worker
        execution or gateway initialization.

    @parameters
    service : GatewayService
        Service instance responsible for gateway initialization
        and message processing.

    message : dict[str, Any]
        Message payload to be processed by the gateway.

    @examples
    >>> worker = MessageWorker(service, message)
    >>> worker.result_ready.connect(handle_result)
    >>> worker.error_occurred.connect(handle_error)
    >>> worker.start()
    """

    # Signals used to safely communicate results to the UI thread.
    result_ready = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        service: GatewayService,
        message: dict[str, Any],
    ) -> None:
        """
        @summary
        Initialize the worker with the gateway service and message payload.

        @parameters
        service : GatewayService
            Gateway service used to process the message.

        message : dict[str, Any]
            Message payload submitted for processing.

        @returns
        None
        """

        super().__init__()

        self.service = service

        # Keep a separate copy of the message dictionary so that
        # external changes to its top-level fields do not affect
        # the payload while it is being processed.
        self.message = message.copy()

    def run(self) -> None:
        """
        @summary
        Execute asynchronous gateway processing in the worker thread.

        QThread.start() invokes this method in a separate thread.
        asyncio.run() creates an event loop, executes the asynchronous
        service operation, and closes the event loop when processing
        finishes.

        @signals
        result_ready
            Emits the GatewayResponse returned by the gateway.

        error_occurred
            Emits a descriptive error message if an unexpected
            exception interrupts worker execution.

        @returns
        None
        """

        try:
            # Execute the asynchronous gateway operation in this
            # worker thread instead of blocking the UI thread.
            response: GatewayResponse = asyncio.run(
                self.service.process(self.message)
            )

            # Send the structured gateway response to connected
            # slots in the desktop application.
            self.result_ready.emit(response)

        except Exception as exc:
            # Report unexpected initialization or execution errors
            # without allowing the exception to escape the worker.
            self.error_occurred.emit(str(exc))
