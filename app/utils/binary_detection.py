"""Helpers for identifying binary content."""
from __future__ import annotations

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".ico", ".webp",
    ".mp3", ".wav", ".ogg", ".flac", ".aac",
    ".mp4", ".avi", ".mov", ".mkv", ".wmv",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp",
    ".exe", ".dll", ".so", ".dylib", ".app", ".msi",
    ".ttf", ".otf", ".woff", ".woff2",
    ".bin", ".dat", ".iso", ".img", ".pickle", ".pkl", ".pyc", ".pyo", ".pyd",
    ".class", ".jar",
    ".swf",
    ".db", ".sqlite", ".sqlite3",
}

_TEXT_CHARS = bytes({7, 8, 9, 10, 11, 12, 13, 27} | set(range(0x20, 0x7F)) | {0x80, 0xFE, 0xFF})
_NULL_BYTE = 0
_NON_TEXT_THRESHOLD = 0.15
_NULL_BYTE_THRESHOLD_RATIO = 4


def _is_likely_binary_by_content(chunk: bytes) -> bool:
    """Heuristic binary detection based on NULL and non-text characters."""
    if not chunk:
        return False

    chunk_len = len(chunk)
    null_count = chunk.count(_NULL_BYTE)
    if null_count > chunk_len // _NULL_BYTE_THRESHOLD_RATIO:
        return True

    nontext_count = sum(1 for byte in chunk if byte not in _TEXT_CHARS and byte != _NULL_BYTE)
    if nontext_count > chunk_len * _NON_TEXT_THRESHOLD:
        return True

    return False


__all__ = ["BINARY_EXTENSIONS", "_is_likely_binary_by_content"]
