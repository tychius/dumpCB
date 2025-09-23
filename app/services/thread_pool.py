"""
thread_pool: Provides a shared ThreadPoolExecutor for background tasks.
Respects DUMPCB_MAX_WORKERS env var for concurrency control.
Public API: SHARED_POOL, get_shared_pool(), MAX_WORKERS.
"""
import os
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

def _get_max_workers() -> int:
    """Determines the max workers for the pool, respecting the env var."""
    default_workers = os.cpu_count() or 4
    try:
        env_workers = os.environ.get("DUMPCB_MAX_WORKERS")
        if env_workers:
            max_workers = int(env_workers)
            logger.info(f"Using DUMPCB_MAX_WORKERS={max_workers} for shared thread pool.")
            return max_workers
        else:
            logger.info(f"Using default max_workers={default_workers} (CPU count or 4) for shared thread pool.")
            return default_workers
    except ValueError:
        logger.warning(f"Invalid value for DUMPCB_MAX_WORKERS: '{env_workers}'. Using default: {default_workers}.")
        return default_workers
    except Exception as e:
        logger.exception(f"Error reading DUMPCB_MAX_WORKERS environment variable. Using default: {default_workers}.")
        return default_workers

# Determine max workers and store it
MAX_WORKERS = _get_max_workers()

# Module-level shared thread pool
SHARED_POOL = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# Optional: Add a function to get the pool if needed elsewhere, 
def get_shared_pool() -> ThreadPoolExecutor:
    """Returns the shared ThreadPoolExecutor instance."""
    return SHARED_POOL

__all__ = ["SHARED_POOL", "get_shared_pool", "MAX_WORKERS"] 