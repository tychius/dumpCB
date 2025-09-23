from pathlib import Path
from typing import List, Dict, Set, Optional
import logging

from app.utils.file_utils import get_language_identifier, read_file_content
from app.utils.token_estimator import estimate_file_tokens

logger = logging.getLogger(__name__)

def _get_file_icon(path: Path) -> str:
    """Return an appropriate icon for the file type."""
    if path.suffix.lower() in {'.py', '.pyw'}:
        return '🐍'
    elif path.suffix.lower() in {'.js', '.ts', '.jsx', '.tsx'}:
        return '⚡'
    elif path.suffix.lower() in {'.html', '.htm'}:
        return '🌐'
    elif path.suffix.lower() in {'.css', '.scss', '.sass'}:
        return '🎨'
    elif path.suffix.lower() in {'.json', '.yaml', '.yml', '.toml'}:
        return '⚙️'
    elif path.suffix.lower() in {'.md', '.rst', '.txt'}:
        return '📝'
    elif path.suffix.lower() in {'.sql'}:
        return '🗄️'
    elif path.suffix.lower() in {'.sh', '.bat', '.ps1'}:
        return '⚡'
    elif path.suffix.lower() in {'.dockerfile', '.dockerignore'} or path.name.lower() in {'dockerfile', 'docker-compose.yml'}:
        return '🐳'
    else:
        return '📄'

def _build_directory_tree(file_data: List[tuple[Path, int]], selected_files: Set[Path]) -> Dict[str, any]:
    """Build a nested directory structure for display."""
    tree = {}
    
    for path, tokens in file_data:
        parts = path.parts
        current = tree
        
        # Build the nested structure
        for i, part in enumerate(parts):
            if part not in current:
                current[part] = {
                    'children': {},
                    'is_file': i == len(parts) - 1,
                    'path': Path(*parts[:i+1]),
                    'tokens': tokens if i == len(parts) - 1 else 0,
                    'selected': path in selected_files if i == len(parts) - 1 else False
                }
            current = current[part]['children']
    
    return tree

def _format_tree_recursive(tree: Dict[str, any], prefix: str = "", is_root: bool = True) -> List[str]:
    """Recursively format the directory tree into text lines."""
    lines = []
    items = list(tree.items())
    
    for i, (name, data) in enumerate(items):
        is_last = i == len(items) - 1
        
        if data['is_file']:
            # File entry
            icon = _get_file_icon(data['path'])
            status = "✓ " if data['selected'] else "  "
            tokens_str = f"({data['tokens']:,} tokens)" if data['tokens'] > 0 else ""
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{status}{icon} {name} {tokens_str}")
        else:
            # Directory entry
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}📁 {name}/")
            
            # Recurse for children
            extension = "    " if is_last else "│   "
            child_lines = _format_tree_recursive(data['children'], prefix + extension, False)
            lines.extend(child_lines)
    
    return lines

def format_enhanced_project_structure(
    all_files: List[Path],
    selected_files: List[Path],
    project_root: Path,
    file_token_map: Optional[Dict[Path, int]] = None,
) -> str:
    """
    Generate an enhanced project structure with tree view, icons, and token estimates.
    """
    structure_lines = ["Enhanced Project Structure:", "============================="]
    
    if not all_files:
        structure_lines.append("(No relevant files found)")
        return "\n".join(structure_lines) + "\n"
    
    # Get token estimates for all files (prefer provided map when available)
    file_data = []
    selected_set = set(selected_files)
    total_selected_tokens = 0
    total_files_tokens = 0
    
    for path in sorted(all_files):
        try:
            abs_path = project_root.resolve() / path
            if file_token_map is not None and path in file_token_map:
                tokens = file_token_map[path]
            else:
                tokens = estimate_file_tokens(abs_path)
            file_data.append((path, tokens))
            total_files_tokens += tokens
            if path in selected_set:
                total_selected_tokens += tokens
        except Exception as exc:
            logger.warning("Token estimate failed for %s: %s", path, exc, exc_info=True)
            file_data.append((path, 0))
    
    # Build and format the tree
    tree = _build_directory_tree(file_data, selected_set)
    tree_lines = _format_tree_recursive(tree)
    structure_lines.extend(tree_lines)
    
    # Add summary statistics
    structure_lines.append("")
    structure_lines.append(f"📊 Summary:")
    structure_lines.append(f"   Total Files: {len(all_files)}")
    structure_lines.append(f"   Selected for Content: {len(selected_files)}")
    structure_lines.append(f"   Total Estimated Tokens: {total_files_tokens:,}")
    structure_lines.append(f"   Selected Files Tokens: {total_selected_tokens:,}")
    
    structure_lines.append("")  # Add blank line
    return "\n".join(structure_lines)

