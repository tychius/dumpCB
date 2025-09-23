import logging
from typing import Optional, List, Any
from pathlib import Path
from PySide6.QtWidgets import QPushButton, QLabel, QFileDialog, QProgressBar
from PySide6.QtCore import QObject, Slot, Signal, QTimer
from app.services.context_service import ContextService
from app.ui.workers import ScanWorker
from app.ui.components.file_list_view import FileListView
from app.ui.errors import WorkerError
from app.ui.status_bus import get_status_bus # Import StatusBus access

logger = logging.getLogger(__name__)

DEFAULT_ERROR_DURATION = 5000 # ms

class FileSelectionController(QObject):
    """Controller managing folder selection, file scanning, and file list view interactions."""
    # This signal remains useful for updating the UI list itself
    scan_results_ready = Signal(list, list) # included, ignored

    def __init__(self, 
                 select_folder_button: QPushButton,
                 folder_label: QLabel,
                 file_list_view: FileListView,
                 ctx_service: ContextService,
                 progress_bar: QProgressBar,
                 main_window=None):
        super().__init__()
        self.select_folder_button = select_folder_button
        self.folder_label = folder_label
        self.file_list_view = file_list_view
        self.ctx_service = ctx_service
        self.main_window = main_window  # For status updates, etc.
        self.selected_folder_path: Optional[Path] = None
        self.all_scanned_paths: List[Path] = []
        self.scan_worker = None
        self.progress_bar = progress_bar
        self.select_folder_button.clicked.connect(self.on_select_folder)
        # Connect the new signal from FileListView to a new slot
        self.file_list_view.total_token_estimate_changed.connect(self._on_token_estimate_changed)
        # Progress bar visibility now handled via StatusBus listener

    @Slot()
    def on_select_folder(self) -> None:
        """Handles the folder selection dialog and initiates the file scanning process."""
        dir_path = QFileDialog.getExistingDirectory(
            self.main_window,
            "Select Project Root Folder",
            str(self.selected_folder_path or Path.home())
        )
        if dir_path:
            self.clear_all()
            self.selected_folder_path = Path(dir_path)
            if self.selected_folder_path:
                self.ctx_service.project_root = self.selected_folder_path
            self.folder_label.setText(f"Scanning: {dir_path}")
            get_status_bus().progress(True, f"Scanning {dir_path}...") # Start progress
            self.scan_worker = ScanWorker(self.ctx_service, force=True)
            self.scan_worker.error.connect(self._on_scan_error)
            self.scan_worker.finished.connect(self._on_scan_finished)
            self.scan_worker.start()
        else:
            get_status_bus().info("Folder selection cancelled.")

    @Slot(object)
    def _on_scan_finished(self, payload: object) -> None:
        """
        Slot: receives (included_paths, ignored_paths, token_map) from ScanWorker,
        populates the list view, updates status.
        """
        if not isinstance(payload, tuple) or len(payload) != 3:
            logger.error("Scan worker returned unexpected payload: %s", payload)
            included, ignored, token_map = [], [], {}
        else:
            included, ignored, token_map = payload

        # FileListView expects List[Tuple[Path, int]]
        # Only include non-ignored files in the left panel
        file_data = [(p, token_map.get(p, 0)) for p in included]

        self.selected_folder_path = self.ctx_service.project_root
        self.folder_label.setText(str(self.selected_folder_path))
        self.all_scanned_paths = [p for p, _ in file_data]

        self.file_list_view.populate(
            file_data,
            checked_paths=set(included),
            ignored_paths=set(ignored),
        )

        status_msg = f"Scan complete: {len(included)} files discovered, {len(ignored)} ignored."
        get_status_bus().success(status_msg)
        get_status_bus().progress(False, status_msg)
        self.scan_results_ready.emit(included, ignored)
        self.scan_worker = None

    @Slot(int)
    def _on_token_estimate_changed(self, total_tokens: int) -> None:
        """Token estimate changed - handled by WindowPresenter now."""
        # Token count display is now handled by WindowPresenter._update_token_estimate
        # This avoids duplicate token count displays in both status bar and token count label
        pass

    @Slot(object)
    def _on_scan_error(self, error_obj: Any) -> None:
        # Check if the received object is our WorkerError
        if isinstance(error_obj, WorkerError):
            logger.error(f"Scan Worker Error:\n{error_obj.traceback}")
            status_msg = f"Scan Error: {str(error_obj.exception)}"
            get_status_bus().error(status_msg)
        else:
            # Fallback for unexpected error types
            logger.error(f"Received unexpected error signal type: {type(error_obj)} - {error_obj}")
            status_msg = "An unknown scan error occurred."
            get_status_bus().error(status_msg)
        
        get_status_bus().progress(False, status_msg) # Stop progress on error
        self.scan_worker = None

        # Optionally reset to "Ready" after a delay
        QTimer.singleShot(DEFAULT_ERROR_DURATION, lambda: get_status_bus().reset() if get_status_bus().error_message_updated else None)

    @Slot()
    def clear_all(self) -> None:
        """Clears the folder label, file list, and output text."""
        logger.info("Clearing selection and output.")
        self.selected_folder_path = None
        self.folder_label.setText("No folder selected")
        # self.file_list_view.clear_list() # Removed: populate sets a new model, clearing the old one.
        # Reset status by emitting the info signal
        get_status_bus().info_message_updated.emit("Ready")

    @Slot()
    def clear_selection(self) -> None:
        """Clears only the file selection, keeping the folder."""
        logger.info("Clearing file selection.")
        if self.file_list_view.model:
            self.file_list_view.set_selection_state(False)
        get_status_bus().info("File selection cleared.")

    @Slot()
    def _select_all_files(self) -> None:
        logger.info("Selecting all valid files.")
        self.file_list_view.set_selection_state(True)

    @Slot()
    def _deselect_all_files(self) -> None:
        logger.info("Deselecting all files.")
        self.file_list_view.set_selection_state(False)

    def get_selected_paths(self) -> list[Path]:
        """Returns a list of currently selected file paths from the view."""
        return self.file_list_view.get_selected() 