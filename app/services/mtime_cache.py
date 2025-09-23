from pathlib import Path
import json
import threading
from typing import Dict, List, Tuple, Optional, Any
import logging
from PySide6.QtCore import QObject, Signal, QThread, QMutex, QWaitCondition

logger = logging.getLogger(__name__)

class MTimeCache(QObject):
    """
    Handles loading, saving, and in-memory storage of file modification times
    and file lists for projects, keyed by project root directory.

    Uses a JSON file (`~/.dumpcb-cache.json`) for persistence across sessions.
    Provides thread-safe access to the cached data.

    Attributes:
        CACHE_FILE (Path): The path to the cache file in the user's home directory.
        cache_updated (Signal): Emitted when the cache is updated (currently unused).
    """
    CACHE_FILE = Path.home() / ".dumpcb-cache.json"
    cache_updated = Signal()

    def __init__(self) -> None:
        """Initializes the cache, loading existing data from disk."""
        super().__init__()
        # {<abs_project_root_str>: {"mtimes": {<rel_path_str>: mtime, ...}, "files": [<rel_path_str>, ...]}, ...}
        self._ram: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Loads the cache data from the JSON file into memory."""
        if self.CACHE_FILE.exists():
            try:
                data = json.loads(self.CACHE_FILE.read_text(encoding='utf-8'))
                if isinstance(data, dict):
                    self._ram = data
            except json.JSONDecodeError as e:
                logger.warning(f"Cache file {self.CACHE_FILE} is corrupted (JSONDecodeError: {e}). Ignoring cache.")
            except (OSError, IOError) as e:
                # Log full error but only print warning
                logger.exception(f"Error reading cache file {self.CACHE_FILE}")
                logger.warning(f"Error loading cache file {self.CACHE_FILE}: {e}. Ignoring cache.")

    def load(self, project_root: Path) -> Optional[Tuple[Dict[str, float], List[str]]]:
        """Loads cached mtimes and file list for a project root. Returns None if not cached."""
        key = str(project_root.resolve())
        with self._lock:
            cached_data = self._ram.get(key)
            if cached_data and "mtimes" in cached_data and "files" in cached_data:
                # Return copies to prevent external modification
                return cached_data["mtimes"].copy(), cached_data["files"].copy()
            return None

    def save(self, project_root: Path, mtimes: Dict[str, float], files: List[str]) -> None:
        """
        Saves the modification times and file list for a specific project root
        to the in-memory cache and persists it to the JSON file.

        Args:
            project_root: The absolute path to the project root.
            mtimes: A dictionary mapping relative file paths (str) to their modification times (float).
            files: A list of relative file paths (str) included in the cache entry.
        """
        key = str(project_root.resolve())
        with self._lock:
            self._ram[key] = {"mtimes": mtimes, "files": files}
            try:
                self.CACHE_FILE.write_text(json.dumps(self._ram, indent=4), encoding='utf-8')
                logger.debug(f"Cache saved successfully for {key}")
            except (OSError, IOError, TypeError) as e: # Catch file errors and json errors
                logger.warning(f"Error saving cache file {self.CACHE_FILE}: {e}") 