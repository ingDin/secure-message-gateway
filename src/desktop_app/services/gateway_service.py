
"""
@summary
Gateway service adapter responsible for initializing and exposing
the existing asynchronous Secure Message Gateway to the desktop
application.

This module provides the integration boundary between the desktop
presentation layer and the gateway processing core.

The service handles:
- gateway configuration loading
- filesystem path resolution
- gateway instance initialization
- asynchronous message processing

@architecture
- GatewayService encapsulates the gateway initialization lifecycle.
- JSON configuration is loaded from the project configuration directory.
- Relative filesystem paths are resolved against the project root.
- GatewayAsync remains responsible for message validation,
  authentication, freshness enforcement, and audit logging.
- The service exposes a simplified interface to the desktop layer.

@design
The service separates gateway initialization and access from the
presentation layer. UI components should interact with this service
instead of constructing GatewayAsync directly.

@notes
This module does not implement background execution or Qt thread
management. Message processing must be delegated to an appropriate
background worker when integrated into the desktop interface.
"""

import json
from pathlib import Path
from typing import Any

from secure_gateway.gateway import GatewayAsync
from secure_gateway.models import GatewayResponse


class GatewayService:
    """
    @summary
    Provides a controlled interface between the desktop application
    and the asynchronous gateway processing core.

    GatewayService loads the application configuration, initializes
    the GatewayAsync instance, and exposes its message-processing
    functionality.

    @architecture
    1. Resolve the project root and configuration file location.
    2. Load and normalize filesystem paths from the configuration.
    3. Initialize the GatewayAsync processing engine.
    4. Delegate incoming messages to the gateway.

    @parameters
    config_path : str | Path | None
        Optional path to the gateway JSON configuration file.
        Defaults to config/config.json in the project root.

    project_root : str | Path | None
        Optional project root directory.
        Defaults to the project root inferred from this module location.

    @examples
    >>> service = GatewayService()
    >>> service.initialize()
    >>> response = await service.process(message)
    """

    # Configuration entries that represent filesystem paths.
    PATH_SETTINGS = (
        ("crypto", "keys_file"),
        ("crypto", "keys_archive"),
        ("freshness", "counter_file"),
        ("audit", "path"),
        ("logging", "path"),
    )

    def __init__(
        self,
        config_path: str | Path | None = None,
        project_root: str | Path | None = None,
    ) -> None:
        """
        @summary
        Initialize the service configuration and internal gateway state.

        The gateway instance is intentionally not created here.
        Initialization is deferred until initialize() or process()
        is called.

        @parameters
        config_path : str | Path | None
            Optional configuration file location.

        project_root : str | Path | None
            Optional project root directory.

        @returns
        None
        """

        # Resolve the project root from the module location unless
        # an explicit project directory has been provided.
        self.project_root = (
            Path(project_root).resolve()
            if project_root is not None
            else Path(__file__).resolve().parents[3]
        )

        # Resolve the configuration file location.
        self.config_path = (
            Path(config_path).resolve()
            if config_path is not None
            else self.project_root / "config" / "config.json"
        )

        # Gateway initialization is deferred until first use.
        self._gateway: GatewayAsync | None = None

    def load_config(self) -> dict[str, Any]:
        """
        @summary
        Load the gateway configuration and normalize filesystem paths.

        Relative paths are interpreted against the project root to
        ensure consistent resource resolution regardless of the
        application's current working directory.

        @returns
        dict[str, Any]
            Parsed gateway configuration with resolved filesystem paths.

        @raises
        FileNotFoundError
            If the configuration file does not exist.

        json.JSONDecodeError
            If the configuration file contains invalid JSON.
        """

        with self.config_path.open("r", encoding="utf-8") as config_file:
            config = json.load(config_file)

        # Normalize configured filesystem paths.
        for section, setting in self.PATH_SETTINGS:
            value = config.get(section, {}).get(setting)

            if value:
                path = Path(value)

                if not path.is_absolute():
                    config[section][setting] = str(
                        self.project_root / path
                    )

        return config

    def initialize(self) -> None:
        """
        @summary
        Initialize the asynchronous gateway using the loaded configuration.

        Creates the GatewayAsync instance and stores it for subsequent
        message-processing requests.

        @returns
        None
        """

        config = self.load_config()
        self._gateway = GatewayAsync(config)

    async def process(
        self,
        message: dict[str, Any],
    ) -> GatewayResponse:
        """
        @summary
        Process an incoming message through the gateway security pipeline.

        Initializes the gateway on first use if it has not already
        been initialized, then delegates message processing to
        GatewayAsync.

        @parameters
        message : dict[str, Any]
            Incoming message containing the fields required by the
            gateway schema, including id, counter, msg, and hmac.

        @returns
        GatewayResponse
            Structured response returned by the gateway, indicating
            whether message processing succeeded or failed.
        """

        # Initialize the gateway lazily when required.
        if self._gateway is None:
            self.initialize()

        return await self._gateway.process(message)
