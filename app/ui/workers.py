"""
workers: Defines background worker threads for scanning and context generation.
BaseWorker provides a signal-based interface for async tasks in the UI.
Public API: BaseWorker, ScanWorker, GenerateWorker.
"""
from PySide6.QtCore import QThread, Signal, QObject
from pathlib import Path
from typing import List, Tuple, Any, Dict
from app.services.context_service import ContextService
import logging
import traceback
from app.ui.errors import WorkerError

logger = logging.getLogger(__name__)

class BaseWorker(QThread):
    error = Signal(object)  # Changed from Signal(str) to Signal(object)
    finished = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    def run(self) -> None:
        raise NotImplementedError("Subclasses must implement the run method")

class ScanWorker(BaseWorker):
    finished = Signal(tuple)  # Emits (included_paths, ignored_paths, token_map)

    def __init__(self, ctx_service: ContextService, force: bool = False, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.ctx_service = ctx_service
        self.force = force

    def run(self) -> None:
        try:
            logger.info(f"Starting scan worker for {self.ctx_service.project_root} (force={self.force})")
            included_paths, ignored_paths = self.ctx_service.scan(force=self.force)
            token_map = self.ctx_service.estimate_tokens(included_paths)
            self.finished.emit((included_paths, ignored_paths, token_map))
        except Exception as e:
            logger.exception("Error during file scan")
            tb_str = traceback.format_exc()
            self.error.emit(WorkerError(exception=e, traceback=tb_str))

class GenerateWorker(BaseWorker):
    finished = Signal(str)  # Emits the generated context string

    def __init__(self, ctx_service: ContextService, selected_paths: List[Path], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.ctx_service = ctx_service
        self.selected_paths = selected_paths

    def run(self) -> None:
        try:
            logger.info(f"Starting generate worker for {len(self.selected_paths)} files.")
            result = self.ctx_service.generate(self.selected_paths)
            self.finished.emit(result)
        except Exception as e:
            logger.exception("Error during context generation")
            tb_str = traceback.format_exc()
            self.error.emit(WorkerError(exception=e, traceback=tb_str)) 