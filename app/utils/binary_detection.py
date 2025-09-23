import logging
from pathlib import Path

logger = logging.getLogger(__name__)

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

# Set of byte values typically considered printable ASCII or common control codes in text files.
# Includes standard ASCII range 32-126, plus tab, newline, carriage return, form feed, vertical tab.
# Also includes BEL, BS, ESC, and potentially some high-bit markers used by encodings.
# Excludes NULL (0) and most other control codes (1-6, 14-31, 127).
_TEXT_CHARS = bytes({7, 8, 9, 10, 11, 12, 13, 27} | set(range(0x20, 0x7f)) | {0x80, 0xFE, 0xFF}) 
_NULL_BYTE = 0
_NON_TEXT_THRESHOLD = 0.15 # Proportion of non-text bytes to trigger binary classification
_NULL_BYTE_THRESHOLD_RATIO = 4 # e.g., if more than 1/4 of the chunk is null bytes

def _is_likely_binary_by_content(chunk: bytes) -> bool:
    """
    Applies heuristics to a chunk of bytes to determine if it's likely binary.

    Checks for:
    1. A high proportion of null bytes (more than len(chunk) / _NULL_BYTE_THRESHOLD_RATIO).
    2. A significant proportion (more than _NON_TEXT_THRESHOLD, e.g., 15%) of bytes
       that are not common text characters (printable ASCII + common whitespace/control)
       or null bytes.

    The 15% threshold for non-text characters is a common heuristic used in various
    tools (like `grep` or `git`). It's based on the observation that text files,
    even those with some binary data embedded (like comments in certain formats),
    rarely exceed this percentage of non-standard bytes. Binary files, on the
    other hand, frequently do.
    [Add reference links here if available]

    Args:
        chunk: The initial bytes read from the file.

    Returns:
        True if the heuristics suggest the content is binary, False otherwise.
    """
    if not chunk:
        return False # Empty file is not binary

    chunk_len = len(chunk)
    null_count = chunk.count(_NULL_BYTE)
    
    # Check for excessive null bytes first
    if null_count > chunk_len // _NULL_BYTE_THRESHOLD_RATIO:
        return True

    # Count non-text characters (excluding nulls, as they were checked)
    nontext_count = sum(1 for byte in chunk if byte not in _TEXT_CHARS and byte != _NULL_BYTE)

    # Check proportion of other non-text bytes
    if nontext_count > chunk_len * _NON_TEXT_THRESHOLD:
        return True

    return False 