"""ContextService: Core service for scanning, filtering, and generating project context."""
from __future__ import annotations

from collections import deque
import logging
import os
from pathlib import Path
from typing import Dict

from concurrent.futures import Future, TimeoutError, as_completed

from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

from app.core.formatter import format_output
from app.core.ignore_handler import IgnoreHandler
from app.services.mtime_cache import MTimeCache
from app.services.thread_pool import MAX_WORKERS, SHARED_POOL
from app.utils.file_utils import is_binary_file
from app.utils.token_estimator import estimate_file_tokens

logger = logging.getLogger(__name__)


class ContextService:
    """Scan a project directory, honour ignore rules, and format results."""

    _handler_cache: Dict[Path, IgnoreHandler] = {}

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.cache = MTimeCache()

    def _get_ignore_handler(self, directory: Path) -> IgnoreHandler:
        handler = self._handler_cache.get(directory)
        if handler is None:
            handler = IgnoreHandler(directory)
            self._handler_cache[directory] = handler
        return handler

    def scan(self, force: bool = False) -> tuple[list[Path], list[Path]]:
        handler = self._get_ignore_handler(self.project_root)
        cached_mtimes = self.cache.load(self.project_root)

        all_relative_paths: list[Path] = self.walk_all_files(self.project_root)
        all_relative_paths.sort()

        current_mtimes = self.get_current_mtimes(self.project_root, all_relative_paths)

        if not force and cached_mtimes:
            old_mtimes, cached_files = cached_mtimes
            cached_paths = [Path(path) for path in cached_files]
            if not self.should_regenerate(current_mtimes, old_mtimes):
                logger.info("Cache hit for %s. Using cached file list.", self.project_root)
                included_cached: list[Path] = []
                ignored_cached: list[Path] = []
                for path in cached_paths:
                    if handler.is_ignored(self.project_root / path):
                        ignored_cached.append(path)
                    else:
                        included_cached.append(path)
                return included_cached, ignored_cached
            logger.info("Cache miss or invalid for %s. Recalculating files.", self.project_root)
        else:
            logger.info("Cache not found or force=True for %s. Calculating files.", self.project_root)

        included_files: list[Path] = []
        ignored_files: list[Path] = []
        for path in all_relative_paths:
            target = self.project_root / path
            if handler.is_ignored(target):
                ignored_files.append(path)
            else:
                included_files.append(path)

        all_files_str = [p.as_posix() for p in all_relative_paths]
        self.cache.save(self.project_root, current_mtimes, all_files_str)

        return included_files, ignored_files

    def estimate_tokens(self, relative_paths: list[Path]) -> dict[Path, int]:
        token_map: dict[Path, int] = {}
        for rel_path in relative_paths:
            abs_path = self.project_root / rel_path
            try:
                if abs_path.is_file():
                    token_map[rel_path] = estimate_file_tokens(abs_path)
                else:
                    logger.debug("Skipping token estimation for non-file path: %s", rel_path)
                    token_map[rel_path] = 0
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Token estimate failed for %s: %s", rel_path, exc, exc_info=True)
                token_map[rel_path] = 0
        return token_map

    def explain_ignore(self, path: Path):
        handler = self._get_ignore_handler(self.project_root)
        target = path if path.is_absolute() else (self.project_root / path)
        return handler.explain(target)

    def generate(self, selected: list[Path]) -> str:
        included_files, _ = self.scan(force=False)
        all_project_files_for_structure = sorted(set(included_files))

        filtered_paths: list[Path] = []
        for rel_path in selected:
            abs_path = self.project_root / rel_path
            if abs_path.is_file():
                if not is_binary_file(abs_path):
                    filtered_paths.append(rel_path)
                else:
                    logger.info("Selected path identified as binary, skipping: %s", rel_path)
            else:
                logger.warning("Selected path is not a file or doesn't exist, skipping: %s", rel_path)

        token_map = self.estimate_tokens(included_files)

        return format_output(
            self.project_root,
            filtered_paths,
            all_project_files_for_structure,
            file_token_map=token_map,
        )

    @staticmethod
    def get_current_mtimes(root: Path, relative_paths: list[Path]) -> dict[str, float]:
        mtimes: dict[str, float] = {}
        for rel_path in relative_paths:
            abs_path = root / rel_path
            try:
                if abs_path.is_file():
                    mtimes[rel_path.as_posix()] = abs_path.stat().st_mtime
            except FileNotFoundError:
                continue
            except OSError as exc:
                logger.warning("Could not stat file %s: %s", abs_path, exc)
        return mtimes

    @staticmethod
    def should_regenerate(new_mtimes: dict[str, float], old_mtimes: dict[str, float]) -> bool:
        if new_mtimes.keys() != old_mtimes.keys():
            return True
        for path_str, mtime in new_mtimes.items():
            if old_mtimes.get(path_str) != mtime:
                return True
        return False

    @staticmethod
    def walk_and_filter(
        root: Path,
        spec: PathSpec,
        original_root: Path,
        max_workers: int,
    ) -> list[Path]:
        all_relative_paths: list[Path] = []
        queue: deque[Path] = deque([root])
        active_futures: set[Future[tuple[list[Path], list[Path]]]] = set()

        while queue or active_futures:
            while queue and len(active_futures) < max_workers:
                current_dir = queue.popleft()
                future = SHARED_POOL.submit(
                    ContextService._process_directory_entries,
                    current_dir,
                    spec,
                    original_root,
                )
                active_futures.add(future)

            wait_timeout = 0.1 if queue else None
            try:
                for future in as_completed(active_futures, timeout=wait_timeout):
                    try:
                        results, dirs_to_enqueue = future.result()
                        all_relative_paths.extend(results)
                        queue.extend(dirs_to_enqueue)
                    finally:
                        active_futures.remove(future)
            except TimeoutError:
                if active_futures:
                    logger.debug(
                        "Timeout waiting for directory scan results (%d active tasks). Continuing...",
                        len(active_futures),
                    )

        logger.debug("Walk completed. Found %d non-ignored files/dirs relative paths.", len(all_relative_paths))
        return all_relative_paths

    @staticmethod
    def _process_directory_entries(
        directory: Path,
        spec: PathSpec,
        original_root: Path,
    ) -> tuple[list[Path], list[Path]]:
        results: list[Path] = []
        dirs_to_enqueue: list[Path] = []

        try:
            with os.scandir(directory) as iterator:
                for entry in iterator:
                    abs_path = Path(entry.path)
                    try:
                        path_relative_to_original = abs_path.relative_to(original_root)
                    except ValueError:
                        logger.warning("Encountered path outside original root: %s", abs_path)
                        continue

                    rel_str = path_relative_to_original.as_posix()
                    is_dir = entry.is_dir(follow_symlinks=False)

                    if is_dir and spec.match_file(rel_str + "/"):
                        logger.debug("Ignoring directory and contents: %s/", rel_str)
                        continue
                    if spec.match_file(rel_str):
                        logger.debug("Ignoring entry: %s", rel_str)
                        continue

                    if is_dir:
                        dirs_to_enqueue.append(abs_path)
                    elif entry.is_file(follow_symlinks=False):
                        results.append(path_relative_to_original)
        except OSError as exc:
            logger.warning("Could not scan directory %s: %s", directory, exc)
        except Exception:
            logger.exception("Error processing directory entries for %s", directory)

        return results, dirs_to_enqueue

    @staticmethod
    def walk_all_files(root: Path) -> list[Path]:
        allow_all_spec = PathSpec.from_lines(GitWildMatchPattern, [])
        return ContextService.walk_and_filter(root, allow_all_spec, root, MAX_WORKERS)


__all__ = ["ContextService"]
