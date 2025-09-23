from dataclasses import dataclass
import traceback

@dataclass
class WorkerError:
    """Data class to hold worker exception and traceback."""
    exception: Exception
    traceback: str 