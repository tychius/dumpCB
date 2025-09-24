"""Top-level package for dumpcb utilities."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - only for type checkers
    from .services.context_service import ContextService as _ContextService

__all__ = ["ContextService"]


def __getattr__(name: str):  # pragma: no cover - simple delegation
    if name == "ContextService":
        from .services.context_service import ContextService

        return ContextService
    raise AttributeError(name)
