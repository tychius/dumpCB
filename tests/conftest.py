"""Test configuration for ensuring project imports succeed."""
from __future__ import annotations

import sys
from pathlib import Path

# Add the project root to sys.path so ``import app`` works when tests run via pytest.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
