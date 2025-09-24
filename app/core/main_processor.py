"""High-level orchestration of scan and generate phases."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import List, Optional

from app.core.formatter import format_output
from app.core.ignore_handler import IgnoreHandler
from app.services.context_service import ContextService

logger = logging.getLogger(__name__)


class MainProcessor:
    """Wrap the ContextService with logging and safety checks."""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        if not self.project_path.is_dir():
            msg = f"Project path does not exist or is not a directory: {self.project_path}"
            logger.error(msg)
            raise ValueError(msg)

        self.ctx_service = ContextService(self.project_path)
        self.ignore_handler: Optional[IgnoreHandler] = None
        try:
            logger.debug("Initializing IgnoreHandler for %s", self.project_path)
            self.ignore_handler = IgnoreHandler(self.project_path)
        except (OSError, IOError) as exc:
            msg = f"Failed to initialize IgnoreHandler: {exc}"
            logger.exception(msg)
            raise RuntimeError(msg) from exc

    def run_scan_phase(self) -> List[Path]:
        start_time = time.time()
        logger.info("Starting scan phase for: %s", self.project_path)
        try:
            included, ignored = self.ctx_service.scan(force=True)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Error during scan phase")
            raise RuntimeError(f"Failed to scan project structure: {exc}") from exc

        scan_time = time.time() - start_time
        combined = sorted(set(included + ignored))
        logger.info(
            "Scan phase completed in %.2f seconds. Found %d items.",
            scan_time,
            len(combined),
        )
        return combined

    def run_generate_phase(self, selected_relative_paths: List[Path]) -> str:
        if self.ignore_handler is None:
            msg = "IgnoreHandler not initialized before generate phase."
            logger.error(msg)
            raise RuntimeError(msg)

        start_time = time.time()
        logger.info("Starting generate phase with %d selected paths.", len(selected_relative_paths))

        try:
            included, _ = self.ctx_service.scan(force=False)
            all_project_files = sorted(set(included))
            valid_selected_files = [
                path for path in selected_relative_paths if (self.project_path / path).is_file()
            ]
            logger.info("Generating context for %d valid selected files.", len(valid_selected_files))

            token_map = self.ctx_service.estimate_tokens(included)
            formatted_output = format_output(
                self.project_path,
                valid_selected_files,
                all_project_files,
                file_token_map=token_map,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Error during generate phase")
            raise RuntimeError(f"Failed to generate context: {exc}") from exc

        generate_time = time.time() - start_time
        logger.info("Generate phase completed in %.2f seconds.", generate_time)
        return formatted_output


__all__ = ["MainProcessor"]
