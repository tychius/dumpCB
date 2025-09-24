"""Simple JSON-backed cache for file modification times."""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class MTimeCache(QObject):
    """Thread-safe cache storing mtimes and file lists per project root."""

    CACHE_FILE = Path.home() / ".dumpcb-cache.json"
    cache_updated = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._ram: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        if not self.CACHE_FILE.exists():
            return

        try:
            data = json.loads(self.CACHE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.warning("Cache file %s is corrupted (JSONDecodeError: %s). Ignoring cache.", self.CACHE_FILE, exc)
            return
        except (OSError, IOError) as exc:
            logger.exception("Error reading cache file %s", self.CACHE_FILE)
            logger.warning("Error loading cache file %s: %s. Ignoring cache.", self.CACHE_FILE, exc)
            return

        if isinstance(data, dict):
            self._ram = data

    def load(self, project_root: Path) -> Optional[Tuple[Dict[str, float], List[str]]]:
        key = str(project_root.resolve())
        with self._lock:
            cached_data = self._ram.get(key)
            if cached_data and "mtimes" in cached_data and "files" in cached_data:
                return cached_data["mtimes"].copy(), cached_data["files"].copy()
            return None

    def save(self, project_root: Path, mtimes: Dict[str, float], files: List[str]) -> None:
        key = str(project_root.resolve())
        with self._lock:
            self._ram[key] = {"mtimes": mtimes, "files": files}
            try:
                self.CACHE_FILE.write_text(json.dumps(self._ram, indent=4), encoding="utf-8")
                logger.debug("Cache saved successfully for %s", key)
            except (OSError, IOError, TypeError) as exc:
                logger.warning("Error saving cache file %s: %s", self.CACHE_FILE, exc)


__all__ = ["MTimeCache"]
