import logging
from PySide6.QtWidgets import QTextEdit, QPushButton, QLabel, QApplication, QFileDialog, QProgressBar
from PySide6.QtCore import QObject, Slot, Signal, QTimer
from pathlib import Path
from app.ui.workers import GenerateWorker
from app.services.context_service import ContextService
from typing import Optional, List, Any
from app.ui.errors import WorkerError
from app.ui.status_bus import get_status_bus # Import StatusBus access
from app.utils.token_estimator import estimate_text_tokens   # ➋ new import

logger = logging.getLogger(__name__)

DEFAULT_ERROR_DURATION = 5000 # ms

class OutputController(QObject):
    """Controller managing the output text box and related actions like copy/save."""
    output_generated = Signal(str) # Signal to indicate new output is ready (for UI state updates etc.)

    def __init__(self, 
                 output_textbox: QTextEdit, 
                 ctx_service: ContextService,
                 copy_button: QPushButton,
                 save_button: QPushButton,
                 clear_button: QPushButton,
                 main_window=None):
        super().__init__()
        self.output_textbox = output_textbox
        self.ctx_service = ctx_service
        self.main_window = main_window  # For dialogs
        self.generate_worker = None

        # Connect text change to potentially update UI state (via presenter)
        self.output_textbox.textChanged.connect(lambda: self.output_generated.emit(self.output_textbox.toPlainText()))

    def _update_output_textbox(self, result: str, is_error: bool = False):
        self.output_textbox.setPlainText(result)
        self.output_generated.emit(result) # Emit signal when text is updated

    @Slot(list) # Use list for now, refine later if possible
    def generate_context(self, selected_paths: List[Path]) -> None:
        """Initiates the context generation process based on selected file paths."""
        if not selected_paths:
            get_status_bus().error("No files selected to generate context.")
            QTimer.singleShot(DEFAULT_ERROR_DURATION, get_status_bus().reset)
            return
        
        status_msg = f"Generating context for {len(selected_paths)} files..."
        get_status_bus().progress(True, status_msg)
        self._update_output_textbox("")
        self.generate_worker = GenerateWorker(self.ctx_service, selected_paths)
        self.generate_worker.error.connect(self._on_generate_error)
        self.generate_worker.finished.connect(self._on_generate_finished)
        self.generate_worker.start()

    @Slot(str)
    def _on_generate_finished(self, result: str) -> None:
        self._update_output_textbox(result)
        approx_toks = estimate_text_tokens(result)
        status_msg = f"Context generated successfully (≈ {approx_toks:,} tokens)."
        get_status_bus().success(status_msg)
        get_status_bus().progress(False, status_msg)
        self.generate_worker = None
        QTimer.singleShot(DEFAULT_ERROR_DURATION, lambda: get_status_bus().reset() if get_status_bus().success_message_updated else None)

    @Slot(object)
    def _on_generate_error(self, error_obj: Any) -> None:
        if isinstance(error_obj, WorkerError):
            logger.error(f"Generate Worker Error:\n{error_obj.traceback}")
            status_msg = f"Generation Error: {str(error_obj.exception)}"
            get_status_bus().error(status_msg)
        else:
            logger.error(f"Received unexpected error signal type: {type(error_obj)} - {error_obj}")
            status_msg = "An unknown generation error occurred."
            get_status_bus().error(status_msg)
        
        get_status_bus().progress(False, status_msg)
        self.generate_worker = None
        QTimer.singleShot(DEFAULT_ERROR_DURATION, lambda: get_status_bus().reset() if get_status_bus().error_message_updated else None)

    @Slot()
    def copy_to_clipboard(self) -> None:
        """Copies the content of the output text box to the system clipboard."""
        content = self.output_textbox.toPlainText()
        if content:
            try:
                clipboard = QApplication.clipboard()
                clipboard.setText(content)
                approx_toks = estimate_text_tokens(content)
                status_msg = f"Copied ≈ {approx_toks:,} tokens to clipboard."
                logger.info(status_msg)
                get_status_bus().success(status_msg)
                QTimer.singleShot(DEFAULT_ERROR_DURATION, get_status_bus().reset)
            except Exception as e:
                logger.exception("Error copying to clipboard using Qt")
                get_status_bus().error(f"Error copying: {e}")
                QTimer.singleShot(DEFAULT_ERROR_DURATION, get_status_bus().reset)
        else:
            get_status_bus().info("Nothing to copy.")
            QTimer.singleShot(DEFAULT_ERROR_DURATION, get_status_bus().reset)

    @Slot()
    def handle_save_request(self) -> None:
        """Handles the request to save the output, using the current project root."""
        project_root = self.ctx_service.project_root if self.ctx_service else None
        content = self.output_textbox.toPlainText()

        if not content:
            get_status_bus().info("Nothing to save.")
            QTimer.singleShot(DEFAULT_ERROR_DURATION, get_status_bus().reset)
            return
            
        default_filename = "llm_context.md"
        if project_root:
            default_filename = project_root.name + "_context.md"
            
        initial_path = str(project_root / default_filename if project_root else default_filename)

        file_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "Save Context As",
            initial_path,
            "Markdown files (*.md);;Text files (*.txt);;All files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                status_msg = f"Saved to {Path(file_path).name}"
                logger.info(f"Content saved to file: {file_path}")
                get_status_bus().success(status_msg)
                QTimer.singleShot(DEFAULT_ERROR_DURATION, get_status_bus().reset)
            except (OSError, IOError) as e:
                logger.exception("Error saving to file")
                get_status_bus().error(f"Error saving file: {e}")
                QTimer.singleShot(DEFAULT_ERROR_DURATION, get_status_bus().reset)
        else:
            logger.info("Save file operation cancelled.")
            get_status_bus().info("Save cancelled.")
            QTimer.singleShot(DEFAULT_ERROR_DURATION, get_status_bus().reset)

    @Slot()
    def clear_output(self) -> None:
        """Clears the output text box."""
        if self.output_textbox.toPlainText():
            self.output_textbox.clear()
            get_status_bus().info("Output cleared.")
            QTimer.singleShot(DEFAULT_ERROR_DURATION, get_status_bus().reset)
        else:
            get_status_bus().reset()
        logger.info("Output text box cleared.") 