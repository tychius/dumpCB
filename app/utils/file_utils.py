"""Utility helpers for reading files and classifying their type."""
from __future__ import annotations

from pathlib import Path
import logging
from typing import Optional

import chardet

from app.config.constants import LANGUAGE_MAP
from .binary_detection import BINARY_EXTENSIONS, _is_likely_binary_by_content

logger = logging.getLogger(__name__)


def read_file_content(file_path: Path) -> tuple[str, str] | None:
    """Return the decoded contents of *file_path* and the encoding that was used."""
    try:
        return file_path.read_text(encoding="utf-8", errors="replace"), "utf-8"
    except (OSError, ValueError) as exc:
        logger.warning("Error reading %s as UTF-8: %s. Attempting fallback detection.", file_path, exc)

    try:
        with file_path.open("rb") as handle:
            raw_data = handle.read()
    except (OSError, ValueError):
        logger.exception("Fallback error reading %s", file_path)
        return None

    detected_encoding = chardet.detect(raw_data).get("encoding")
    if detected_encoding:
        logger.info("Detected encoding %s for %s.", detected_encoding, file_path)
        return raw_data.decode(detected_encoding, errors="replace"), detected_encoding

    logger.warning("Could not detect encoding for %s. Decoding as latin-1.", file_path)
    return raw_data.decode("latin-1", errors="replace"), "latin-1"


def get_language_identifier(file_path: Path) -> str:
    """Return the Markdown language identifier for *file_path* if known."""
    if file_path.name == "Dockerfile":
        return LANGUAGE_MAP.get("Dockerfile", "")

    extension = file_path.suffix.lower()
    return LANGUAGE_MAP.get(extension, "")


def get_language_from_extension(file_path: Path) -> Optional[str]:
    """Return the language name associated with *file_path*'s extension."""
    if file_path.name == "Dockerfile":
        return LANGUAGE_MAP.get("Dockerfile")
    return LANGUAGE_MAP.get(file_path.suffix.lower())


def is_binary_file(file_path: Path, unknown_ext_read_limit: int = 1024) -> bool:
    """Return ``True`` if *file_path* is likely a binary file."""
    extension = file_path.suffix.lower()

    if extension in BINARY_EXTENSIONS:
        return True
    if extension in LANGUAGE_MAP or file_path.name == "Dockerfile":
        return False

    if extension:
        try:
            with file_path.open("rb") as handle:
                chunk = handle.read(unknown_ext_read_limit)
        except OSError as exc:
            logger.warning("Could not read %s for binary check: %s", file_path, exc)
            return False
        except Exception:
            logger.exception("Unexpected error during binary check for %s", file_path)
            return False

        if _is_likely_binary_by_content(chunk):
            logger.debug("Detected binary content in %s by heuristic.", file_path)
            return True

    return False
