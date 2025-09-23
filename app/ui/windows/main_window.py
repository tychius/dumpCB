"""
MainWindow: The main application window and entry point for the UI.
Sets up the widget hierarchy, applies styles, and wires up the presenter.
Public API: MainWindow class (instantiated by run_app.py).
"""
import logging
from typing import Optional, List
from pathlib import Path
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QTextEdit, QProgressBar, 
                             QSizePolicy, QFrame, QApplication, QSpacerItem)
from PySide6.QtCore import Qt, QFile, QTextStream, QIODevice
from PySide6.QtGui import QFont, QFontDatabase, QKeySequence
from app.ui.frameless_window_mixin import FramelessWindowMixin
from app.ui.components.title_bar import TitleBar
from app.ui.components.file_list_view import FileListView
from app.ui.presenters.window_presenter import WindowPresenter
import assets.resources_rc

logger = logging.getLogger(__name__)

STYLE_FILE = Path(__file__).parent / "../style.qss"
PREFERRED_MONO = ['JetBrains Mono', 'Fira Code', 'Consolas', 'Courier New', 'Menlo', 'Monaco', 'Liberation Mono', 'DejaVu Sans Mono']
PREFERRED_UI_FONT = ['Segoe UI', 'Inter', 'Roboto', 'Helvetica Neue', 'Arial']

