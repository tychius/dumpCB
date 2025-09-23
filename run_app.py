import sys
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

# Assuming qt_main_window.py is in app/ui/
# Adjust the import path if necessary based on your structure
try:
    # Ensure Qt resources are registered before any icon lookups
    import assets.resources_rc  # noqa: F401
    from app.ui.windows.main_window import MainWindow
except ImportError as e:
    logging.error(f"Could not import MainWindow/resources: {e}")
    sys.exit(1)

# Basic Logging Setup (can be more sophisticated)
# Configure to log to a file in a packaged app might be better
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format) 

# You could add a FileHandler here for packaged apps:
# log_file = Path(sys.executable).parent / 'app.log' if getattr(sys, 'frozen', False) else 'app.log' 
# file_handler = logging.FileHandler(log_file)
# file_handler.setFormatter(logging.Formatter(log_format))
# logging.getLogger().addHandler(file_handler) # Add handler to root logger

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("Starting dumpCB application...")
    
    # Set High DPI scaling policy (important for modern displays)
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    try:
        app = QApplication(sys.argv)
        
        # Set application details (optional but good)
        app.setApplicationName("dumpCB")
        # You might set organization details too
        # app.setOrganizationName("YourNameOrCompany") 
        
        # Set application icon from Qt resources (works for source and frozen builds)
        app.setWindowIcon(QIcon(":/logo.ico"))
        logger.info("Application icon set from Qt resources.")

        window = MainWindow()
        window.show()
        
        logger.info("Application event loop started.")
        exit_code = app.exec()
        logger.info(f"Application finished with exit code {exit_code}.")
        sys.exit(exit_code)
        
    except Exception as e:
        logger.exception(f"An unhandled exception occurred: {e}")
        # Optionally show a simple error dialog to the user here
        # from PySide6.QtWidgets import QMessageBox
        # error_dialog = QMessageBox()
        # error_dialog.setIcon(QMessageBox.Icon.Critical)
        # error_dialog.setText("An unexpected error occurred.")
        # error_dialog.setInformativeText(str(e))
        # error_dialog.setWindowTitle("Application Error")
        # error_dialog.exec()
        sys.exit(1) 