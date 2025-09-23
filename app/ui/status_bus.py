import logging
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

class StatusBus(QObject):
    """
    A central bus for emitting status updates throughout the application.
    Components can emit signals here instead of directly manipulating UI elements.
    """
    # Signals carry the message string
    info_message_updated = Signal(str)
    success_message_updated = Signal(str)
    error_message_updated = Signal(str)
    # Progress signal: (active: bool, message: str)
    progress_updated = Signal(bool, str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

    def info(self, message: str):
        logger.debug(f"StatusBus emitting info: {message}")
        self.info_message_updated.emit(message)

    def success(self, message: str):
        logger.debug(f"StatusBus emitting success: {message}")
        self.success_message_updated.emit(message)

    def error(self, message: str):
        logger.warning(f"StatusBus emitting error: {message}") # Log errors as warnings
        self.error_message_updated.emit(message)

    def progress(self, active: bool, message: str = ""):
        logger.debug(f"StatusBus emitting progress: active={active}, msg='{message}'")
        self.progress_updated.emit(active, message)

    def reset(self):
        """Resets the status to a default 'Ready' state."""
        logger.debug("StatusBus resetting status.")
        self.info("Ready")

# Global instance (Singleton pattern)
# This allows easy access from anywhere without complex dependency injection
# Ensure this is appropriate for your application's scale and testing needs.
_status_bus_instance: StatusBus | None = None

def get_status_bus() -> StatusBus:
    """Returns the global singleton StatusBus instance."""
    global _status_bus_instance
    if _status_bus_instance is None:
        _status_bus_instance = StatusBus()
    return _status_bus_instance

__all__ = ["StatusBus", "get_status_bus"] 