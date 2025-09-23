from __future__ import annotations

import pathspec
from pathlib import Path
import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathspec.patterns import GitWildMatchPattern

from app.config.constants import DEFAULT_IGNORE_PATTERNS

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IgnoreRule:
    pattern: str
    source: str
    line: Optional[int] = None

    def display_source(self) -> str:
        if self.line is not None:
            return f"{self.source}:{self.line}"
        return self.source


class IgnoreHandler:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.spec, self._rules, self._rule_specs = self._load_specs()

    def _load_patterns_from_file(self, file_path: Path) -> list[Tuple[str, int]]:
        """Loads ignore patterns and line numbers from a given file (e.g., .gitignore)."""
        patterns: list[Tuple[str, int]] = []
        if file_path.is_file():
            try:
                for idx, raw_line in enumerate(file_path.read_text(encoding='utf-8', errors='ignore').splitlines(), start=1):
                    pattern = raw_line.strip()
                    if pattern and not pattern.startswith('#'):
                        patterns.append((pattern, idx))
                logger.info(f"Loaded {len(patterns)} patterns from {file_path.name}")
            except FileNotFoundError:
                logger.debug(f"Ignore file not found during read: {file_path}")
            except (OSError, UnicodeDecodeError) as e:
                logger.error(f"Error reading ignore file {file_path}: {e}")
            except Exception as e:
                logger.exception(f"Unexpected error reading ignore file {file_path}")
        else:
            logger.debug(f"Ignore file not found: {file_path}")
        return patterns

    def _load_specs(self) -> tuple[pathspec.PathSpec, list[IgnoreRule], list[pathspec.PathSpec]]:
        """Loads default, .gitignore, and .llmignore patterns along with metadata."""
        rules: list[IgnoreRule] = []

        for raw_pattern in DEFAULT_IGNORE_PATTERNS:
            pattern = raw_pattern.strip()
            if pattern and not pattern.startswith('#'):
                rules.append(IgnoreRule(pattern=pattern, source="default"))

        file_sources = [
            (self.project_root / ".gitignore", ".gitignore"),
            (self.project_root / ".llmignore", ".llmignore"),
        ]

        for file_path, source_name in file_sources:
            for pattern, line_no in self._load_patterns_from_file(file_path):
                rules.append(IgnoreRule(pattern=pattern, source=source_name, line=line_no))

        patterns = [rule.pattern for rule in rules]
        logger.debug(f"Total combined ignore patterns: {len(patterns)}")

        spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, patterns)
        rule_specs = [pathspec.PathSpec.from_lines(GitWildMatchPattern, [rule.pattern]) for rule in rules]

        return spec, rules, rule_specs

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
            logger.exception(f"Error checking ignore status for {path}")
            return True # Treat as ignored on error 

    def explain(self, path: Path) -> Optional[IgnoreRule]:
        """Return the first ignore rule that matches the provided path, if any."""
        try:
            abs_path = path if path.is_absolute() else self.project_root / path
            relative_path = abs_path.relative_to(self.project_root)
            rel_str = relative_path.as_posix()
        except ValueError:
            logger.error("Cannot explain ignore for path outside project root: %s", path)
            return None

        # Consider directory-specific matches by appending trailing slash when appropriate
        candidates = [rel_str]
        try:
            if abs_path.is_dir() and not rel_str.endswith('/'):
                candidates.append(rel_str + '/')
        except OSError:
            # If we cannot stat the path (e.g., it was removed), still try trailing slash heuristic
            if not rel_str.endswith('/'):
                candidates.append(rel_str + '/')

        for candidate in candidates:
            for rule_spec, rule in zip(self._rule_specs, self._rules):
                if rule_spec.match_file(candidate):
                    return rule

        return None