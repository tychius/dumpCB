"""Formatting helpers for turning scan results into Markdown."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

from app.utils.file_utils import get_language_identifier, read_file_content
from app.utils.token_estimator import estimate_file_tokens

logger = logging.getLogger(__name__)

_FILE_ICON_MAP = {
    "🐍": {".py", ".pyw"},
    "⚡": {".js", ".ts", ".jsx", ".tsx", ".sh", ".bat", ".ps1"},
    "🌐": {".html", ".htm"},
    "🎨": {".css", ".scss", ".sass"},
    "⚙️": {".json", ".yaml", ".yml", ".toml"},
    "📝": {".md", ".rst", ".txt"},
    "🗄️": {".sql"},
    "🐳": {".dockerfile", ".dockerignore"},
}

_SPECIAL_ICON_NAMES = {
    "dockerfile": "🐳",
    "docker-compose.yml": "🐳",
}


def _get_file_icon(path: Path) -> str:
    suffix = path.suffix.lower()
    for icon, extensions in _FILE_ICON_MAP.items():
        if suffix in extensions:
            return icon
    return _SPECIAL_ICON_NAMES.get(path.name.lower(), "📄")


def _build_directory_tree(file_data: List[tuple[Path, int]], selected_files: Set[Path]) -> Dict[str, dict]:
    tree: Dict[str, dict] = {}
    for path, tokens in file_data:
        parts = path.parts
        current = tree
        for index, part in enumerate(parts):
            is_file = index == len(parts) - 1
            current.setdefault(part, {
                "children": {},
                "is_file": is_file,
                "path": Path(*parts[: index + 1]),
                "tokens": tokens if is_file else 0,
                "selected": path in selected_files if is_file else False,
            })
            current = current[part]["children"]
    return tree


def _format_tree_recursive(tree: Dict[str, dict], prefix: str = "") -> List[str]:
    lines: List[str] = []
    items = list(tree.items())
    for index, (name, data) in enumerate(items):
        is_last = index == len(items) - 1
        connector = "└── " if is_last else "├── "
        if data["is_file"]:
            icon = _get_file_icon(data["path"])
            status = "✓ " if data["selected"] else "  "
            tokens_str = f"({data['tokens']:,} tokens)" if data["tokens"] > 0 else ""
            lines.append(f"{prefix}{connector}{status}{icon} {name} {tokens_str}".rstrip())
            continue

        lines.append(f"{prefix}{connector}📁 {name}/")
        extension = "    " if is_last else "│   "
        lines.extend(_format_tree_recursive(data["children"], prefix + extension))
    return lines


def format_enhanced_project_structure(
    all_files: List[Path],
    selected_files: List[Path],
    project_root: Path,
    file_token_map: Optional[Dict[Path, int]] = None,
) -> str:
    structure_lines = ["Enhanced Project Structure:", "============================="]
    if not all_files:
        structure_lines.append("(No relevant files found)")
        return "\n".join(structure_lines) + "\n"

    file_data: List[tuple[Path, int]] = []
    selected_set = set(selected_files)
    total_selected_tokens = 0
    total_files_tokens = 0

    for path in sorted(all_files):
        abs_path = project_root.resolve() / path
        try:
            tokens = (
                file_token_map[path]
                if file_token_map is not None and path in file_token_map
                else estimate_file_tokens(abs_path)
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Token estimate failed for %s: %s", path, exc, exc_info=True)
            tokens = 0
        file_data.append((path, tokens))
        total_files_tokens += tokens
        if path in selected_set:
            total_selected_tokens += tokens

    tree = _build_directory_tree(file_data, selected_set)
    tree_lines = _format_tree_recursive(tree)
    structure_lines.extend(tree_lines)

    structure_lines.append("")
    structure_lines.append("📊 Summary:")
    structure_lines.append(f"   Total Files: {len(all_files)}")
    structure_lines.append(f"   Selected for Content: {len(selected_files)}")
    structure_lines.append(f"   Total Estimated Tokens: {total_files_tokens:,}")
    structure_lines.append(f"   Selected Files Tokens: {total_selected_tokens:,}")
    structure_lines.append("")
    return "\n".join(structure_lines)


def format_architectural_overview(project_root: Path, all_files: List[Path]) -> str:
    overview_lines = ["Architectural Overview:", "======================"]

    py_files = [f for f in all_files if f.suffix == ".py"]
    js_files = [f for f in all_files if f.suffix in {".js", ".ts", ".jsx", ".tsx"}]
    config_files = [f for f in all_files if f.suffix in {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"}]
    doc_files = [f for f in all_files if f.suffix in {".md", ".rst", ".txt"}]

    technologies = []
    if py_files:
        technologies.append("Python")
    if js_files:
        technologies.append("JavaScript/TypeScript")
    if any("requirements.txt" in str(f) or "pyproject.toml" in str(f) for f in all_files):
        technologies.append("pip/Poetry")
    if any("package.json" in str(f) for f in all_files):
        technologies.append("npm/Node.js")
    if any("dockerfile" in str(f).lower() for f in all_files):
        technologies.append("Docker")

    if technologies:
        overview_lines.append(f"🛠️  Primary Technologies: {', '.join(technologies)}")

    overview_lines.append("")
    overview_lines.append("📁 Project Components:")
    if py_files:
        overview_lines.append(f"   • Python modules: {len(py_files)} files")
    if js_files:
        overview_lines.append(f"   • JavaScript/TypeScript: {len(js_files)} files")
    if config_files:
        overview_lines.append(f"   • Configuration files: {len(config_files)} files")
    if doc_files:
        overview_lines.append(f"   • Documentation: {len(doc_files)} files")

    overview_lines.append("")
    overview_lines.append("🏗️  Architecture Characteristics:")
    has_ui = any("ui" in str(f) or "frontend" in str(f) or "web" in str(f) for f in all_files)
    has_api = any("api" in str(f) or "server" in str(f) or "backend" in str(f) for f in all_files)
    has_tests = any("test" in str(f) for f in all_files)
    has_docs = bool(doc_files)
    if has_ui and has_api:
        overview_lines.append("   • Full-stack application (UI + API)")
    elif has_ui:
        overview_lines.append("   • Frontend/UI focused application")
    elif has_api:
        overview_lines.append("   • Backend/API focused application")
    else:
        overview_lines.append("   • Library or utility project")
    if has_tests:
        overview_lines.append("   • Includes test suite")
    if has_docs:
        overview_lines.append("   • Well-documented codebase")

    entry_points = [
        f
        for f in all_files
        if f.name in {"main.py", "app.py", "run.py", "server.py", "index.js", "index.ts", "app.js", "app.ts"}
    ]
    if entry_points:
        overview_lines.append("")
        overview_lines.append("🚀 Entry Points:")
        overview_lines.extend(f"   • {entry}" for entry in entry_points)

    overview_lines.append("")
    return "\n".join(overview_lines)


def format_file_content(project_root: Path, relative_path: Path) -> str | None:
    absolute_path = project_root.resolve() / relative_path
    result = read_file_content(absolute_path)
    if result is None:
        logger.warning("Skipping file due to read error: %s", relative_path.as_posix())
        return (
            f"--- File: {relative_path.as_posix()} ---\n"
            "```\n[Error reading file content]\n```\n"
        )

    content, encoding = result
    lang_identifier = get_language_identifier(absolute_path)
    header = f"--- File: {relative_path.as_posix()} ---"
    code_block = f"```{lang_identifier}\n{content}\n```"
    if encoding == "latin-1":
        code_block += "\n<!-- encoding fallback: latin‑1 -->"
    return f"{header}\n{code_block}\n"


def format_output(
    project_root: Path,
    relevant_files: List[Path],
    all_files: Optional[List[Path]] | None = None,
    file_token_map: Optional[Dict[Path, int]] = None,
) -> str:
    output_parts: List[str] = []
    all_files = relevant_files if all_files is None else all_files

    output_parts.append(format_architectural_overview(project_root, all_files))
    output_parts.append(
        format_enhanced_project_structure(
            all_files,
            relevant_files,
            project_root,
            file_token_map=file_token_map,
        )
    )

    output_parts.append("File Contents:")
    output_parts.append("==============")
    if not relevant_files:
        output_parts.append("(No relevant files to display content for)")
    else:
        for relative in relevant_files:
            rendered = format_file_content(project_root, relative)
            output_parts.append(
                rendered
                or f"--- File: {relative.as_posix()} ---\n[Failed to read]"
            )

    return "\n".join(output_parts)
