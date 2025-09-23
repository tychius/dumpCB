from pathlib import Path
import logging
import time
from typing import List, Optional

from .ignore_handler import IgnoreHandler
from .formatter import format_output
from app.services.context_service import ContextService

logger = logging.getLogger(__name__)

class MainProcessor:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve() # Resolve path early
        if not self.project_path.is_dir():
            msg = f"Project path does not exist or is not a directory: {self.project_path}"
            logger.error(msg)
            raise ValueError(msg)
        self.ctx_service = ContextService(self.project_path)
        self.ignore_handler: Optional[IgnoreHandler] = None
        try:
            logger.debug(f"Initializing IgnoreHandler for {self.project_path}")
            self.ignore_handler = IgnoreHandler(self.project_path)
            logger.debug("IgnoreHandler initialized.")
        except (OSError, IOError) as e:
            msg = f"Failed to initialize IgnoreHandler: {e}"
            logger.exception(msg)
            raise RuntimeError(msg) from e

    def run_scan_phase(self) -> List[Path]:
        """
        Runs the initial scan to discover the project structure.
        
        Returns:
            List[Path]: A list of all discovered relative paths.
        Raises:
            RuntimeError: If scanning fails.
        """
        start_time = time.time()
        logger.info(f"Starting scan phase for: {self.project_path}")
        try:
            included, ignored = self.ctx_service.scan(force=True)
            scan_time = time.time() - start_time
            combined = sorted(set(included + ignored))
            logger.info(f"Scan phase completed in {scan_time:.2f} seconds. Found {len(combined)} items.")
            return combined
        except Exception as e:
            logger.exception("Error during scan phase")
            raise RuntimeError(f"Failed to scan project structure: {e}") from e

    def run_generate_phase(self, selected_relative_paths: List[Path]) -> str:
        """
        Generates the final formatted output based on the user-selected files.

        Args:
            selected_relative_paths: A list of relative paths selected by the user.

        Returns:
            str: The final formatted context string.
        Raises:
            RuntimeError: If generation fails or IgnoreHandler wasn't initialized.
        """
        if self.ignore_handler is None:
            # This should ideally not happen if initialized in __init__
            msg = "IgnoreHandler not initialized before generate phase."
            logger.error(msg)
            raise RuntimeError(msg)
            
        start_time = time.time()
        logger.info(f"Starting generate phase with {len(selected_relative_paths)} selected paths.")
        
        try:
            # The scan for all files might be cached, use force=False
            included, ignored = self.ctx_service.scan(force=False)
            all_project_files = sorted(set(included))
            
            # selected_relative_paths already comes filtered from the UI (ignored items are disabled)
            # Filter selected paths to ensure they are actually files, just in case
            valid_selected_files = [p for p in selected_relative_paths if (self.project_path / p).is_file()]
            logger.info(f"Generating context for {len(valid_selected_files)} valid selected files.")

            # 2. Format the output using the valid selected files and all discovered files
            logger.debug("Formatting output...")
            token_map = self.ctx_service.estimate_tokens(included)

            formatted_output = format_output(
                self.project_path,
                valid_selected_files,
                all_project_files,
                file_token_map=token_map,
            )
            logger.debug("Output formatted.")

            generate_time = time.time() - start_time
            logger.info(f"Generate phase completed in {generate_time:.2f} seconds.")
            return formatted_output

        except Exception as e:
            logger.exception("Error during generate phase")
            raise RuntimeError(f"Failed to generate context: {e}") from e 