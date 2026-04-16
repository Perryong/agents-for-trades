"""Screener strategy registry.

Provides a protocol-based registry for pluggable screening strategies.
Each strategy implements the ScreenerStrategy protocol and registers
with a unique name. The API and UI select strategies by name.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:
    from .screener_agent import ScreenerResult


@runtime_checkable
class ScreenerStrategy(Protocol):
    """Protocol for screener strategies."""

    def screen(self, config: dict, llm: object) -> "ScreenerResult": ...


@dataclass
class ScreenerInfo:
    """Metadata about a screener strategy."""
    name: str
    display_name: str
    description: str


_registry: dict[str, tuple[ScreenerInfo, ScreenerStrategy]] = {}


def register_strategy(name: str, info: ScreenerInfo, strategy: ScreenerStrategy) -> None:
    """Register a screener strategy by name."""
    _registry[name] = (info, strategy)


def get_strategy(name: str) -> ScreenerStrategy:
    """Look up a strategy by name. Falls back to 'momentum' if name is empty."""
    if not name:
        name = "momentum"
    if name not in _registry:
        raise KeyError(f"Unknown screener strategy: '{name}'. Available: {list(_registry.keys())}")
    return _registry[name][1]


def list_strategies() -> list[ScreenerInfo]:
    """Return metadata for all registered strategies."""
    return [info for info, _ in _registry.values()]


def get_strategy_info(name: str) -> ScreenerInfo | None:
    """Return info for a specific strategy, or None if not found."""
    entry = _registry.get(name)
    return entry[0] if entry else None
