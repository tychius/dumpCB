import chardet
from pathlib import Path
import logging
from typing import Optional
import os

from app.config.constants import LANGUAGE_MAP
from .binary_detection import BINARY_EXTENSIONS, _is_likely_binary_by_content

logger = logging.getLogger(__name__)


def read_file_content(file_path: Path) -> tuple[str, str] | None:
    """
    Reads the content of a file, attempting UTF-8 encoding first,
    then falling back to chardet detection and latin-1.

    Returns:
        (content, encoding) tuple, or None if reading fails.
    """
    try:
        # Read using UTF-8 with replacement for invalid characters
        return file_path.read_text(encoding='utf-8', errors='replace'), 'utf-8'
    except (OSError, ValueError) as e:
        logger.warning(f"Error reading {file_path} as UTF-8: {e}. Attempting fallback detection.")
        try:
            # Fallback: detect encoding and decode
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            detected_encoding = chardet.detect(raw_data).get('encoding')
            if detected_encoding:
                logger.info(f"Detected encoding {detected_encoding} for {file_path}.")
                return raw_data.decode(detected_encoding, errors='replace'), detected_encoding
            # Last resort: decode as latin-1
            logger.warning(f"Could not detect encoding for {file_path}. Decoding as latin-1.")
            return raw_data.decode('latin-1', errors='replace'), 'latin-1'
        except (OSError, ValueError) as e2:
            logger.exception(f"Fallback error reading {file_path}")
            return None

def get_language_identifier(file_path: Path) -> str:
    """
    Determines the Markdown language identifier based on the file extension.

    Args:
        file_path: The Path object of the file.

    Returns:
        The language identifier string (e.g., "python"), or an empty string if unknown.
    """
    # Handle special filenames first
    if file_path.name == 'Dockerfile':
        return LANGUAGE_MAP.get('Dockerfile', '')

    # Check extension
    extension = file_path.suffix.lower()
    return LANGUAGE_MAP.get(extension, '') # Return empty string if no mapping found 

def get_language_from_extension(file_path: Path) -> Optional[str]:
    """Gets the language name based on file extension."""
    ext = file_path.suffix.lower()
    # Special case for Dockerfile with no extension
    if file_path.name == 'Dockerfile':
        return LANGUAGE_MAP.get('Dockerfile')
    return LANGUAGE_MAP.get(ext)

def is_binary_file(file_path: Path, unknown_ext_read_limit: int = 1024) -> bool:
    """
    Checks if a file is likely binary.

    First, checks against a list of known binary extensions.
    If the extension is unknown and not recognized as a text language,
    reads the first `unknown_ext_read_limit` bytes and uses heuristics
    (checking for null bytes or high proportion of non-text characters)
    to determine if it's binary.

    Args:
        file_path: The Path object of the file.
        unknown_ext_read_limit: Max bytes to read for heuristic check.

    Returns:
        True if the file is considered binary, False otherwise.
    """
    ext = file_path.suffix.lower()

    # 1. Check known binary extensions
    if ext in BINARY_EXTENSIONS:
        return True

    # 2. Check known text extensions (from LANGUAGE_MAP)
    if ext in LANGUAGE_MAP:
        return False # Known text language, assume not binary
    if file_path.name == 'Dockerfile': # Special case
        return False

    # 3. Extension is unknown, apply heuristic check by reading content
    # Only read if extension is not empty (avoid reading for extensionless files
    # unless we explicitly want to - current logic avoids it).
    if ext:
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(unknown_ext_read_limit)
            # Call the heuristic function from the other module
            is_binary_content = _is_likely_binary_by_content(chunk)
            if is_binary_content:
                 logger.debug(f"Detected binary content in {file_path} by heuristic.")
            return is_binary_content

        except OSError as e:
            logger.warning(f"Could not read {file_path} for binary check: {e}")
            # Treat unreadable files as non-binary to avoid excluding potentially useful content
            return False 
        except Exception as e:
            logger.exception(f"Unexpected error during binary check for {file_path}")
            # Treat as non-binary on unexpected error
            return False 
            
    # 4. If extension is empty or heuristic check didn't classify as binary, assume text.
    return False 