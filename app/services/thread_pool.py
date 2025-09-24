"""Shared thread pool helpers."""
from __future__ import annotations

import atexit
import logging
import os
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


def _get_max_workers() -> int:
    default_workers = max(1, os.cpu_count() or 4)
    env_value = os.environ.get("DUMPCB_MAX_WORKERS")
    if not env_value:
        logger.info("Using default max_workers=%s for shared thread pool.", default_workers)
        return default_workers

    try:
        parsed = int(env_value)
    except ValueError:
        logger.warning("Invalid value for DUMPCB_MAX_WORKERS=%r. Using default %s.", env_value, default_workers)
        return default_workers

    if parsed < 1:
        logger.warning("DUMPCB_MAX_WORKERS=%s is less than 1. Using default %s.", parsed, default_workers)
        return default_workers

    logger.info("Using DUMPCB_MAX_WORKERS=%s for shared thread pool.", parsed)
    return parsed


MAX_WORKERS = _get_max_workers()
SHARED_POOL = ThreadPoolExecutor(max_workers=MAX_WORKERS)


def _shutdown_pool() -> None:
    SHARED_POOL.shutdown(wait=False)


def get_shared_pool() -> ThreadPoolExecutor:
    """Return the shared ThreadPoolExecutor instance."""
    return SHARED_POOL


atexit.register(_shutdown_pool)

__all__ = ["SHARED_POOL", "get_shared_pool", "MAX_WORKERS"]
