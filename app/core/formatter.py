from pathlib import Path
from typing import List, Dict
import logging

from app.utils.file_utils import get_language_identifier, read_file_content

logger = logging.getLogger(__name__)

def format_project_structure(relative_files: List[Path]) -> str:
    """
    Generates a string representation of the project structure (list of files).

    Args:
        relative_files: A list of Path objects relative to the project root.

    Returns:
        A formatted string listing the files.
    """
    structure_lines = ["Project Structure:", "==================="]
    if not relative_files:
        structure_lines.append("(No relevant files found)")
    else:
        # Use forward slashes for cross-platform consistency in output
        structure_lines.extend([f"- {p.as_posix()}" for p in relative_files])
    structure_lines.append("\n") # Add a blank line after structure
    return "\n".join(structure_lines)

def format_file_content(project_root: Path, relative_path: Path) -> str | None:
    """
    Formats the content of a single file into a Markdown code block.

    Args:
        project_root: The absolute path to the project root.
        relative_path: The relative path of the file from the project root.

    Returns:
        A formatted string for the file, or None if the file cannot be read.
    """
    absolute_path = project_root.resolve() / relative_path
    content = read_file_content(absolute_path)

    if content is None:
        logger.warning(f"Skipping file due to read error: {relative_path.as_posix()}")
        return f"--- File: {relative_path.as_posix()} ---\n```\n[Error reading file content]\n```\n"

    lang_identifier = get_language_identifier(absolute_path)
    # Use forward slashes for the path in the header
    header = f"--- File: {relative_path.as_posix()} ---"
    code_block = f"```{lang_identifier}\n{content}\n```"

    return f"{header}\n{code_block}\n"

def format_output(project_root: Path, relevant_files: List[Path]) -> str:
    """
    Generates the final formatted string including structure and file contents.

    Args:
        project_root: The absolute path to the project root.
        relevant_files: A list of Path objects relative to the project root.

    Returns:
        The final formatted output string.
    """
    output_parts = []

    # 1. Format Project Structure
    structure_string = format_project_structure(relevant_files)
    output_parts.append(structure_string)

    # 2. Format Content Section Header
    output_parts.append("File Contents:")
    output_parts.append("==============")

    # 3. Format each file's content
    if not relevant_files:
        output_parts.append("(No relevant files to display content for)")
    else:
        for relative_path in relevant_files:
            formatted_file = format_file_content(project_root, relative_path)
            if formatted_file:
                output_parts.append(formatted_file)
            else:
                # Append an error message placeholder if reading failed completely
                output_parts.append(f"--- File: {relative_path.as_posix()} ---\n[Failed to read or format file]\n")

    return "\n".join(output_parts) 