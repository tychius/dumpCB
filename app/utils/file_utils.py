import chardet
from pathlib import Path
import logging

from app.config.constants import LANGUAGE_MAP

logger = logging.getLogger(__name__)


def read_file_content(file_path: Path) -> str | None:
    """
    Reads the content of a file, attempting UTF-8 encoding first,
    then falling back to chardet detection.

    Args:
        file_path: The Path object of the file to read.

    Returns:
        The content of the file as a string, or None if reading fails.
    """
    try:
        # Try reading with UTF-8 first, common and fast
        return file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        logger.warning(f"UTF-8 decoding failed for {file_path}. Attempting detection.")
        try:
            # Fallback to detecting the encoding
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            detected_encoding = chardet.detect(raw_data)['encoding']
            if detected_encoding:
                logger.info(f"Detected encoding {detected_encoding} for {file_path}.")
                return raw_data.decode(detected_encoding, errors='replace') # Replace errors
            else:
                logger.warning(f"Could not detect encoding for {file_path}. Reading as binary/latin-1.")
                # Last resort: read as latin-1 which reads all bytes
                return file_path.read_text(encoding='latin-1')
        except Exception as e:
            logger.error(f"Error reading {file_path} after encoding detection: {e}")
            return None
    except OSError as e:
        # Handles cases like file not found (though less likely here), permission errors
        logger.error(f"OS Error reading {file_path}: {e}")
        return None
    except Exception as e:
        # Catch any other unexpected errors during file reading
        logger.error(f"Unexpected error reading {file_path}: {e}")
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

# List of common binary file extensions (lowercase)
# This list is not exhaustive but covers many common types.
BINARY_EXTENSIONS = {
    # Images
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.ico', '.webp',
    # Audio
    '.mp3', '.wav', '.ogg', '.flac', '.aac',
    # Video
    '.mp4', '.avi', '.mov', '.mkv', '.wmv',
    # Archives
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
    # Documents (often binary)
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp',
    # Executables/Libraries
    '.exe', '.dll', '.so', '.dylib', '.app', '.msi',
    # Fonts
    '.ttf', '.otf', '.woff', '.woff2',
    # Other
    '.bin', '.dat', '.iso', '.img', '.pickle', '.pkl', '.pyc', '.pyo', '.pyd', # Python bytecode/compiled
    '.class', '.jar', # Java bytecode/archive
    '.swf', # Flash
    '.db', '.sqlite', '.sqlite3', # Databases
}

def is_binary_file(file_path: Path) -> bool:
    """
    Checks if a file is likely binary based on its extension.

    Args:
        file_path: The Path object of the file.

    Returns:
        True if the file extension is in the known binary list, False otherwise.
    """
    return file_path.suffix.lower() in BINARY_EXTENSIONS 