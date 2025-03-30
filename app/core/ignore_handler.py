import pathspec
from pathlib import Path
import logging

from app.config.constants import DEFAULT_IGNORE_PATTERNS

logger = logging.getLogger(__name__)

class IgnoreHandler:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.spec = self._load_specs()

    def _load_patterns_from_file(self, file_path: Path) -> list[str]:
        """Loads ignore patterns from a given file (e.g., .gitignore)."""
        patterns = []
        if file_path.is_file():
            try:
                with file_path.open('r', encoding='utf-8', errors='ignore') as f:
                    patterns = f.read().splitlines()
                logger.info(f"Loaded {len(patterns)} patterns from {file_path.name}")
            except OSError as e:
                logger.warning(f"Could not read ignore file {file_path}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error reading {file_path}: {e}")
        return patterns

    def _load_specs(self) -> pathspec.PathSpec:
        """Loads default, .gitignore, and .llmignore patterns."""
        all_patterns = list(DEFAULT_IGNORE_PATTERNS)

        # Load .gitignore
        gitignore_path = self.project_root / ".gitignore"
        all_patterns.extend(self._load_patterns_from_file(gitignore_path))

        # Load .llmignore (these could potentially override/add to .gitignore)
        llmignore_path = self.project_root / ".llmignore"
        all_patterns.extend(self._load_patterns_from_file(llmignore_path))

        # Filter out empty lines and comments
        filtered_patterns = [
            p for p in all_patterns
            if p.strip() and not p.strip().startswith('#')
        ]

        logger.debug(f"Total combined ignore patterns: {len(filtered_patterns)}")
        return pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, filtered_patterns)

    def is_ignored(self, path: Path) -> bool:
        """
        Checks if a given path (relative to project root) should be ignored.

        Args:
            path: The Path object to check.

        Returns:
            True if the path should be ignored, False otherwise.
        """
        try:
            # pathspec expects relative paths, preferably as strings with forward slashes
            relative_path_str = path.relative_to(self.project_root).as_posix()

            # Check against the compiled spec
            is_match = self.spec.match_file(relative_path_str)

            # Also explicitly ignore if it's the root .git directory itself
            # pathspec might not ignore the top-level dir if pattern is just ".git/"
            # depending on how it's called (match_file vs match_directory).
            # This adds robustness.
            if not is_match and relative_path_str == ".git":
                 # Ensure we always ignore the root .git folder if present
                 # We need to check if the original path IS the .git dir
                if path.name == ".git" and path.parent == self.project_root and path.is_dir():
                     logger.debug(f"Explicitly ignoring top-level .git directory: {path}")
                     return True

            if is_match:
                logger.debug(f"Ignoring path: {relative_path_str}")
            return is_match

        except ValueError as e:
            # This can happen if the path is not relative to the project root,
            # which shouldn't occur with correct usage but is good to handle.
            logger.error(f"Path {path} does not seem to be relative to project root {self.project_root}: {e}")
            return True # Treat as ignored if path is outside root
        except Exception as e:
            logger.error(f"Error checking ignore status for {path}: {e}")
            return True # Treat as ignored on error 