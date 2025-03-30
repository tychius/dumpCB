import sys
import logging
from typing import Optional, List, Dict
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QScrollArea,
    QCheckBox,
    QProgressBar,
    QSizePolicy,
    QFileDialog,
    QFrame,
    QStyle
)
from PySide6.QtCore import Slot, Qt, QFile, QTextStream, QObject, Signal, QThread, QPoint, QSize, QEvent # Added QEvent
from PySide6.QtGui import QFont, QFontDatabase, QIcon, QAction # Added QIcon

# Core logic imports
from app.core.main_processor import MainProcessor
from app.core.ignore_handler import IgnoreHandler
from app.utils.file_utils import is_binary_file

logger = logging.getLogger(__name__)

# --- Constants ---
STYLE_FILE = Path(__file__).parent / "style.qss"
# Preferred Monospace Fonts (add more if needed)
PREFERRED_MONO = ['JetBrains Mono', 'Fira Code', 'Consolas', 'Courier New', 'Menlo', 'Monaco', 'Liberation Mono', 'DejaVu Sans Mono']
# Preferred UI Font (optional)
PREFERRED_UI_FONT = ['Segoe UI', 'Inter', 'Roboto', 'Helvetica Neue', 'Arial']

# --- Worker for Background Tasks ---
class Worker(QObject):
    """Handles background processing tasks (scan, generate)."""
    scan_complete = Signal(list) # Emits list of Path objects
    generate_complete = Signal(str) # Emits the final formatted string
    error = Signal(str) # Emits error messages
    status_update = Signal(str) # Emits status updates

    def __init__(self, processor: MainProcessor):
        super().__init__()
        self.processor = processor
        self._is_running = True

    @Slot()
    def stop(self):
        self._is_running = False # Allow graceful stop if needed

    @Slot()
    def run_scan_task(self):
        """Executes the scan phase in the background."""
        if not self._is_running:
            return
        try:
            logger.info("Worker starting scan task...")
            self.status_update.emit("Scanning project structure...")
            all_paths = self.processor.run_scan_phase()
            if self._is_running:
                logger.info("Worker scan complete, emitting signal.")
                self.scan_complete.emit(all_paths)
        except Exception as e:
            logger.exception("Error in worker scan task")
            if self._is_running:
                self.error.emit(f"Scan Error: {e}")

    @Slot(list) # Takes the list of selected relative paths
    def run_generate_task(self, selected_files: List[Path]):
        """Executes the generate phase in the background."""
        if not self._is_running:
            return
        try:
            logger.info(f"Worker starting generate task with {len(selected_files)} files...")
            self.status_update.emit("Generating context...")
            result = self.processor.run_generate_phase(selected_files)
            if self._is_running:
                logger.info("Worker generate complete, emitting signal.")
                self.generate_complete.emit(result)
        except Exception as e:
            logger.exception("Error in worker generate task")
            if self._is_running:
                self.error.emit(f"Generation Error: {e}")

