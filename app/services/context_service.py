"""
ContextService: Core service for scanning, filtering, and generating project context.
Handles ignore rules, caching, and parallel directory walking.
Public API: ContextService.scan(), ContextService.generate().
"""
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Callable, Any, Type, Iterator
from pathspec import PathSpec
import logging
from concurrent.futures import ThreadPoolExecutor, Future, as_completed, TimeoutError
from os import scandir, DirEntry
import os

from app.core.ignore_handler import IgnoreHandler
from app.core.formatter import format_output
from app.utils.file_utils import is_binary_file
from app.services.mtime_cache import MTimeCache
from app.services.thread_pool import SHARED_POOL, MAX_WORKERS # Import MAX_WORKERS
from app.utils.token_estimator import estimate_file_tokens
from pathspec.patterns import GitWildMatchPattern

logger = logging.getLogger(__name__)

class ContextService:
    """
    Core service responsible for scanning projects, managing file context,
    handling ignore rules, and generating the final formatted output.

    It utilizes an MTimeCache for performance, an IgnoreHandler for filtering,
    and a shared ThreadPoolExecutor for parallel directory walking.

    Attributes:
        project_root (Path): The root directory of the project being analyzed.
        cache (MTimeCache): Instance of the modification time cache.
    """
    # Caches loaded handlers per project root to avoid redundant file reads
    _handler_cache: Dict[Path, IgnoreHandler] = {}

    def __init__(self, project_root: Path) -> None:
        """Initializes the ContextService with the project root directory."""
        self.project_root = project_root
        self.cache = MTimeCache()

    def _get_ignore_handler(self, directory: Path) -> IgnoreHandler:
        """Gets or creates an IgnoreHandler for the given directory's project root."""
        if directory not in self._handler_cache:
            self._handler_cache[directory] = IgnoreHandler(directory)
        return self._handler_cache[directory]

    def scan(self, force: bool = False) -> tuple[list[Path], list[Path]]:
        """
        Scans the project directory for files, respecting ignore rules and using
        an mtime cache to optimize subsequent scans.

        Args:
            force: If True, bypasses the cache and performs a full rescan.

        Returns:
            A tuple containing two lists of relative Paths:
            (included_files, ignored_files)
        """
        handler = self._get_ignore_handler(self.project_root)
        cached_mtimes = self.cache.load(self.project_root)

        # Phase A: walk every file (allow-all) so ignored paths are still discovered
        all_relative_paths: List[Path] = ContextService.walk_all_files(self.project_root)

        # Normalize ordering for deterministic behaviour
        all_relative_paths.sort()

        # Get mtimes for the files found by the walk
        current_mtimes = self.get_current_mtimes(self.project_root, all_relative_paths)

        # get_current_mtimes already returns Dict[str, float] with posix paths as keys
        current_mtimes_str: Dict[str, float] = current_mtimes

        # Check cache validity
        if not force and cached_mtimes:
            old_mtimes_str, cached_files_str = cached_mtimes
            # Convert cached file strings back to Paths relative to project_root
            cached_paths = [Path(p) for p in cached_files_str]
            # Compare mtimes
            if not self.should_regenerate(current_mtimes_str, old_mtimes_str):
                logger.info(f"Cache hit for {self.project_root}. Using cached file list.")
                # Separate cached paths into included and ignored based on current spec
                included_cached: list[Path] = []
                ignored_cached: list[Path] = []
                for path in cached_paths:
                    if handler.is_ignored(self.project_root / path):
                        ignored_cached.append(path)
                    else:
                        included_cached.append(path)
                return included_cached, ignored_cached
            else:
                logger.info(f"Cache miss or invalid for {self.project_root}. Recalculating files.")
        else:
            logger.info(f"Cache not found or force=True for {self.project_root}. Calculating files.")

        # If cache miss/invalid/forced, filter the freshly walked paths
        included_files = []
        ignored_files = []
        for path in all_relative_paths:
            if handler.is_ignored(self.project_root / path):
                ignored_files.append(path)
            else:
                included_files.append(path)

        # Save the new state to cache (mtimes and the list of *all* relative paths)
        all_files_str = [p.as_posix() for p in all_relative_paths]
        self.cache.save(self.project_root, current_mtimes_str, all_files_str)

        return included_files, ignored_files

    def estimate_tokens(self, relative_paths: list[Path]) -> dict[Path, int]:
        """Estimate tokens for a collection of project-relative paths."""
        token_map: dict[Path, int] = {}
        for rel_path in relative_paths:
            abs_path = self.project_root / rel_path
            try:
                if abs_path.is_file():
                    token_map[rel_path] = estimate_file_tokens(abs_path)
                else:
                    logger.debug("Skipping token estimation for non-file path: %s", rel_path)
                    token_map[rel_path] = 0
            except Exception as exc:
                logger.warning("Token estimate failed for %s: %s", rel_path, exc, exc_info=True)
                token_map[rel_path] = 0
        return token_map

    def explain_ignore(self, path: Path):
        handler = self._get_ignore_handler(self.project_root)
        target = path if path.is_absolute() else (self.project_root / path)
        return handler.explain(target)

    def generate(self, selected: list[Path]) -> str:
        """
        Generates the final formatted context string for the selected files.

        It first ensures the file list is up-to-date by calling `scan()`. 
        Then, it filters the user-selected list to include only valid, non-binary files.
        Finally, it calls the `format_output` utility to create the structured output.

        Args:
            selected: A list of relative file paths selected by the user in the UI.

        Returns:
            A formatted string containing the project structure and file contents.
        """
        # Use only included files for the structure display
        included_files, ignored_files = self.scan(force=False)
        all_project_files_for_structure = sorted(list(set(included_files)))

        # Filter the 'selected' list passed in ONLY for essential checks
        filtered_paths: list[Path] = []
        for p in selected: # 'selected' comes directly from UI checks
            abs_path = self.project_root / p
            # Condition: Path must be a file and must not be considered binary.
            # The is_binary_file check now incorporates the extension fast-path.
            # We trust the UI selection regarding ignores (UI disables ignored file checkboxes).
            if abs_path.is_file():
                if not is_binary_file(abs_path): # Use the enhanced check
                    filtered_paths.append(p)
                else:
                    logger.info(f"Selected path identified as binary, skipping: {p}")
            elif not abs_path.is_file():
                 logger.warning(f"Selected path is not a file or doesn't exist, skipping: {p}")

        # Pass the filtered UI selection and the full file list for structure
        # Ensure format_output receives lists of Paths
        token_map = self.estimate_tokens(included_files)

        output = format_output(
            self.project_root,
            filtered_paths,
            all_project_files_for_structure,
            file_token_map=token_map,
        )
        return output

    @staticmethod
    def get_current_mtimes(root: Path, relative_paths: list[Path]) -> dict[str, float]:
        """
        Gets the modification times for a list of files relative to a root.

        Args:
            root: The absolute root path.
            relative_paths: A list of file paths relative to the root.

        Returns:
            A dictionary mapping relative path strings (posix format) to mtime floats.
        """
        mtimes = {}
        for rel_path in relative_paths:
            try:
                abs_path = root / rel_path
                if abs_path.is_file():
                    mtimes[rel_path.as_posix()] = abs_path.stat().st_mtime
            except FileNotFoundError:
                pass # Ignore files that disappeared between walk and stat
            except OSError as e:
                logger.warning(f"Could not stat file {abs_path}: {e}")
        return mtimes

    @staticmethod
    def should_regenerate(new_mtimes: dict[str, float], old_mtimes: dict[str, float]) -> bool:
        """
        Compares two sets of modification times to determine if regeneration is needed.

        Args:
            new_mtimes: The current modification times.
            old_mtimes: The cached modification times.

        Returns:
            True if the file sets differ or any mtime has changed, False otherwise.
        """
        # Check if the set of paths has changed
        if new_mtimes.keys() != old_mtimes.keys():
            return True
        # Check if any mtime for the same path has changed
        for path_str, mtime in new_mtimes.items():
            if old_mtimes.get(path_str) != mtime:
                return True
        # If keys are the same and no mtimes differ, cache is valid
        return False

    # Note: Consider adding Progress reporting via callback
    @staticmethod
    def walk_and_filter(
        root: Path,
        spec: PathSpec,
        original_root: Path,
        max_workers: int
    ) -> list[Path]:
        """
        (Static) Walks a directory tree using a thread pool, returning relative paths.

        This method performs a parallel walk starting from `root`. It uses the
        provided `pathspec` to filter out ignored files/directories during the walk.
        It submits directory processing tasks to the shared thread pool.

        Args:
            root: The absolute path to start the walk from.
            spec: The `pathspec.PathSpec` object used for filtering.
            original_root: The absolute path of the project root, used for calculating relative paths.
            max_workers: The maximum number of worker threads to use.

        Returns:
            A list of relative Paths (relative to `original_root`) of the files/
            directories found that were NOT ignored by the spec.
        """
        all_relative_paths: List[Path] = [] 
        queue: List[Path] = [root] # Queue stores absolute paths

        pool = SHARED_POOL
        active_futures: set[Future[Tuple[List[Path], List[Path]]]] = set()

        while queue or active_futures:
            # Submit new tasks from the queue if the pool has capacity
            while queue and len(active_futures) < max_workers:
                current_dir = queue.pop(0)
                try:
                    # Iterate directly over the scandir iterator
                    dir_iterator = os.scandir(current_dir)
                    # Submit processing for the iterator directly
                    # Note: _process_directory_entries needs to handle the iterator
                    future = pool.submit(ContextService._process_directory_entries, dir_iterator, spec, original_root)
                    active_futures.add(future)
                except OSError as e:
                    logger.warning(f"Could not scan directory: {current_dir}, skipping. Error: {e}")
                    continue

            # Process completed futures
            wait_timeout = 0.1 if queue else None 
            
            completed_futures: set[Future[Tuple[List[Path], List[Path]]]] = set()
            try:
                for future in as_completed(active_futures, timeout=wait_timeout):
                    try:
                        results, dirs_to_enqueue = future.result()
                        all_relative_paths.extend(results)
                        queue.extend(dirs_to_enqueue) # Add newly found dirs to the main queue
                        completed_futures.add(future)
                    except Exception as e:
                        logger.exception(f"Error processing directory results for future: {future}: {e}")
                        completed_futures.add(future) # Mark as completed even if error
            except TimeoutError:
                # Log a warning if no futures complete within the timeout
                if active_futures: # Only log if we were actually waiting for something
                    logger.warning(f"Timeout waiting for directory scan results ({len(active_futures)} active tasks). Continuing...")
                # Continue loop to check queue/submit more
                pass

            # Remove completed futures from the active set
            active_futures -= completed_futures

        logger.debug(f"Walk completed. Found {len(all_relative_paths)} non-ignored files/dirs relative paths.")
        return all_relative_paths

    @staticmethod
    def _process_directory_entries(dir_iterator: Iterator[os.DirEntry], spec: PathSpec, original_root: Path) -> Tuple[List[Path], List[Path]]:
        """
        (Static) Processes entries from a directory iterator, filtering based on spec.

        Designed to be run in a worker thread. Iterates through directory entries,
        checks ignore spec, and categorizes into files to include or directories
        to enqueue for further scanning.

        Args:
            dir_iterator: An iterator yielding `os.DirEntry` objects (from `os.scandir`).
            spec: The `pathspec.PathSpec` for filtering.
            original_root: The project root path for calculating relative paths.

        Returns:
            A tuple: (list_of_included_relative_file_paths, list_of_absolute_dir_paths_to_enqueue)
        """
        results = []
        dirs_to_enqueue = []
        for entry in dir_iterator:
            try:
                abs_path = Path(entry.path)
                path_relative_to_original = abs_path.relative_to(original_root)
                rel_str = path_relative_to_original.as_posix()

                # Store is_dir result to avoid redundant checks
                is_dir = entry.is_dir(follow_symlinks=False)

                # Check if directory *itself* should be ignored
                if is_dir and spec.match_file(rel_str + '/'):
                    logger.debug(f"Ignoring directory and contents: {rel_str}/")
                    continue # Skip this directory entirely

                # Check if file/dir should be ignored based on its own path
                if spec.match_file(rel_str):
                   logger.debug(f"Ignoring entry: {rel_str}")
                   continue # Ignore this specific entry

                if is_dir:
                    dirs_to_enqueue.append(abs_path)
                # Only check is_file if it wasn't a directory
                elif entry.is_file(follow_symlinks=False):
                    results.append(path_relative_to_original)
                # Ignore other types (symlinks not followed etc)

            except (OSError, ValueError) as e:
                logger.warning(f"Error processing entry {entry.path}: {e}")
                continue # Ignore entry on error
        return results, dirs_to_enqueue

    @staticmethod
    def walk_all_files(root: Path) -> list[Path]:
        """
        (Static) Walks a directory tree and returns all found files without filtering.

        Useful for getting a complete list of files for structure display,
        ignoring any .gitignore or .llmignore rules.

        Args:
            root: The directory root to walk.

        Returns:
            A list of relative Paths of all files found under the root.
        """
        # Allow-all spec (no patterns)
        allow_all_spec = PathSpec.from_lines(GitWildMatchPattern, [])
        # Leverage shared walker to enumerate every file
        return ContextService.walk_and_filter(root, allow_all_spec, root, MAX_WORKERS)