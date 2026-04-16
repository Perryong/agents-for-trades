"""Market regime API endpoints.

GET /api/regime — current regime classification + breadth score
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any

regime_router = APIRouter(prefix="/api")

# Cache regime result for 15 minutes
_regime_cache: dict = {"result": None, "expires": 0}


class RegimeResponse(BaseModel):
    regime: str                    # "Broadening" | "Concentration" | "Contraction" | "Inflationary" | "Transitional"
    confidence: float              # 0-100
    breadth_score: float           # 0-100
    breadth_label: str             # "Healthy" | "Moderate" | "Weak"
    signals: Dict[str, Any]
    computed_at: str


class ExposureResponse(BaseModel):
    exposure_ceiling: float
    posture: str               # NEW_ENTRY_ALLOWED | REDUCE_ONLY | CASH_PRIORITY
    growth_vs_value_bias: str
    regime: str
    breadth_label: str
    top_probability: float
    ftd_state: str
    rationale: str
    computed_at: str


_exposure_cache: dict = {"result": None, "expires": 0}


@regime_router.get("/exposure", response_model=ExposureResponse)
async def get_exposure():
    """Return current exposure recommendation."""
    import asyncio
    import time

    now = time.time()
    if _exposure_cache["result"] and _exposure_cache["expires"] > now:
        return _exposure_cache["result"]

    from tradingagents.services.exposure_manager import compute_exposure
    result = await asyncio.to_thread(compute_exposure)

    response = ExposureResponse(
        exposure_ceiling=result.exposure_ceiling,
        posture=result.posture,
        growth_vs_value_bias=result.growth_vs_value_bias,
        regime=result.regime,
        breadth_label=result.breadth_label,
        top_probability=result.top_probability,
        ftd_state=result.ftd_state,
        rationale=result.rationale,
        computed_at=result.computed_at.isoformat(),
    )

    _exposure_cache["result"] = response
    _exposure_cache["expires"] = now + 900

    return response


@regime_router.get("/regime", response_model=RegimeResponse)
async def get_regime():
    """Return current market regime classification."""
    import asyncio
    import time

    now = time.time()
    if _regime_cache["result"] and _regime_cache["expires"] > now:
        return _regime_cache["result"]

    from tradingagents.services.regime_detector import detect_regime
    result = await asyncio.to_thread(detect_regime)

    response = RegimeResponse(
        regime=result.regime,
        confidence=result.confidence,
        breadth_score=result.breadth_score,
        breadth_label=result.breadth_label,
        signals=result.signals,
        computed_at=result.computed_at.isoformat(),
    )

    _regime_cache["result"] = response
    _regime_cache["expires"] = now + 900  # 15 min cache

    return response