# --- Main Window --- 
class MainWindow(QMainWindow):
    """Main application window using PySide6 with custom title bar."""
    # Define signals if MainWindow needs to emit something (optional)

    def __init__(self, parent: Optional[QWidget] = None):
        """Initializes the main window."""
        super().__init__(parent)

        logger.info("Initializing MainWindow (PySide6 UI)")

        # --- Window Setup (Frameless) ---
        self.setWindowTitle("dumpCB")
        self.setGeometry(100, 100, 1000, 800)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint) # Hide native title bar
        # Remove the translucent attribute as it makes the window completely transparent
        # self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True) # Enable mouse tracking for hover events

        # --- State Variables ---
        self.selected_folder_path: Optional[Path] = None # Store as Path object
        self.is_scanning = False
        self.is_generating = False
        self.processor: Optional[MainProcessor] = None
        self.ignore_handler: Optional[IgnoreHandler] = None
        self.all_scanned_paths: List[Path] = []
        self.file_checkboxes: Dict[Path, QCheckBox] = {}
        self.worker_thread: Optional[QThread] = None
        self.worker: Optional[Worker] = None
        self.drag_position: Optional[QPoint] = None # For window dragging
        
        # For window resizing
        self.resize_margin = 8  # Margin area for resize
        self.resizing = False
        self.resize_direction = None

        # --- Font Setup ---
        self._configure_fonts()

        # --- UI Setup ---
        self._setup_ui()
        self._connect_signals()
        self._apply_stylesheet()
        self._update_ui_states() # Initial state

        logger.info("MainWindow initialization complete.")

    def _configure_fonts(self):
        """Configures and stores application fonts."""
        self.default_font = self._find_best_font(PREFERRED_UI_FONT, fallback_size=10)
        QApplication.setFont(self.default_font) # Apply globally
        logger.info(f"Using UI font: {self.default_font.family()}")
        self.mono_font = self._find_best_font(PREFERRED_MONO, fallback_size=10)
        logger.info(f"Using Monospace font: {self.mono_font.family()}")
        self.file_list_font = self._find_best_font(PREFERRED_UI_FONT, fallback_size=9)

    def _find_best_font(self, preferred_list: List[str], fallback_size: int = 10) -> QFont:
        """Finds the first available font from the preferred list."""
        available_fonts = QFontDatabase.families()
        for family in preferred_list:
            if family in available_fonts:
                return QFont(family, fallback_size)
        return QFont(QApplication.font().family(), fallback_size)

    # --- UI Setup Methods ---
    def _setup_ui(self):
        """Creates and arranges the widgets in the main window."""
        logger.debug("Setting up UI elements")
        # Main container needed for custom frameless window styling/background
        self.container_widget = QWidget()
        self.container_widget.setObjectName("containerWidget") # For QSS styling
        self.container_widget.setMouseTracking(True) # Enable mouse tracking on container too
        self.container_widget.installEventFilter(self)  # Install event filter
        self.setCentralWidget(self.container_widget) # Was central_widget

        self.main_layout = QVBoxLayout(self.container_widget) # Layout for the container
        self.main_layout.setContentsMargins(0, 0, 0, 0) # No margins on the container itself
        self.main_layout.setSpacing(0) # No spacing for main sections

        # --- Create UI sections --- 
        self._create_title_bar() # Create first
        
        # Create horizontal separator below title bar
        self.title_content_separator = QFrame()
        self.title_content_separator.setObjectName("titleContentSeparator")
        self.title_content_separator.setFrameShape(QFrame.Shape.HLine)
        self.title_content_separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.title_content_separator.setFixedHeight(1)
        
        self._create_content_area() # Create a content area below title bar

        # Add title bar and content area to main layout
        self.main_layout.addWidget(self.title_bar_widget)
        self.main_layout.addWidget(self.title_content_separator)
        self.main_layout.addWidget(self.content_area_widget, 1) # Content area takes stretch
        
        # --- Populate content area --- 
        content_layout = QVBoxLayout(self.content_area_widget)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(15)

        self._create_top_frame()
        self._create_action_frame()
        self._create_file_list_frame()
        self._create_progress_bar()
        self._create_output_textbox()
        self._create_status_bar()

        # Add sections to content layout
        content_layout.addWidget(self.top_frame_widget)
        content_layout.addWidget(self.action_frame_widget)
        content_layout.addWidget(self.file_list_label)
        content_layout.addWidget(self.file_list_scroll_area, 1)
        content_layout.addWidget(self.progress_bar)
        content_layout.addWidget(self.output_textbox, 2)
        content_layout.addWidget(self.status_bar_label)

        self.progress_bar.hide()

    def _create_content_area(self):
        """Creates the main container widget below the title bar."""
        self.content_area_widget = QWidget()
        self.content_area_widget.setObjectName("contentAreaWidget")
        self.content_area_widget.setMouseTracking(True)  # Enable mouse tracking in content area
        self.content_area_widget.installEventFilter(self)  # Install event filter
        # Layout set up in _setup_ui
        
    def _apply_stylesheet(self):
        """Loads and applies the QSS stylesheet."""
        # Define essential base styles that should always apply
        base_style = """
        QWidget#containerWidget {
            background-color: #1E1E2E;
            border: 1px solid #3A3A4A;
            border-radius: 6px;
        }
        
        QFrame#titleSeparator {
            color: #3A3A4A;
            background-color: #3A3A4A;
        }
        
        QFrame#titleContentSeparator {
            color: #3A3A4A;
            background-color: #3A3A4A;
        }
        
        QPushButton#minimizeButton, QPushButton#maximizeButton, QPushButton#closeButton {
            background-color: transparent;
            border: none;
            padding: 4px;
            qproperty-iconSize: 16px;
            qproperty-flat: true;
        }
        
        QPushButton#minimizeButton {
            padding-top: 2px; /* Reduce top padding to raise the icon */
            padding-bottom: 8px; /* Add bottom padding to center vertically */
        }
        
        QPushButton#minimizeButton:hover, QPushButton#maximizeButton:hover {
            background-color: #3A3A4A;
            border-radius: 4px;
        }
        
        QPushButton#closeButton:hover {
            background-color: #D32F2F;
            border-radius: 4px;
        }
        """

        loaded_style = ""
        try:
            if STYLE_FILE.exists():
                file = QFile(str(STYLE_FILE))
                if file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
                    stream = QTextStream(file)
                    loaded_style = stream.readAll()
                    file.close()
                    logger.info(f"Loaded stylesheet from {STYLE_FILE}")
                else:
                    logger.error(f"Could not open stylesheet file: {STYLE_FILE} - {file.errorString()}")
            else:
                logger.warning(f"Stylesheet file not found: {STYLE_FILE}. Using default styles.")
        except Exception as e:
            logger.exception(f"Error loading stylesheet: {e}")

        # Combine base style with loaded style (loaded style takes precedence)
        final_style = base_style + "\n" + loaded_style
        self.container_widget.setStyleSheet(final_style)

    def _create_title_bar(self):
        """Creates the custom title bar widget and its controls."""
        self.title_bar_widget = QWidget()
        self.title_bar_widget.setObjectName("titleBarWidget")
        self.title_bar_widget.setFixedHeight(35) # Set a fixed height
        self.title_bar_widget.setMouseTracking(True)  # Enable mouse tracking
        self.title_bar_widget.installEventFilter(self)  # Install event filter
        layout = QHBoxLayout(self.title_bar_widget)
        layout.setContentsMargins(10, 0, 0, 0) # Left margin, no top/bottom/right
        layout.setSpacing(10)

        # Title Label
        self.title_label = QLabel("dumpCB")
        self.title_label.setObjectName("titleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Vertical separator line
        self.title_separator = QFrame()
        self.title_separator.setObjectName("titleSeparator")
        self.title_separator.setFrameShape(QFrame.Shape.VLine)
        self.title_separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.title_separator.setFixedWidth(1)

        # Window Control Buttons using standard icons
        style = QApplication.style() # Get the application style

        self.minimize_button = QPushButton()
        # Switch back to icon for consistency, but we'll adjust its alignment in CSS
        self.minimize_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TitleBarMinButton))
        self.minimize_button.setIconSize(QSize(16, 16))  # Set larger icon size
        self.minimize_button.setObjectName("minimizeButton")
        self.minimize_button.setFixedSize(30, 30)
        self.minimize_button.setToolTip("Minimize")

        self.maximize_button = QPushButton()
        self.maximize_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton))
        self.maximize_button.setIconSize(QSize(16, 16))  # Set larger icon size
        self.maximize_button.setObjectName("maximizeButton")
        self.maximize_button.setFixedSize(30, 30)
        self.maximize_button.setToolTip("Maximize")

        self.close_button = QPushButton()
        self.close_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton))
        self.close_button.setIconSize(QSize(16, 16))  # Set larger icon size
        self.close_button.setObjectName("closeButton")
        self.close_button.setFixedSize(30, 30)
        self.close_button.setToolTip("Close")

        layout.addWidget(self.title_label)
        layout.addStretch(1)
        layout.addWidget(self.title_separator)
        layout.addWidget(self.minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(self.close_button)
        
        # Set object name for the layout if needed for margins/spacing via QSS
        # layout.setObjectName("titleBarLayout") 

    def _create_top_frame(self):
        self.top_frame_widget = QWidget()
        self.top_frame_widget.setObjectName("top_frame_widget")
        layout = QHBoxLayout(self.top_frame_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.select_folder_button = QPushButton("Select Project Folder")
        self.select_folder_button.setObjectName("selectFolderButton")
        self.select_folder_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setObjectName("folderPathLabel")
        self.folder_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.folder_label.setWordWrap(True)
        layout.addWidget(self.select_folder_button)
        layout.addWidget(self.folder_label, 1)

    def _create_action_frame(self):
        self.action_frame_widget = QWidget()
        self.action_frame_widget.setObjectName("action_frame_widget")
        layout = QHBoxLayout(self.action_frame_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.select_all_button = QPushButton("Select All Files")
        self.select_all_button.setObjectName("selectAllButton")
        self.deselect_all_button = QPushButton("Deselect All")
        self.deselect_all_button.setObjectName("deselectAllButton")
        self.generate_button = QPushButton("Generate Context")
        self.generate_button.setObjectName("generateButton")
        self.copy_button = QPushButton("Copy to Clipboard")
        self.copy_button.setObjectName("copyButton")
        self.save_button = QPushButton("Save to File")
        self.save_button.setObjectName("saveButton")
        self.clear_button = QPushButton("Clear")
        self.clear_button.setObjectName("clearButton")
        self.clear_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.select_all_button)
        layout.addWidget(self.deselect_all_button)
        layout.addStretch(1)
        layout.addWidget(self.generate_button)
        layout.addWidget(self.copy_button)
        layout.addWidget(self.save_button)
        layout.addStretch(1)
        layout.addWidget(self.clear_button)

    def _create_file_list_frame(self):
        self.file_list_label = QLabel("Select Files for Context:")
        self.file_list_label.setObjectName("fileListLabel")
        self.file_list_label.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)
        self.file_list_scroll_area = QScrollArea()
        self.file_list_scroll_area.setObjectName("fileListScrollArea")
        self.file_list_scroll_area.setWidgetResizable(True)
        self.file_list_scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.file_list_container = QWidget()
        self.file_list_container.setObjectName("fileListContainer")
        self.file_list_layout = QVBoxLayout(self.file_list_container)
        self.file_list_layout.setContentsMargins(5, 5, 5, 5)
        self.file_list_layout.setSpacing(3)
        self.file_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.file_list_scroll_area.setWidget(self.file_list_container)

    def _create_progress_bar(self):
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _create_output_textbox(self):
        self.output_textbox = QTextEdit()
        self.output_textbox.setObjectName("outputTextEdit")
        self.output_textbox.setReadOnly(True)
        self.output_textbox.setFont(self.mono_font)
        self.output_textbox.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.output_textbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _create_status_bar(self):
        self.status_bar_label = QLabel("Ready")
        self.status_bar_label.setObjectName("statusBarLabel")
        self.status_bar_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    # --- Signal Connections --- 
    def _connect_signals(self):
        """Connects widget signals to appropriate slots."""
        # Title bar buttons
        self.minimize_button.clicked.connect(self.showMinimized)
        self.maximize_button.clicked.connect(self._toggle_maximize_restore)
        self.close_button.clicked.connect(self.close)
        
        # Main content buttons
        self.select_folder_button.clicked.connect(self.select_folder)
        self.select_all_button.clicked.connect(self._select_all_files)
        self.deselect_all_button.clicked.connect(self._deselect_all_files)
        self.generate_button.clicked.connect(self.start_generate_thread)
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.save_button.clicked.connect(self.save_to_file)
        self.clear_button.clicked.connect(self.clear_all)
        # Worker/Thread signals connected when tasks are started

    # --- UI State Update --- 
    def _update_ui_states(self):
        """Updates the enabled/disabled state of widgets based on app state."""
        is_processing = self.is_scanning or self.is_generating
        folder_selected = self.selected_folder_path is not None
        scan_complete = bool(self.all_scanned_paths)
        has_output = self.output_textbox.toPlainText() != ""
        output_is_error = self.status_bar_label.property("status") == "error"

        self.select_folder_button.setEnabled(not is_processing)
        self.select_all_button.setEnabled(scan_complete and not is_processing)
        self.deselect_all_button.setEnabled(scan_complete and not is_processing)
        self.generate_button.setEnabled(scan_complete and not is_processing)
        self.copy_button.setEnabled(has_output and not output_is_error and not is_processing)
        self.save_button.setEnabled(has_output and not output_is_error and not is_processing)
        self.clear_button.setEnabled(folder_selected and not is_processing)

        logger.debug(f"Updating UI states: processing={is_processing}, folder={folder_selected}, scan={scan_complete}, output={has_output}, error_state={output_is_error}")
        
        # Update maximize button icon based on window state
        style = QApplication.style()
        if self.isMaximized():
            self.maximize_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton)) # Restore icon
            self.maximize_button.setIconSize(QSize(16, 16))  # Maintain icon size
            self.maximize_button.setToolTip("Restore")
        else:
            self.maximize_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton)) # Maximize icon
            self.maximize_button.setIconSize(QSize(16, 16))  # Maintain icon size
            self.maximize_button.setToolTip("Maximize")

    # --- Core Action Slots --- 
    @Slot()
    def _toggle_maximize_restore(self):
        """Toggles between maximized and normal window state."""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        # State update will fix button appearance
        self._update_ui_states() 
        
    @Slot()
    def select_folder(self):
        """Handles the 'Select Project Folder' button click."""
        if self.is_scanning or self.is_generating:
            return # Prevent action while busy
            
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Project Root Folder",
            str(self.selected_folder_path or Path.home()) # Start at previous or home
        )

        if dir_path:
            self.clear_all() # Clear previous state
            self.selected_folder_path = Path(dir_path)
            self.folder_label.setText(dir_path) # Update label directly
            self.update_status(f"Selected: {dir_path}. Starting scan...")
            logger.info(f"Folder selected: {dir_path}. Starting scan.")
            self.start_scan_thread(dir_path)
        else:
            logger.info("Folder selection cancelled.")
            # No need to clear again if cancelled, select_folder already cleared
            
    @Slot()
    def clear_all(self):
        """Clears the current state and UI elements."""
        logger.info("Clearing selection and output.")
        self.selected_folder_path = None
        self.folder_label.setText("No folder selected")
        self.processor = None
        self.ignore_handler = None
        self.all_scanned_paths = []
        self.file_checkboxes = {}
        self._cleanup_thread() # Stop existing thread if any

        # Clear UI elements
        for i in reversed(range(self.file_list_layout.count())):
            widget = self.file_list_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        self.output_textbox.clear()
        self.update_status("Ready")
        self._update_ui_states()

    @Slot()
    def _select_all_files(self):
        """Checks all enabled checkboxes in the file list."""
        logger.info("Selecting all valid files.")
        changed = False
        for cb in self.file_checkboxes.values():
            if cb.isEnabled() and not cb.isChecked():
                cb.setChecked(True)
                changed = True
        if changed:
            logger.debug("Selected all enabled files.")

    @Slot()
    def _deselect_all_files(self):
        """Unchecks all enabled checkboxes in the file list."""
        logger.info("Deselecting all files.")
        changed = False
        for cb in self.file_checkboxes.values():
             if cb.isEnabled() and cb.isChecked():
                cb.setChecked(False)
                changed = True
        if changed:
            logger.debug("Deselected all enabled files.")

    # --- Threading and Worker Interaction ---
    def _setup_worker_thread(self):
        """Creates and configures the worker and thread."""
        if not self.selected_folder_path:
             logger.error("Cannot setup worker without a selected folder path.")
             return False
             
        try:
            self.processor = MainProcessor(str(self.selected_folder_path))
            self.ignore_handler = self.processor.ignore_handler # Get handler
            if not self.ignore_handler:
                 raise RuntimeError("IgnoreHandler failed to initialize in MainProcessor")

            self._cleanup_thread() # Ensure previous thread is stopped
            
            self.worker = Worker(self.processor)
            self.worker_thread = QThread()
            self.worker.moveToThread(self.worker_thread)

            # Connect worker signals to main window slots
            self.worker.scan_complete.connect(self._handle_scan_complete)
            self.worker.generate_complete.connect(self._handle_generate_complete)
            self.worker.error.connect(self._handle_error)
            self.worker.status_update.connect(self.update_status)

            # Connect thread signals
            self.worker_thread.started.connect(self.worker.run_scan_task) # Default action on start
            self.worker_thread.finished.connect(self._on_thread_finished)
            
            return True
            
        except Exception as e:
            logger.exception("Failed to setup worker thread")
            self.update_status(f"Error initializing processor: {e}", is_error=True)
            self.processor = None # Ensure processor is None on error
            self.ignore_handler = None
            return False

    def start_scan_thread(self, folder_path: str):
        """Starts the background thread for the scan task."""
        if self.is_scanning or self.is_generating:
            logger.warning("Processing already in progress.")
            return
            
        if self._setup_worker_thread(): # Setup includes processor init
            self.is_scanning = True
            self._update_ui_states()
            self._show_progress_bar("Scanning project structure...")
            logger.info(f"Starting scan thread for: {folder_path}")
            self.worker_thread.start()
        else:
            # Error already logged by _setup_worker_thread
            self._update_ui_states() # Update UI to reflect failed start
            
    @Slot()
    def start_generate_thread(self):
        """Starts the background thread for the generate task."""
        if self.is_scanning: # Explicit check for scanning
            logger.warning("Generate requested while scan is in progress. Ignoring.")
            self.update_status("Scan in progress, please wait...", is_error=True)
            return
        if self.is_generating:
            logger.warning("Generate requested while already generating. Ignoring.")
            return
            
        if not self.processor or not self.worker or not self.worker_thread:
             self.update_status("Error: No project scanned or worker not ready.", is_error=True)
             logger.error("Generate clicked but processor/worker/thread not ready.")
             return

        selected_files = [
            path for path, cb in self.file_checkboxes.items()
            if cb.isChecked() and cb.isEnabled()
        ]

        if not selected_files:
            self.update_status("Error: No files selected for generation.", is_error=True)
            return

        self.is_generating = True
        self._update_ui_states()
        self._show_progress_bar("Generating context...")
        self.output_textbox.clear() # Clear previous output

        # Disconnect scan task from started signal if connected
        try: self.worker_thread.started.disconnect(self.worker.run_scan_task) 
        except RuntimeError: pass # Ignore if not connected
        # Connect generate task to started signal
        self.worker_thread.started.connect(lambda: self.worker.run_generate_task(selected_files))
        
        logger.info(f"Starting generate thread with {len(selected_files)} selected files.")
        # Restart the thread (safe way to trigger new task on existing thread/worker)
        if self.worker_thread.isRunning():
            logger.warning("Generate thread requested while thread was already running? This shouldn't happen often.")
            # If needed, could implement a queue or signal the worker directly
            # For now, we rely on UI state preventing this.
            self.worker.run_generate_task(selected_files) # Try direct call if running? Risky.
        else:
             self.worker_thread.start()

    def _cleanup_thread(self):
        """Stops and cleans up the worker thread."""
        if self.worker_thread and self.worker_thread.isRunning():
            logger.info("Requesting worker thread to quit...")
            if self.worker:
                self.worker.stop() # Signal worker to stop gracefully if possible
            self.worker_thread.quit()
            if not self.worker_thread.wait(3000): # Wait 3 seconds
                 logger.warning("Worker thread did not quit gracefully. Terminating.")
                 self.worker_thread.terminate() # Force terminate if needed
                 self.worker_thread.wait() # Wait after terminate
            logger.info("Worker thread finished.")
        self.worker_thread = None
        self.worker = None

    @Slot()
    def _on_thread_finished(self):
        """Slot called when the worker thread finishes naturally."""
        logger.debug("Worker thread finished signal received.")
        # State (is_scanning/is_generating) should be set false by the task completion handler
        # or the finally block of the worker method.
        # self._update_ui_states() # UI state often updated by task completion signal handler

    # --- Worker Signal Handlers (Slots) ---
    @Slot(list)
    def _handle_scan_complete(self, all_paths: List[Path]):
        """Handles the scan_complete signal from the worker."""
        logger.info(f"Scan complete signal received with {len(all_paths)} paths.")
        self.is_scanning = False
        self._hide_progress_bar()
        self._populate_file_list_ui(all_paths)
        # self.update_status("Scan complete. Review files...") # Status set in _populate
        self._update_ui_states()

    @Slot(str)
    def _handle_generate_complete(self, result: str):
        """Handles the generate_complete signal from the worker."""
        logger.info(f"Generate complete signal received. Result length: {len(result)}")
        self.is_generating = False
        self._hide_progress_bar()
        self._update_output_textbox(result)
        self.update_status("Context generated successfully.", status_type="success")
        self._update_ui_states()

    @Slot(str)
    def _handle_error(self, error_message: str):
        """Handles the error signal from the worker."""
        logger.error(f"Worker error signal received: {error_message}")
        # Determine which phase failed based on state
        if self.is_scanning:
             self.update_status(f"Scan Failed: {error_message}", is_error=True)
             self.clear_all() # Clear state on scan fail
        elif self.is_generating:
             self.update_status(f"Generation Failed: {error_message}", is_error=True)
             self._update_output_textbox(f"ERROR:\n{error_message}", is_error=True)
        else:
             self.update_status(f"Error: {error_message}", is_error=True)

        self.is_scanning = False
        self.is_generating = False
        self._hide_progress_bar()
        self._update_ui_states()
        
    # --- UI Update Methods ---
    def _populate_file_list_ui(self, all_paths: List[Path]):
        """Clears and populates the file list scroll area with checkboxes."""
        logger.info(f"Populating file list UI with {len(all_paths)} items.")
        self.all_scanned_paths = all_paths
        self.file_checkboxes = {}

        # Clear previous widgets safely
        while self.file_list_layout.count():
            item = self.file_list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not self.processor or not self.ignore_handler:
            logger.error("Processor or IgnoreHandler not available for populating file list.")
            self._handle_error("Internal state error during scan results processing.")
            return

        project_root = self.processor.project_path
        processed_count = 0
        for relative_path in all_paths:
            try:
                path_str = relative_path.as_posix()
                absolute_path = project_root / relative_path
                is_dir = absolute_path.is_dir()

                # Determine initial check state & enabled state
                initial_check = False
                is_enabled = False
                if not is_dir:
                    is_binary = is_binary_file(absolute_path)
                    is_ignored = self.ignore_handler.is_ignored(absolute_path)
                    if not is_binary and not is_ignored:
                        initial_check = True # Default check valid files
                        is_enabled = True

                checkbox = QCheckBox(path_str)
                checkbox.setFont(self.file_list_font)
                checkbox.setChecked(initial_check)
                checkbox.setEnabled(is_enabled)
                # QSS :disabled selector handles visual style

                self.file_list_layout.addWidget(checkbox)
                self.file_checkboxes[relative_path] = checkbox
                processed_count += 1
            except Exception as e:
                 logger.warning(f"Error processing path for UI list '{relative_path}': {e}")
                 
        # Remove the stretch item if it exists, then re-add it
        if self.file_list_layout.count() > processed_count:
             item = self.file_list_layout.takeAt(self.file_list_layout.count() -1)
             if item:
                del item # Should delete the spacer item
        self.file_list_layout.addStretch(1) # Ensure items align top

        logger.info(f"Finished populating file list UI. Added {processed_count} items.")
        self.update_status("Scan complete. Review files and click 'Generate Context'.")
        # self._update_ui_states() # Called by _handle_scan_complete

    def _show_progress_bar(self, status_message: str = "Processing..."):
        """Shows the progress bar and updates status."""
        self.update_status(status_message)
        self.progress_bar.show()
        # self.progress_bar.setRange(0, 0) # Already set in init

    def _hide_progress_bar(self):
        """Hides the progress bar."""
        self.progress_bar.hide()

    def _update_output_textbox(self, result: str, is_error: bool = False):
        """Updates the main output text box."""
        self.output_textbox.setPlainText(result) # Use setPlainText for efficiency
        # State (success/error) is handled by the calling slot (_handle_generate_complete or _handle_error)
        
    @Slot(str, str)
    def update_status(self, message: str, status_type: str = "info"):
        """Updates the status bar label and its style property.
           status_type can be 'info', 'success', 'error'."""
        self.status_bar_label.setText(message)
        # Set a dynamic property for QSS styling
        if status_type == "error":
            self.status_bar_label.setProperty("status", "error")
            logger.error(f"Status Update (Error): {message}")
        elif status_type == "success":
            self.status_bar_label.setProperty("status", "success")
            logger.info(f"Status Update (Success): {message}")
        else:
            self.status_bar_label.setProperty("status", "info") # Default/info
            logger.info(f"Status Update: {message}")
            
        # Force style refresh to apply property changes
        self.style().unpolish(self.status_bar_label)
        self.style().polish(self.status_bar_label)

    # --- Other Action Slots ---
    @Slot()
    def copy_to_clipboard(self):
        """Copies the content of the output textbox to the clipboard."""
        content = self.output_textbox.toPlainText()
        if content:
            try:
                clipboard = QApplication.clipboard()
                clipboard.setText(content)
                logger.info(f"Copied {len(content)} characters to clipboard.")
                self.update_status("Content copied to clipboard!", status_type="success")
            except Exception as e:
                logger.exception("Error copying to clipboard using Qt")
                self.update_status(f"Error copying: {e}", is_error=True)
        else:
            self.update_status("Nothing to copy.")

    @Slot()
    def save_to_file(self):
        """Saves the content of the output textbox to a file."""
        content = self.output_textbox.toPlainText()
        if not content:
            self.update_status("Nothing to save.")
            return

        default_filename = "llm_context.md"
        if self.selected_folder_path:
            default_filename = self.selected_folder_path.name + "_context.md"
            
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Context As",
            str(self.selected_folder_path / default_filename if self.selected_folder_path else default_filename),
            "Markdown files (*.md);;Text files (*.txt);;All files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Content saved to file: {file_path}")
                self.update_status(f"Saved to {Path(file_path).name}", status_type="success")
            except Exception as e:
                logger.exception("Error saving to file")
                self.update_status(f"Error saving file: {e}", is_error=True)
        else:
            logger.info("Save file operation cancelled.")

    # --- Mouse Events for Dragging --- 
    def mousePressEvent(self, event):
        """Captures mouse press events for window dragging and resizing."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if we're in a resize area
            resize_area = self._get_resize_area(event.position().toPoint())
            if resize_area:
                self.resizing = True
                self.resize_direction = resize_area
                self.drag_position = event.globalPosition().toPoint()
                event.accept()
                return
            
            # Check if the press is within the title bar widget bounds
            if self.title_bar_widget.geometry().contains(event.position().toPoint()):
                 # Calculate position difference for smooth dragging
                 self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                 logger.debug(f"Mouse press in title bar, starting drag at {self.drag_position}")
                 event.accept()
            else:
                 self.drag_position = None
                 # Pass event down if not on title bar (allows interaction with content)
                 super().mousePressEvent(event) 
        else:
             super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handles mouse move events for window dragging and resizing."""
        # Resize handling
        if self.resizing and event.buttons() == Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint()
            diff = new_pos - self.drag_position
            self.drag_position = new_pos
            
            # Get geometry
            geo = self.geometry()
            
            # Apply appropriate resize based on direction
            if 'left' in self.resize_direction:
                geo.setLeft(geo.left() + diff.x())
            if 'right' in self.resize_direction:
                geo.setRight(geo.right() + diff.x())
            if 'top' in self.resize_direction:
                geo.setTop(geo.top() + diff.y())
            if 'bottom' in self.resize_direction:
                geo.setBottom(geo.bottom() + diff.y())
                
            # Enforce minimum size
            if geo.width() < 600:
                if 'left' in self.resize_direction:
                    geo.setLeft(geo.right() - 600)
                else:
                    geo.setRight(geo.left() + 600)
            
            if geo.height() < 400:
                if 'top' in self.resize_direction:
                    geo.setTop(geo.bottom() - 400)
                else:
                    geo.setBottom(geo.top() + 400)
            
            self.setGeometry(geo)
            event.accept()
            return
            
        # Update cursor based on position
        pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
        resize_area = self._get_resize_area(pos)
        
        if resize_area:
            # Set appropriate cursor based on resize area
            if resize_area == "top-left" or resize_area == "bottom-right":
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif resize_area == "top-right" or resize_area == "bottom-left":
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif resize_area == "left" or resize_area == "right":
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif resize_area == "top" or resize_area == "bottom":
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            
            # Don't accept event here to allow other widgets to receive it
            return
        else:
            # Reset cursor if not in resize area
            self.setCursor(Qt.CursorShape.ArrowCursor)
        
        # Dragging handling when left button is pressed
        if hasattr(event, 'buttons') and event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None and not self.resizing:
            # Move the window to the new position
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
            return
        
        # Let the event propagate if not handled
        if hasattr(event, 'ignore'):
            event.ignore()

    def mouseReleaseEvent(self, event):
        """Handles mouse release events to stop dragging or resizing."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.resizing:
                self.resizing = False
                self.resize_direction = None
                event.accept()
                return
            if self.drag_position is not None:
                logger.debug("Mouse release, stopping drag")
                self.drag_position = None
                event.accept()
                return
        super().mouseReleaseEvent(event)
    
    def _get_resize_area(self, pos):
        """Determines if position is in a resize area, returns direction(s)."""
        rect = self.rect()
        margin = self.resize_margin
        
        # Check borders
        top = pos.y() <= margin
        bottom = pos.y() >= rect.height() - margin
        left = pos.x() <= margin
        right = pos.x() >= rect.width() - margin
        
        # Return directions as a string e.g. "top-left", "right", etc.
        if top and left: return "top-left"
        if top and right: return "top-right"
        if bottom and left: return "bottom-left"
        if bottom and right: return "bottom-right"
        if top: return "top"
        if bottom: return "bottom"
        if left: return "left"
        if right: return "right"
        return None

    # --- Window Close Event --- 
    def closeEvent(self, event):
        """Handle window close event, ensuring thread cleanup."""
        logger.info("Close event triggered. Cleaning up...")
        self._cleanup_thread()
        super().closeEvent(event)

    def eventFilter(self, watched, event):
        """Event filter to handle mouse tracking/cursor changes for all child widgets."""
        if event.type() == QEvent.Type.MouseMove:
            # Forward mouse move events to main window for cursor updates
            self.mouseMoveEvent(event)
            return False  # Still allow the event to be handled by its target
        return super().eventFilter(watched, event)

# --- Standalone Execution (for testing UI file directly) ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 