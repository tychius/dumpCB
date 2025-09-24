"""Ignore-file handling for the project scanner."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pathspec
from pathspec.patterns import GitWildMatchPattern

from app.config.constants import DEFAULT_IGNORE_PATTERNS

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IgnoreRule:
    pattern: str
    source: str
    line: Optional[int] = None

    def display_source(self) -> str:
        return f"{self.source}:{self.line}" if self.line is not None else self.source


class IgnoreHandler:
    """Compile ignore rules from defaults, .gitignore and .llmignore files."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.spec, self._rules, self._rule_specs = self._load_specs()

    def _load_patterns_from_file(self, file_path: Path) -> list[tuple[str, int]]:
        patterns: list[tuple[str, int]] = []
        if not file_path.is_file():
            logger.debug("Ignore file not found: %s", file_path)
            return patterns

        try:
            contents = file_path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError) as exc:
            logger.error("Error reading ignore file %s: %s", file_path, exc)
            return patterns

        for idx, raw_line in enumerate(contents.splitlines(), start=1):
            pattern = raw_line.strip()
            if pattern and not pattern.startswith("#"):
                patterns.append((pattern, idx))
        logger.info("Loaded %d patterns from %s", len(patterns), file_path.name)
        return patterns

    def _load_specs(self) -> tuple[pathspec.PathSpec, list[IgnoreRule], list[pathspec.PathSpec]]:
        rules: list[IgnoreRule] = []

        for raw_pattern in DEFAULT_IGNORE_PATTERNS:
            pattern = raw_pattern.strip()
            if pattern and not pattern.startswith("#"):
                rules.append(IgnoreRule(pattern=pattern, source="default"))

        file_sources = [
            (self.project_root / ".gitignore", ".gitignore"),
            (self.project_root / ".llmignore", ".llmignore"),
        ]
        for file_path, source_name in file_sources:
            for pattern, line_no in self._load_patterns_from_file(file_path):
                rules.append(IgnoreRule(pattern=pattern, source=source_name, line=line_no))

        patterns = [rule.pattern for rule in rules]
        logger.debug("Total combined ignore patterns: %d", len(patterns))

        spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, patterns)
        rule_specs = [pathspec.PathSpec.from_lines(GitWildMatchPattern, [rule.pattern]) for rule in rules]
        return spec, rules, rule_specs

    def is_ignored(self, path: Path) -> bool:
        """Return ``True`` if the given *path* should be ignored."""
        try:
            relative_path_str = path.relative_to(self.project_root).as_posix()
        except ValueError as exc:
            logger.error(
                "Path %s does not seem to be relative to project root %s: %s",
                path,
                self.project_root,
                exc,
            )
            return True
        except Exception:
            logger.exception("Error computing relative path for %s", path)
            return True

        try:
            is_match = self.spec.match_file(relative_path_str)
        except Exception:
            logger.exception("Error checking ignore status for %s", path)
            return True

        if not is_match and relative_path_str == ".git":
            if path.name == ".git" and path.parent == self.project_root and path.is_dir():
                logger.debug("Explicitly ignoring top-level .git directory: %s", path)
                return True

        if is_match:
            logger.debug("Ignoring path: %s", relative_path_str)
        return is_match

    def explain(self, path: Path) -> Optional[IgnoreRule]:
        """Return the first ignore rule that matches *path*, if any."""
        abs_path = path if path.is_absolute() else self.project_root / path
        try:
            relative_path = abs_path.relative_to(self.project_root)
        except ValueError:
            logger.error("Cannot explain ignore for path outside project root: %s", path)
            return None

        rel_str = relative_path.as_posix()
        candidates = [rel_str]
        if not rel_str.endswith("/"):
            try:
                if abs_path.is_dir():
                    candidates.append(rel_str + "/")
            except OSError:
                candidates.append(rel_str + "/")

        for candidate in candidates:
            for rule_spec, rule in zip(self._rule_specs, self._rules):
                if rule_spec.match_file(candidate):
                    return rule
        return None


__all__ = ["IgnoreHandler", "IgnoreRule"]
