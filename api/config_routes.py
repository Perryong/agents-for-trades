"""Runtime configuration CRUD endpoints.

GET /api/config          — all config (defaults merged with DB overrides)
GET /api/config/{key}    — single value
PUT /api/config/{key}    — upsert with validation
"""
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from .db import SessionDep
from .models import Config

logger = logging.getLogger(__name__)
config_router = APIRouter(prefix="/api")

# User-configurable subset of DEFAULT_CONFIG (skip internal paths)
_EXPOSED_DEFAULTS: dict[str, Any] = {
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5.2",
    "quick_think_llm": "gpt-5-mini",
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "enable_options": True,
    "options_vendor": "yfinance",
    "options_delta_target": 0.30,
    "options_dte_window": [0, 90],
    "options_min_oi": 100,
    "available_margin": None,
    "exclude_margin_intensive": False,
    # Risk parameters (Epic 6.3 defaults)
    "stop_loss_pct": 5.0,
    "max_position_pct": 10.0,
    "max_portfolio_exposure_pct": 50.0,
    "min_confidence_threshold": 65.0,
    # Agent weights (Epic 6.4 defaults)
    "agent_weight_fundamentals": 1.0,
    "agent_weight_news": 1.0,
    "agent_weight_market": 1.0,
    "agent_weight_social": 1.0,
    # Watchlist (Epic 6.2 default)
    "watchlist": [],
    # Schedule (Epic 6.4 default)
    "schedule_time": "08:00",
}

# Validation rules: key → (min, max) for numeric, or callable for complex
_VALIDATORS: dict[str, tuple[float, float] | str] = {
    "min_confidence_threshold": (0, 100),
    "max_position_pct": (0, 100),
    "max_portfolio_exposure_pct": (0, 100),
    "stop_loss_pct": (0, 50),
    "agent_weight_fundamentals": (0.0, 1.0),
    "agent_weight_news": (0.0, 1.0),
    "agent_weight_market": (0.0, 1.0),
    "agent_weight_social": (0.0, 1.0),
    "options_delta_target": (0.0, 1.0),
    "options_min_oi": (0, 100000),
    "max_debate_rounds": (1, 10),
    "max_risk_discuss_rounds": (1, 10),
    "watchlist": "watchlist",
}


def _validate(key: str, value: Any) -> None:
    """Validate a config value. Raises HTTPException on invalid."""
    rule = _VALIDATORS.get(key)
    if rule is None:
        return  # No validation for unknown keys

    if rule == "watchlist":
        if not isinstance(value, list):
            raise HTTPException(status_code=422, detail=f"'{key}' must be a JSON array")
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise HTTPException(status_code=422, detail=f"'{key}' items must be non-empty strings")
        return

    if isinstance(rule, tuple):
        lo, hi = rule
        if not isinstance(value, (int, float)):
            raise HTTPException(status_code=422, detail=f"'{key}' must be a number")
        if value < lo or value > hi:
            raise HTTPException(status_code=422, detail=f"'{key}' must be between {lo} and {hi}")


class ConfigValue(BaseModel):
    value: Any


@config_router.get("/config")
async def get_all_config(session: SessionDep):
    """Return all config: defaults merged with DB overrides."""
    result = await session.execute(select(Config))
    db_entries = {c.key: json.loads(c.value) for c in result.scalars().all()}
    merged = {**_EXPOSED_DEFAULTS, **db_entries}
    return merged


@config_router.get("/config/{key}")
async def get_config_value(key: str, session: SessionDep):
    """Return a single config value (DB override or default fallback)."""
    result = await session.execute(select(Config).where(Config.key == key))
    entry = result.scalar_one_or_none()
    if entry:
        return {"key": key, "value": json.loads(entry.value)}
    if key in _EXPOSED_DEFAULTS:
        return {"key": key, "value": _EXPOSED_DEFAULTS[key]}
    raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")


@config_router.put("/config/{key}")
async def put_config_value(key: str, body: ConfigValue, session: SessionDep):
    """Upsert a config value with validation."""
    _validate(key, body.value)

    result = await session.execute(select(Config).where(Config.key == key))
    entry = result.scalar_one_or_none()

    if entry:
        entry.value = json.dumps(body.value)
        entry.updated_at = datetime.utcnow()
    else:
        entry = Config(key=key, value=json.dumps(body.value))
        session.add(entry)

    await session.commit()
    return {"key": key, "value": body.value}