class MainWindow(QMainWindow, FramelessWindowMixin):
    """
    Main application window using PySide6 with custom title bar.

    Responsibilities:
    - Setting up the main window frame and properties.
    - Building the UI widget hierarchy.
    - Applying base styles and loading QSS.
    - Instantiating the WindowPresenter to handle logic and interactions.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        logger.info("Initializing MainWindow (Modularized UI)")
        self.setWindowTitle("dumpCB")
        self.setGeometry(100, 100, 1000, 800)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self._configure_fonts()
        self._build_ui()
        self._apply_stylesheet()

        # Instantiate the presenter, passing necessary UI elements
        self.presenter = WindowPresenter(window=self)

        logger.info("MainWindow initialization complete.")

    def _configure_fonts(self):
        """Configures default, monospace, and file list fonts for the application."""
        self.default_font = self._find_best_font(PREFERRED_UI_FONT, fallback_size=10)
        self.mono_font = self._find_best_font(PREFERRED_MONO, fallback_size=10)
        self.file_list_font = self._find_best_font(PREFERRED_UI_FONT, fallback_size=9)

    def _find_best_font(self, preferred_list: List[str], fallback_size: int = 10) -> QFont:
        """Finds the best available font from a preferred list, falling back if needed."""
        available_fonts = QFontDatabase.families()
        for family in preferred_list:
            if family in available_fonts:
                return QFont(family, fallback_size)
        return QFont(QApplication.font().family(), fallback_size)

    def _build_ui(self):
        """Constructs the main UI layout and widgets."""
        self.container_widget = QWidget()
        self.container_widget.setObjectName("containerWidget")
        self.setCentralWidget(self.container_widget)
        self.main_layout = QVBoxLayout(self.container_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self._create_title_bar()
        self.title_content_separator = QFrame()
        self.title_content_separator.setObjectName("titleContentSeparator")
        self.title_content_separator.setFrameShape(QFrame.Shape.HLine)
        self.title_content_separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.title_content_separator.setFixedHeight(1)
        self._create_content_area()
        self.main_layout.addWidget(self.title_bar_widget)
        self.main_layout.addWidget(self.title_content_separator)
        self.main_layout.addWidget(self.content_area_widget, 1)
        content_layout = QVBoxLayout(self.content_area_widget)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(15)

        # Create standard elements first
        self._create_top_frame()      # Folder selection
        self._create_action_frame()   # Buttons
        self._create_file_list_frame()# File list label and view widget
        self._create_output_textbox() # Output text edit
        self._create_progress_bar()   # Progress bar
        self._create_status_bar()     # Status label

        # --- Create Side-by-Side Layout --- 
        self.side_by_side_widget = QWidget()
        side_by_side_layout = QHBoxLayout(self.side_by_side_widget)
        side_by_side_layout.setContentsMargins(0,0,0,0)
        side_by_side_layout.setSpacing(15) # Spacing between panels

        # Left Panel (Files)
        left_panel_widget = QWidget()
        left_layout = QVBoxLayout(left_panel_widget)
        left_layout.setContentsMargins(0,0,0,0)
        left_layout.setSpacing(5) # Spacing within left panel
        left_layout.addWidget(self.file_list_label)
        left_layout.addWidget(self.file_list_view, 1) # Give list view vertical stretch

        # Right Panel (Output)
        right_panel_widget = QWidget()
        right_layout = QVBoxLayout(right_panel_widget)
        right_layout.setContentsMargins(0,0,0,0)
        right_layout.setSpacing(5) # Spacing within right panel
        self.output_label = QLabel("Output:") # Added label for output
        self.output_label.setObjectName("outputLabel") # Allow styling if needed
        right_layout.addWidget(self.output_label)
        right_layout.addWidget(self.output_textbox, 1) # Give textbox vertical stretch

        # Add panels to side-by-side layout
        side_by_side_layout.addWidget(left_panel_widget, 1) # Stretch factor 1
        side_by_side_layout.addWidget(right_panel_widget, 1) # Stretch factor 1 (adjust as needed, e.g., 2 for more output space)

        # --- Add elements to main content layout --- 
        content_layout.addWidget(self.top_frame_widget)
        content_layout.addWidget(self.action_frame_widget)

        # Ensure Separator Line is created before being added
        self.content_separator = QFrame() # Create the attribute here
        self.content_separator.setObjectName("contentSeparator")
        self.content_separator.setFrameShape(QFrame.Shape.HLine)
        self.content_separator.setFrameShadow(QFrame.Shadow.Sunken)
        content_layout.addWidget(self.content_separator) # Add it to the layout

        content_layout.addWidget(self.side_by_side_widget, 1)
        content_layout.addWidget(self.progress_bar)
        content_layout.addWidget(self.status_bar_widget)

        self.progress_bar.hide()

    def _create_content_area(self):
        """Creates the main content area widget."""
        self.content_area_widget = QWidget()
        self.content_area_widget.setObjectName("contentAreaWidget")

    def _compose_base_style(self) -> str:
        """Composes the base QSS styles for the main window elements."""
        # Using the refined color palette from style.qss
        return """
        QWidget#containerWidget {
            background-color: #1E1E1E; /* bg-secondary */
            border: 1px solid #323232; /* border */
            border-radius: 4px;
        }
        
        QFrame#titleContentSeparator {
            color: #323232;           /* border */
            background-color: #323232;/* border */
        }
        QPushButton#minimizeButton, QPushButton#maximizeButton, QPushButton#closeButton {
            background-color: transparent;
            border: none;
            padding: 4px;
            qproperty-iconSize: 16px;
            qproperty-flat: true;
        }
        QPushButton#minimizeButton:hover, QPushButton#maximizeButton:hover {
            background-color: #2A2F38; /* accent */
            border-radius: 4px;
        }
        QPushButton#closeButton:hover {
            background-color: #D35252; /* danger */
            border-radius: 4px;
        }
        """

    def _load_qss(self) -> str:
        """Loads the QSS stylesheet from the style.qss file. - DEPRECATED
        NOTE: This fallback logic is no longer needed as we rely solely on resources.
        """
        # logger.warning("_load_qss fallback is deprecated. Styles should load from resources.")
        # return ""
        # Keep the old logic commented out for reference, but return empty string.
        loaded_style = ""
        # try:
        #     if STYLE_FILE.exists():
        #         from PySide6.QtCore import QFile, QTextStream
        #         file = QFile(str(STYLE_FILE))
        #         if file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
        #             stream = QTextStream(file)
        #             loaded_style = stream.readAll()
        #             file.close()
        #     else:
        #         logger.warning(f"Stylesheet file not found via fallback: {STYLE_FILE}.")
        # except Exception as e:
        #     logger.exception(f"Error loading stylesheet via fallback: {e}")
        return loaded_style

    def _apply_stylesheet(self):
        """Applies the base styles and loads the main stylesheet from Qt resources."""
        base_style = self._compose_base_style()
        # Load from Qt resources
        loaded_style = ""
        resource_path = ":/style.qss" 
        try:
            file = QFile(resource_path)
            if file.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text):
                stream = QTextStream(file)
                loaded_style = stream.readAll()
                file.close()
            else:
                logger.error(f"Could not open resource file: {resource_path}. Error: {file.errorString()}")
        except Exception as e:
             logger.exception(f"Error loading stylesheet from resource {resource_path}: {e}")
        
        final_style = base_style + "\n" + loaded_style
        self.container_widget.setStyleSheet(final_style)
        logger.info("Applied stylesheet from resources.")

    def _create_title_bar(self) -> None:
        """Creates the custom title bar widget."""
        self.title_bar_widget = TitleBar(self)

    def _create_top_frame(self):
        """Creates the top frame containing folder selection controls."""
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

    def _create_action_frame(self) -> None:
        """Creates the action frame containing main action buttons."""
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
        layout.addItem(QSpacerItem(16, 1, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))
        layout.addStretch(1)
        layout.addWidget(self.generate_button)
        layout.addWidget(self.copy_button)
        layout.addWidget(self.save_button)
        layout.addStretch(1)
        layout.addItem(QSpacerItem(16, 1, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))
        layout.addWidget(self.clear_button)

    def _create_file_list_frame(self) -> None:
        """Creates the file list label and view."""
        self.file_list_label = QLabel("Select Files for Context:")
        self.file_list_label.setObjectName("fileListLabel")
        self.file_list_label.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)
        self.file_list_view = FileListView()

    def _create_progress_bar(self):
        """Creates the progress bar used for background tasks."""
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _create_output_textbox(self):
        """Creates the main text edit area for displaying generated context."""
        self.output_textbox = QTextEdit()
        self.output_textbox.setObjectName("outputTextEdit")
        self.output_textbox.setReadOnly(True)
        self.output_textbox.setFont(self.mono_font)
        self.output_textbox.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.output_textbox.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Keyboard shortcuts
        self.select_folder_button.setShortcut(QKeySequence.StandardKey.Open)
        self.generate_button.setShortcut("Ctrl+G")
        self.copy_button.setShortcut(QKeySequence.StandardKey.Copy)
        self.save_button.setShortcut(QKeySequence.StandardKey.Save)
        self.select_all_button.setShortcut(QKeySequence.StandardKey.SelectAll)
        self.deselect_all_button.setShortcut("Ctrl+D")
        self.clear_button.setShortcut("Ctrl+L")
        # Tooltips
        self.select_folder_button.setToolTip("Select the project root folder (Ctrl+O)")
        self.generate_button.setToolTip("Generate context for selected files (Ctrl+G)")
        self.copy_button.setToolTip("Copy generated context to clipboard (Ctrl+C)")
        self.save_button.setToolTip("Save generated context to file (Ctrl+S)")
        self.select_all_button.setToolTip("Select all files (Ctrl+A)")
        self.deselect_all_button.setToolTip("Deselect all files (Ctrl+D)")
        self.clear_button.setToolTip("Clear output and selection (Ctrl+L)")

    def _create_status_bar(self):
        """Creates the status bar area at the bottom, including status and token count."""
        # Create a container widget for the status bar elements
        self.status_bar_widget = QWidget()
        self.status_bar_widget.setObjectName("statusBarWidget")
        status_layout = QHBoxLayout(self.status_bar_widget)
        status_layout.setContentsMargins(8, 4, 8, 4) # Add some padding
        status_layout.setSpacing(10)

        # Original Status Label (Aligned Left)
        self.status_bar_label = QLabel("Ready")
        self.status_bar_label.setObjectName("statusBarLabel")
        self.status_bar_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred) # Let it expand
        status_layout.addWidget(self.status_bar_label, 1) # Give it stretch factor

        # Token and ignored diagnostics area
        metrics_container = QWidget()
        metrics_layout = QHBoxLayout(metrics_container)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setSpacing(10)

        self.ignored_button = QPushButton("Ignored: 0")
        self.ignored_button.setObjectName("ignoredButton")
        self.ignored_button.setFlat(True)
        self.ignored_button.setCursor(Qt.CursorShape.PointingHandCursor)
        metrics_layout.addWidget(self.ignored_button)

        self.token_count_label = QLabel("Est. Tokens: 0")
        self.token_count_label.setObjectName("tokenCountLabel")
        self.token_count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        metrics_layout.addWidget(self.token_count_label)

        status_layout.addWidget(metrics_container, 0)

    # --- Event Handlers (Placeholder - Link these in presenter) --- 
    def resizeEvent(self, event):
        """Handle window resize events."""
        super().resizeEvent(event)
        # Cap output textbox width
        if hasattr(self, 'output_textbox'):
            max_width = int(self.width() * 0.95) # Use 95% of window width
            self.output_textbox.setMaximumWidth(max_width)
            # You might need to trigger a layout update if it doesn't adjust automatically
            # self.output_textbox.updateGeometry()

    def closeEvent(self, event):
        """Handle the window close event."""
        logger.info("Close event triggered.")
        # Add any cleanup logic here if needed before closing
        super().closeEvent(event) 