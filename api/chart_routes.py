"""Chart overlay REST endpoint.

Provides GET /api/chart/{ticker}/overlay which reads the most recent agent
analysis log for a ticker and returns structured signal/price data.
Returns 404 when no analysis exists (frontend passive-mode signal per D-13).
"""
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
import glob
import re

from .schemas import ChartOverlayResponse

chart_router = APIRouter(prefix="/api")


def _parse_structured_json(text: str) -> dict | None:
    """Extract trailing ```json block from trader output."""
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except (ValueError, json.JSONDecodeError):
            return None
    return None


def _log_dir(ticker: str) -> Path:
    """Return the path to the TradingAgentsStrategy_logs directory for a ticker.

    Extracted as a standalone function so tests can monkeypatch it with a
    tmp_path without touching the filesystem.
    """
    return Path(f"eval_results/{ticker.upper()}/TradingAgentsStrategy_logs")


def _extract_signal(text: str) -> str:
    """Extract BUY/SELL/HOLD from final_trade_decision prose."""
    upper = text.upper()
    # Look for explicit recommendation patterns
    for pattern in [
        r"RECOMMENDATION:\s*(BUY|SELL|HOLD)",
        r"MY RECOMMENDATION:\s*(BUY|SELL|HOLD)",
        r"DECISION.*?(BUY|SELL|HOLD)",
    ]:
        m = re.search(pattern, upper)
        if m:
            return m.group(1)
    # Fallback: count occurrences
    buys = upper.count("BUY")
    sells = upper.count("SELL")
    if sells > buys:
        return "SELL"
    elif buys > sells:
        return "BUY"
    return "HOLD"


def _extract_price(text: str, label: str) -> float | None:
    """Attempt to extract a price value near a label (e.g. 'target', 'stop loss')."""
    patterns = [
        rf"{label}\s*(?:price)?[:\s]*\$?([\d,.]+)",
        rf"\$?([\d,.]+)\s*{label}",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m and m.group(1):
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def _extract_expiry(options_legs: str) -> str | None:
    """Extract YYYY-MM-DD date from options_legs text."""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", options_legs)
    return m.group(1) if m else None


def _extract_strategy_name(options_strategy: str) -> str | None:
    """Extract strategy name from options_strategy text."""
    if not options_strategy or options_strategy.strip() == "":
        return None
    # First non-empty line is typically the strategy name
    for line in options_strategy.strip().split("\n"):
        line = line.strip().lstrip("#").strip()
        if line:
            return line[:80]  # cap length
    return None


@chart_router.get("/chart/{ticker}/overlay", response_model=ChartOverlayResponse)
async def get_chart_overlay(ticker: str):
    """Return agent signal overlay data for the most recent analysis.

    Returns 404 if no analysis exists (passive mode signal to frontend per D-13).
    """
    log_directory = _log_dir(ticker)
    if not log_directory.exists():
        raise HTTPException(status_code=404, detail="No analysis found")

    log_files = sorted(glob.glob(str(log_directory / "full_states_log_*.json")))
    if not log_files:
        raise HTTPException(status_code=404, detail="No analysis found")

    latest_log_path = log_files[-1]

    # Staleness check: if log file is older than 24 hours, treat as no analysis
    import os
    from datetime import datetime, timedelta
    file_mtime = datetime.fromtimestamp(os.path.getmtime(latest_log_path))
    if datetime.now() - file_mtime > timedelta(hours=24):
        raise HTTPException(status_code=404, detail="Analysis expired (>24h old)")

    with open(latest_log_path, encoding="utf-8") as f:
        log_data = json.load(f)

    latest_date = sorted(log_data.keys())[-1]
    state = log_data[latest_date]

    ftd = state.get("final_trade_decision", "")
    options_legs_text = state.get("options_legs", "")
    options_strategy_text = state.get("options_strategy", "")

    # Try structured JSON first (D-13), fallback to regex
    structured = _parse_structured_json(ftd)

    if structured:
        signal = structured.get("signal", _extract_signal(ftd))
        entry_price_val = structured.get("entry_price")
        take_profit_val = structured.get("target_price")
        stop_loss_val = structured.get("stop_loss")
        strategy_val = structured.get("strategy") or _extract_strategy_name(options_strategy_text)
    else:
        signal = _extract_signal(ftd)
        entry_price_val = _extract_price(ftd, "entry")
        take_profit_val = _extract_price(ftd, r"target|take.profit|tp")
        stop_loss_val = _extract_price(ftd, r"stop.loss|sl")
        strategy_val = _extract_strategy_name(options_strategy_text)

    return ChartOverlayResponse(
        ticker=ticker.upper(),
        analysis_date=latest_date,
        signal=signal.upper() if isinstance(signal, str) else signal,
        entry_price=float(entry_price_val) if entry_price_val is not None else None,
        take_profit=float(take_profit_val) if take_profit_val is not None else None,
        stop_loss=float(stop_loss_val) if stop_loss_val is not None else None,
        expiry_date=_extract_expiry(options_legs_text),
        strategy_name=strategy_val,
        options_legs=options_legs_text,
        final_trade_decision=ftd,
    )
