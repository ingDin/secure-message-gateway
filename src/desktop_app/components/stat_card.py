
"""
@summary
Reusable dashboard statistic card for the Secure Message Gateway
desktop application.

This module provides a reusable PyQt6 widget for displaying a single
operational metric through a title, primary value, descriptive subtitle,
and configurable accent indicator.

The component is presentation-focused and independent of gateway
business logic. Metric values are supplied externally by the
application's presentation or service layer.

@architecture
- Extends QFrame to provide a reusable dashboard container.
- Uses QVBoxLayout for consistent vertical component arrangement.
- Exposes set_value() as the public interface for metric updates.
- Uses Qt object names for centralized QSS styling.

@security
The component displays only values explicitly provided by the caller.
It must not be used to display cryptographic keys or sensitive
configuration material.
"""

from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QWidget,
)


class StatCard(QFrame):
    """
    @summary
    Reusable visual component for displaying a single application metric.

    The widget presents a metric title, its current value, an optional
    description, and a colored accent indicator.

    It does not retrieve or calculate gateway statistics. Data is
    provided by the component's caller.

    @parameters
    title : str
        Human-readable title identifying the displayed metric.
    value : str
        Initial metric value. Defaults to "N/A" when data is unavailable.
    subtitle : str
        Supporting description displayed below the primary value.
    accent : str
        Hexadecimal color used for the accent indicator.
    parent : QWidget | None
        Optional parent widget in the Qt object hierarchy.

    @examples
    >>> card = StatCard(
    ...     title="ACCEPTED MESSAGES",
    ...     value="N/A",
    ...     accent="#10B981",
    ... )
    """

    def __init__(
        self,
        title: str,
        value: str = "N/A",
        subtitle: str = "Waiting for gateway data",
        accent: str = "#8B5CF6",
        parent: QWidget | None = None,
    ) -> None:
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

    def set_value(
        self,
        value: str,
        subtitle: str = "",
    ) -> None:
        """
        @summary
        Update the displayed metric value and optional description.

        Updates the primary value label and optionally replaces the
        supporting subtitle.

        @parameters
        value : str
            New metric value to display.
        subtitle : str
            Optional replacement description. If empty, the existing
            subtitle remains unchanged.

        @returns
        None
        """
        self.value_label.setText(value)

        if subtitle:
            self.subtitle_label.setText(subtitle)
