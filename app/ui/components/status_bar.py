from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Slot, QTimer

class StatusBar(QLabel):
    def __init__(self, parent=None):
        super().__init__("Ready", parent)
        self.setObjectName("statusBar")
        # Optional: Add default styling for status types
        self.setStyleSheet("""
            StatusBar[status="info"] { color: black; }
            StatusBar[status="success"] { color: green; }
            StatusBar[status="warning"] { color: orange; }
            StatusBar[status="error"] { color: red; }
        """)
        self._default_text = "Ready"

    @Slot(str, str)
    def update_status(self, text: str, status_type: str = "info", duration_ms: int = 0):
        """Updates the status bar text and optionally clears it after a duration."""
        self.setText(text)
        self.setProperty("status", status_type)
        # Re-polish to apply stylesheet changes based on the property
        self.style().unpolish(self)
        self.style().polish(self)

        # If duration is provided, reset to default after timeout
        if duration_ms > 0:
            QTimer.singleShot(duration_ms, self.reset_status)

    def reset_status(self):
        """Resets the status bar to its default text."""
        self.update_status(self._default_text, "info")

    def set_default_text(self, text: str):
        """Sets the default text to reset to."""
        self._default_text = text 