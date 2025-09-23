import logging
from typing import Any, TYPE_CHECKING
from pathlib import Path
from PySide6.QtCore import QObject, Slot, QPropertyAnimation, QEasingCurve, QByteArray, Qt # type: ignore
from PySide6.QtWidgets import QFileDialog, QMessageBox, QLabel, QListWidget, QListWidgetItem, QDialog, QVBoxLayout, QPushButton # type: ignore

from app.services.context_service import ContextService
from app.ui.controllers.file_selection_controller import FileSelectionController
from app.ui.controllers.output_controller import OutputController

# Use forward reference for type hinting to avoid circular import
if TYPE_CHECKING:
    from app.ui.windows.main_window import MainWindow

from app.ui.status_bus import get_status_bus # Import StatusBus access

logger = logging.getLogger(__name__)

class WindowPresenter(QObject):
    """Presenter for the MainWindow, handling logic, state, and controller interactions."""

    def __init__(self, window: "MainWindow", parent: QObject | None = None):
        super().__init__(parent)
        self.window = window
        
        # Initialize services and controllers
        self.ctx_service = ContextService(Path.home()) # Or get from elsewhere if needed
        self._wire_controllers() # Controllers now use StatusBus internally
        
        self._connect_signals()
        self._connect_status_bus()
        self._last_scan_ignored: list[Path] = []
        self.update_ui_state()

    def _wire_controllers(self) -> None:
        """Initializes and wires up the UI controllers."""
        logger.debug("Wiring controllers in presenter...")
        self.file_selection_controller = FileSelectionController(
            select_folder_button=self.window.select_folder_button,
            folder_label=self.window.folder_label,
            file_list_view=self.window.file_list_view,
            ctx_service=self.ctx_service,
            # Pass progress bar ref if controller still needs it, but presenter handles visibility
            progress_bar=self.window.progress_bar, 
            main_window=self.window # Pass window ref if controller needs it directly
        )

        self.output_controller = OutputController(
            output_textbox=self.window.output_textbox,
            copy_button=self.window.copy_button,
            save_button=self.window.save_button,
            clear_button=self.window.clear_button,
            ctx_service=self.ctx_service,
            main_window=self.window # Pass window ref if controller needs it directly
        )
        logger.debug("Controllers wired.")

    def _connect_signals(self) -> None:
        """Connect signals from the window widgets to presenter slots."""
        logger.debug("Connecting window signals to presenter slots...")
        # File Selection related
        # self.window.select_folder_button.clicked.connect(self.file_selection_controller.select_folder) # Controller connects internally
        self.window.file_list_view.selection_changed.connect(self.update_ui_state)
        # Rely on signal with precomputed total; remove duplicate estimation logic
        self.window.file_list_view.total_token_estimate_changed.connect(self._update_token_count_from_signal)
        self.window.file_list_view.ignored_context_requested.connect(self._on_ignored_item_explain)
        self.file_selection_controller.scan_results_ready.connect(self._on_scan_results_ready)
        self.window.ignored_button.clicked.connect(self._on_ignored_button_clicked)
        # self.file_selection_controller.scan_results_ready.connect(self.update_ui_state) # Update state when list is populated
        # Assuming scan_results_ready now emits List[Tuple[Path, int]], connect it
        # If it still emits List[Path], we need to adjust FileSelectionController or ContextService first
        # For now, token update will happen on selection_changed after populate completes

        # Action Buttons
        self.window.select_all_button.clicked.connect(lambda: self.window.file_list_view.set_selection_state(True))
        self.window.deselect_all_button.clicked.connect(lambda: self.window.file_list_view.set_selection_state(False))
        self.window.generate_button.clicked.connect(self._handle_generate_clicked)

        # Output related
        self.window.copy_button.clicked.connect(self.output_controller.copy_to_clipboard) # Controller handles action
        self.window.save_button.clicked.connect(self.output_controller.handle_save_request) # Controller handles action
        self.window.clear_button.clicked.connect(self._handle_clear_all)
        self.output_controller.output_generated.connect(self.update_ui_state) # Update state when output changes

        # Update UI state when text changes in output (e.g., enable clear/copy/save)
        # self.window.output_textbox.textChanged.connect(self.update_ui_state) # Covered by output_generated
        logger.debug("Signal connections complete.")

    def _connect_status_bus(self) -> None:
        """Connect StatusBus signals to presenter slots for UI updates."""
        logger.debug("Connecting StatusBus signals to presenter slots...")
        bus = get_status_bus()
        bus.info_message_updated.connect(self._on_status_info)
        bus.success_message_updated.connect(self._on_status_success)
        bus.error_message_updated.connect(self._on_status_error)
        bus.progress_updated.connect(self._on_status_progress)
        logger.debug("StatusBus connections complete.")

    def update_ui_state(self) -> None:
        """Updates the enable/disable state of UI elements based on application state."""
        # logger.debug("Updating UI state...") # Can be noisy
        has_folder = bool(self.file_selection_controller.selected_folder_path)
        has_files = bool(self.window.file_list_view.get_all_paths())
        has_selection = bool(self.window.file_list_view.get_selected())
        has_output = bool(self.window.output_textbox.toPlainText())

        self.window.select_all_button.setEnabled(has_files)
        self.window.deselect_all_button.setEnabled(has_selection)
        self.window.generate_button.setEnabled(has_selection)
        self.window.copy_button.setEnabled(has_output)
        self.window.save_button.setEnabled(has_output)
        self.window.clear_button.setEnabled(has_output or has_files or has_folder)

    # --- Slots --- 

    @Slot()
    def _handle_generate_clicked(self): # Delegate to controller
        selected_paths = self.window.file_list_view.get_selected()
        # Optionally pass token count or check against a limit here
        self.output_controller.generate_context(selected_paths)

    # Removed duplicate token estimation method; totals come from FileListView

    @Slot(int)
    def _update_token_count_from_signal(self, total_tokens: int) -> None:
        """Updates the token count label directly from the file list view signal."""
        formatted_tokens = f"{total_tokens:,}"
        self.window.token_count_label.setText(f"Est. Tokens: {formatted_tokens}")

    @Slot()
    def _handle_clear_all(self) -> None:
        """Handles the comprehensive clear action."""
        self.output_controller.clear_output()
        self.file_selection_controller.clear_selection()
        self.update_ui_state()

    # --- Status Bus Slots --- 

    def _animate_status_label(self, label: QLabel, message: str, status_type: str):
        """Helper to set text, style, and animate the status label."""
        label.setText(message)
        label.setProperty("status", status_type)
        
        # Ensure opacity property exists if needed, or use stylesheet
        # label.setGraphicsEffect(QGraphicsOpacityEffect(label)) # If needed
        
        # Ensure style is applied before animation
        label.style().unpolish(label)
        label.style().polish(label)

        # Create and configure animation (simple windowOpacity for label)
        self.status_animation = QPropertyAnimation(label, b"windowOpacity")
        self.status_animation.setDuration(120)
        self.status_animation.setStartValue(0.0)
        self.status_animation.setEndValue(1.0)
        self.status_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.status_animation.start()

    @Slot(str)
    def _on_status_info(self, message: str) -> None:
        """Handle info messages from the StatusBus."""
        self._animate_status_label(self.window.status_bar_label, message, "info")
    
    @Slot(str)
    def _on_status_success(self, message: str) -> None:
        """Handle success messages from the StatusBus."""
        self._animate_status_label(self.window.status_bar_label, message, "success")

    @Slot(str)
    def _on_status_error(self, message: str) -> None:
        """Handle error messages from the StatusBus."""
        self._animate_status_label(self.window.status_bar_label, message, "error")

    @Slot(bool, str)
    def _on_status_progress(self, active: bool, message: str = "") -> None:
        """Shows or hides the progress bar based on StatusBus signal."""
        if active:
            self.window.progress_bar.setRange(0, 0) # Indeterminate
            self.window.progress_bar.show()
            # Update status text if message provided, otherwise keep existing
            if message:
                self._on_status_info(message) # Use info style for progress text
        else:
            self.window.progress_bar.hide()
            # Status text (success/error/info) should be set by the final status emit
            # Example: bus.progress(False, "Scan Complete"); bus.success("Scan Complete")
            # We could potentially set the final message here too if provided
            # if message: 
            #    self._on_status_info(message) # Or infer type? 
    
    @Slot(object)
    def _on_ignored_item_explain(self, path: Path) -> None:
        rule = self.ctx_service.explain_ignore(path)
        if rule is None:
            get_status_bus().info(f"No ignore rule matched {path.as_posix()}")
            return

        message = f"{path.as_posix()}\n↳ {rule.display_source()}\n↳ {rule.pattern}"
        get_status_bus().info(message)

    @Slot()
    def _on_ignored_button_clicked(self) -> None:
        if not self._last_scan_ignored:
            get_status_bus().info("No ignored files detected during last scan.")
            return

        dialog = QDialog(self.window)
        dialog.setWindowTitle("Ignored Paths")
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)

        list_widget = QListWidget(dialog)
        for path in self._last_scan_ignored:
            QListWidgetItem(path.as_posix(), list_widget)
        layout.addWidget(list_widget)

        close_button = QPushButton("Close", dialog)
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)

        dialog.resize(420, 360)
        dialog.exec()

    @Slot(list, list)
    def _on_scan_results_ready(self, included: list[Path], ignored: list[Path]) -> None:
        self._last_scan_ignored = sorted(ignored)
        self.window.ignored_button.setText(f"Ignored: {len(ignored)}")
