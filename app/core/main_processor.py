from pathlib import Path
import logging
import time
from typing import List, Optional

from .ignore_handler import IgnoreHandler
from .file_processor import scan_project_structure, filter_selected_files
from .formatter import format_output

logger = logging.getLogger(__name__)

class MainProcessor:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve() # Resolve path early
        if not self.project_path.is_dir():
            msg = f"Project path does not exist or is not a directory: {self.project_path}"
            logger.error(msg)
            raise ValueError(msg)
            
        # Initialize IgnoreHandler immediately and store it
        self.ignore_handler: Optional[IgnoreHandler] = None
        try:
            logger.debug(f"Initializing IgnoreHandler for {self.project_path}")
            self.ignore_handler = IgnoreHandler(self.project_path)
            logger.debug("IgnoreHandler initialized.")
        except Exception as e:
            msg = f"Failed to initialize IgnoreHandler: {e}"
            logger.exception(msg)
            # We can let this error propagate or handle it depending on desired UI behavior
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
            all_paths = scan_project_structure(self.project_path)
            scan_time = time.time() - start_time
            logger.info(f"Scan phase completed in {scan_time:.2f} seconds. Found {len(all_paths)} items.")
            return all_paths
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
            # 1. Filter the selected paths using full ignores and binary check
            logger.debug("Filtering selected files...")
            filtered_files = filter_selected_files(
                self.project_path, selected_relative_paths, self.ignore_handler
            )
            logger.info(f"Filtered selection down to {len(filtered_files)} files for content generation.")

            # 2. Format the output
            logger.debug("Formatting output...")
            formatted_output = format_output(self.project_path, filtered_files)
            logger.debug("Output formatted.")

            generate_time = time.time() - start_time
            logger.info(f"Generate phase completed in {generate_time:.2f} seconds.")
            return formatted_output

        except Exception as e:
            logger.exception("Error during generate phase")
            raise RuntimeError(f"Failed to generate context: {e}") from e 