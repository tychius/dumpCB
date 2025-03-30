from pathlib import Path
import logging
from typing import List
import pathspec

from .ignore_handler import IgnoreHandler
from app.utils.file_utils import is_binary_file
from app.config.constants import ESSENTIAL_DIR_IGNORE_PATTERNS

logger = logging.getLogger(__name__)

def scan_project_structure(project_root: Path) -> List[Path]:
    """
    Recursively scans the project directory structure, respecting only
    essential directory ignore patterns.

    Args:
        project_root: The root directory of the project.

    Returns:
        A sorted list of all found Path objects (files and directories),
        relative to project_root.
    """
    all_paths = []
    absolute_root = project_root.resolve()
    
    # Create a specific pathspec for essential directory ignores only
    # Use GitWildMatchPattern for consistency with IgnoreHandler
    essential_spec = pathspec.PathSpec.from_lines(
        pathspec.patterns.GitWildMatchPattern, ESSENTIAL_DIR_IGNORE_PATTERNS
    )

    logger.info(f"Starting structural scan of: {absolute_root}")
    
    # Walk the directory tree manually to better control directory skipping
    queue = [absolute_root]
    visited_dirs = set()

    while queue:
        current_dir = queue.pop(0)
        
        if current_dir in visited_dirs:
            continue
        visited_dirs.add(current_dir)
        
        try:
            # Check if the current directory itself should be essentially ignored
            # (relative path needed for pathspec)
            relative_dir_str = current_dir.relative_to(absolute_root).as_posix()
            if relative_dir_str and essential_spec.match_file(relative_dir_str + '/'): # Add trailing slash for dir match
                 logger.debug(f"Skipping essential ignored directory: {relative_dir_str}")
                 continue # Don't process or enqueue contents
                 
            for item in current_dir.iterdir():
                try:
                    # Get relative path for storage and checking
                    relative_path = item.relative_to(absolute_root)
                    relative_path_str = relative_path.as_posix()
                    
                    # Add the item to the list regardless of type (initially)
                    all_paths.append(relative_path)
                    
                    # If it's a directory, check if it's essentially ignored before adding to queue
                    if item.is_dir():
                        # Add trailing slash for pathspec directory matching
                        if not essential_spec.match_file(relative_path_str + '/'):
                            if item not in visited_dirs:
                                queue.append(item)
                        else:
                             logger.debug(f"Not queueing essential ignored directory: {relative_path_str}")
                             
                except OSError as e:
                    logger.warning(f"Could not access item {item}: {e}")
                except ValueError:
                     logger.error(f"Could not make path relative: {item} to {absolute_root}")
                     
        except OSError as e:
            logger.warning(f"Could not iterate directory {current_dir}: {e}")
        except Exception as e:
             logger.error(f"Unexpected error processing directory {current_dir}: {e}")

    # Sort the list for consistent output
    all_paths.sort()

    logger.info(f"Structural scan complete. Found {len(all_paths)} items in {project_root}")
    return all_paths


def filter_selected_files(
    project_root: Path,
    selected_paths: List[Path],
    ignore_handler: IgnoreHandler
) -> List[Path]:
    """
    Filters a list of selected relative paths based on full ignore rules
    and binary file checks.

    Args:
        project_root: The absolute path to the project root.
        selected_paths: A list of relative Path objects selected by the user.
        ignore_handler: An initialized IgnoreHandler with all ignore patterns.

    Returns:
        A sorted list of relative Path objects representing the final files
        to include in the output.
    """
    final_relevant_files = []
    absolute_root = project_root.resolve()
    logger.info(f"Filtering {len(selected_paths)} selected items...")

    for relative_path in selected_paths:
        absolute_path = absolute_root / relative_path
        try:
            # Ensure it's actually a file (user might have selected a dir checkbox)
            if not absolute_path.is_file():
                logger.debug(f"Skipping selected item as it's not a file: {relative_path.as_posix()}")
                continue

            # Check 1: Full ignore rules (including .gitignore, .llmignore, defaults)
            if ignore_handler.is_ignored(absolute_path):
                logger.debug(f"Skipping selected file due to ignore rules: {relative_path.as_posix()}")
                continue

            # Check 2: Binary file check
            if is_binary_file(absolute_path):
                logger.debug(f"Skipping selected file as it is binary: {relative_path.as_posix()}")
                continue

            # If all checks pass, add it to the final list
            final_relevant_files.append(relative_path)
            logger.debug(f"Including selected file: {relative_path.as_posix()}")

        except OSError as e:
            logger.warning(f"Could not access selected path {relative_path.as_posix()}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error filtering path {relative_path.as_posix()}: {e}")

    # Sort for consistent final output generation
    final_relevant_files.sort()
    logger.info(f"Filtered down to {len(final_relevant_files)} relevant files for content generation.")
    return final_relevant_files 