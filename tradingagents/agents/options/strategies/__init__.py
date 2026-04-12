"""Strategy registry package.

Exports:
    load_registry()          - Load and validate registry.yaml via Pydantic
    REGISTRY                 - Module-level singleton (loaded at import time)
    normalize_strategy_key() - Canonical strategy name normalizer (shared utility)
    StrategyMeta, LegDef, SoftScore, StrategyRegistry  - Pydantic models
    GateContext, filter_strategies                      - Gate types
"""

import functools
from pathlib import Path

import yaml

from .models import LegDef, SoftScore, StrategyMeta, StrategyRegistry
from .gate import GateContext, filter_strategies

__all__ = [
    "load_registry",
    "REGISTRY",
    "normalize_strategy_key",
    "StrategyMeta",
    "LegDef",
    "SoftScore",
    "StrategyRegistry",
    "GateContext",
    "filter_strategies",
]


# ---------------------------------------------------------------------------
# Alias map: common non-canonical names -> canonical registry keys
# ---------------------------------------------------------------------------

_ALIAS_MAP: dict[str, str] = {
    "bull call spread": "long_call_spread",
    "bear put spread": "long_put_spread",
    "bear call spread": "short_call_spread",
    "bull put spread": "short_put_spread",
    "cash-secured put": "cash_secured_put",
    "cash secured put": "cash_secured_put",
    "calendar spread": "long_call_calendar",
}


# ---------------------------------------------------------------------------
# normalize_strategy_key
# ---------------------------------------------------------------------------


def normalize_strategy_key(strategy: str) -> str:
    """Return the canonical registry key for a strategy name string.

    Exported here to avoid duplication across consumer modules.
    All consumer files (options_strategy_selector.py,
    strike_expiry_selector.py, options_legs_builder.py) should import
    this function rather than defining their own copy.

    Examples:
        normalize_strategy_key("bull call spread")  -> "long_call_spread"
        normalize_strategy_key("Iron Condor -- bullish IV view") -> "iron_condor"
        normalize_strategy_key("long_call")         -> "long_call"
    """
    name_part = strategy.split("--")[0].strip().lower()
    if name_part in _ALIAS_MAP:
        return _ALIAS_MAP[name_part]
    return name_part.replace(" ", "_").replace("-", "_")


# ---------------------------------------------------------------------------
# load_registry
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=1)
def load_registry() -> StrategyRegistry:
    """Load and validate registry.yaml, cached after first call.

    Returns:
        StrategyRegistry: Fully validated Pydantic model.

    Raises:
        FileNotFoundError: If registry.yaml is missing.
        pydantic.ValidationError: If YAML data fails schema validation.
    """
    path = Path(__file__).parent / "registry.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return StrategyRegistry.model_validate(raw)


# ---------------------------------------------------------------------------
# Module-level singleton — loaded once at import time
# ---------------------------------------------------------------------------

REGISTRY: StrategyRegistry = load_registry()
