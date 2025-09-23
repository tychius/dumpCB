import sys
import logging

# Use PySide6 imports
from PySide6.QtWidgets import QApplication

# Import the new main window class (adjust path/name as needed)
from app.ui.windows.main_window import MainWindow

def setup_logging():
    """Configures basic logging for the application."""
    log_format = '%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_format, stream=sys.stdout)
    logger = logging.getLogger(__name__)
    logger.info("Logging configured.")

# Removed check_clipboard() as Qt handles clipboard interaction internally

def main():
    """Main entry point for the PySide6 application."""
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Codebase Context Aggregator application (PySide6 UI)...")

    try:
        app = QApplication(sys.argv)

        # Apply global styles or settings if needed here
        # Example: app.setStyle("Fusion")

        main_window = MainWindow()
        main_window.show()

        exit_code = app.exec()
        logger.info(f"Application exited with code {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        logger.exception("An unhandled exception occurred during application setup or execution.")
        # Consider showing a simple critical error message box here if possible
        sys.exit(1) # Exit with error code
    finally:
        logger.info("Application closing sequence complete.")

if __name__ == "__main__":
    main() 