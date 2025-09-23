"""
Light-weight, binary-safe token estimator.

•  Accurate if `tiktoken` is installed (lazy import).  
•  Falls back to ≈1 token / 4 bytes heuristic.  
•  Never reads more than 400 KiB from any file.
"""
from __future__ import annotations

from pathlib import Path
import logging
import math

from app.utils.file_utils import is_binary_file, read_file_content

logger = logging.getLogger(__name__)
_MAX_READ = 400 * 1024  # 400 KiB


def _accurate_len(text: str) -> int | None:
    """Use tiktoken if present; return None on import failure."""
    try:
        import tiktoken  # noqa: WPS433 – runtime import is intentional
    except ModuleNotFoundError:
        return None

    try:  # try model-specific first
        enc = tiktoken.encoding_for_model("cl100k_base")
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def estimate_text_tokens(text: str) -> int:
    """
    Cheap & cheerful token estimator for an in-memory string.

    •  Uses the same tiktoken + heuristic fallback as estimate_file_tokens().
    •  No need to duplicate logic – we reuse _accurate_len().
    """
    accurate = _accurate_len(text)
    return accurate if accurate is not None else math.ceil(len(text) / 4)


def estimate_file_tokens(path: Path) -> int:
    """Return an estimated token count for `path` (0 for binaries)."""
    logger.debug("Estimating tokens for: %s", path)
    if is_binary_file(path):
        logger.debug("Detected as binary file: %s", path)
        return 0

    try:
        size = path.stat().st_size
        logger.debug("File size for %s: %d bytes", path, size)
    except OSError as e:
        logger.warning("stat() failed for %s: %s – assuming 0 tokens", path, e)
        return 0

    # Large file → skip read, use size-only heuristic
    if size > _MAX_READ:
        estimate = math.ceil(size / 4)
        logger.debug("Large file heuristic for %s: %d tokens", path, estimate)
        return estimate

    read_res = read_file_content(path)
    if read_res is None:
        logger.warning("read_file_content failed for %s, returning 0 tokens", path)
        return 0
    text, encoding = read_res
    logger.debug("Read %d chars from %s with encoding %s", len(text), path, encoding)

    accurate = _accurate_len(text)
    if accurate is not None:
        logger.debug("Accurate (tiktoken) count for %s: %d tokens", path, accurate)
        return accurate
    else:
        estimate = math.ceil(len(text) / 4)
        logger.debug("Heuristic count for %s: %d tokens", path, estimate)
        return estimate 