def format_architectural_overview(project_root: Path, all_files: List[Path]) -> str:
    """
    Generate an architectural overview based on the project structure.
    """
    overview_lines = ["Architectural Overview:", "======================"]
    
    # Analyze file types and structure
    py_files = [f for f in all_files if f.suffix == '.py']
    js_files = [f for f in all_files if f.suffix in {'.js', '.ts', '.jsx', '.tsx'}]
    config_files = [f for f in all_files if f.suffix in {'.json', '.yaml', '.yml', '.toml', '.ini', '.cfg'}]
    doc_files = [f for f in all_files if f.suffix in {'.md', '.rst', '.txt'}]
    
    # Identify main technologies
    technologies = []
    if py_files:
        technologies.append("Python")
    if js_files:
        technologies.append("JavaScript/TypeScript")
    if any('requirements.txt' in str(f) or 'pyproject.toml' in str(f) for f in all_files):
        technologies.append("pip/Poetry")
    if any('package.json' in str(f) for f in all_files):
        technologies.append("npm/Node.js")
    if any('dockerfile' in str(f).lower() for f in all_files):
        technologies.append("Docker")
    
    # Identify architecture patterns
    has_ui = any('ui' in str(f) or 'frontend' in str(f) or 'web' in str(f) for f in all_files)
    has_api = any('api' in str(f) or 'server' in str(f) or 'backend' in str(f) for f in all_files)
    has_tests = any('test' in str(f) for f in all_files)
    has_docs = bool(doc_files)
    
    # Build overview
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
    
    # Identify entry points
    entry_points = []
    for f in all_files:
        if f.name in {'main.py', 'app.py', 'run.py', 'server.py', 'index.js', 'index.ts', 'app.js', 'app.ts'}:
            entry_points.append(f)
    
    if entry_points:
        overview_lines.append("")
        overview_lines.append("🚀 Entry Points:")
        for entry in entry_points:
            overview_lines.append(f"   • {entry}")
    
    overview_lines.append("")  # Add blank line
    return "\n".join(overview_lines)

def format_file_content(project_root: Path, relative_path: Path) -> str | None:
    """
    Formats the content of a single file into a Markdown code block.
    Appends a comment if encoding fallback to latin-1 was used.

    Args:
        project_root: The absolute path to the project root.
        relative_path: The relative path of the file from the project root.

    Returns:
        A formatted string for the file, or None if the file cannot be read.
    """
    absolute_path = project_root.resolve() / relative_path
    result = read_file_content(absolute_path)
    if result is None:
        logger.warning(f"Skipping file due to read error: {relative_path.as_posix()}")
        return f"--- File: {relative_path.as_posix()} ---\n```\n[Error reading file content]\n```\n"

    content, encoding = result
    lang_identifier = get_language_identifier(absolute_path)
    # Use forward slashes for the path in the header
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
    """
    Generates the final Markdown with enhanced structure:
      1. Architectural overview
      2. Enhanced project structure with tree view and token estimates
      3. File contents
    """
    output_parts: List[str] = []

    # Ensure we have a full file list for structure analysis
    if all_files is None:
        all_files = relevant_files

    # --- 1. Architectural Overview -----------------------------------
    output_parts.append(format_architectural_overview(project_root, all_files))

    # --- 2. Enhanced Project Structure ------------------------------
    output_parts.append(
        format_enhanced_project_structure(
            all_files,
            relevant_files,
            project_root,
            file_token_map=file_token_map,
        )
    )

    # --- 3. File Contents -------------------------------------------
    output_parts.append("File Contents:")
    output_parts.append("==============")
    if not relevant_files:
        output_parts.append("(No relevant files to display content for)")
    else:
        for rel in relevant_files:
            output_parts.append(format_file_content(project_root, rel) or
                                f"--- File: {rel.as_posix()} ---\n[Failed to read]")
    
    return "\n".join(output_parts) 