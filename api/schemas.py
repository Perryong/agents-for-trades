from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class AnalyzeRequest(BaseModel):
    ticker: str
    date: str  # "YYYY-MM-DD"
    analysts: List[str] = ["market", "technical", "social", "news", "fundamentals"]
    llm_provider: str = "openai"
    deep_think_llm: str = "gpt-5.2"
    quick_think_llm: str = "gpt-5-mini"

    def config_dict(self) -> Dict[str, Any]:
        from tradingagents.default_config import DEFAULT_CONFIG
        cfg = dict(DEFAULT_CONFIG)
        cfg["enable_options"] = True  # options always enabled (D-06)
        cfg["llm_provider"] = self.llm_provider
        cfg["deep_think_llm"] = self.deep_think_llm
        cfg["quick_think_llm"] = self.quick_think_llm
        return cfg


class AnalyzeResponse(BaseModel):
    run_id: str


class ProgressEvent(BaseModel):
    type: str  # "node_start" | "node_end" | "complete" | "error"
    node: Optional[str] = None
    state: Optional[Dict[str, Any]] = None
    signal: Optional[str] = None  # populated on "complete" events
    message: Optional[str] = None  # populated on "error" events


class ScreenRequest(BaseModel):
    max_picks: int = Field(default=5, ge=1, le=10)
    universe: str = "sp500"
    strategy: str = "momentum"             # Registry name: "momentum", "vcp", "canslim", etc.
    llm_provider: str = "openai"
    quick_think_llm: str = "gpt-5-mini"

    def config_dict(self) -> Dict[str, Any]:
        from tradingagents.default_config import DEFAULT_CONFIG
        cfg = dict(DEFAULT_CONFIG)
        cfg["screener_n_picks"] = self.max_picks
        cfg["llm_provider"] = self.llm_provider
        cfg["quick_think_llm"] = self.quick_think_llm
        return cfg


class ScreenResponse(BaseModel):
    status: str           # "success" | "partial" | "error"
    data: Dict[str, Any]  # ScreenerResult.model_dump(mode="json") or error dict
    screened_at: str       # ISO 8601 UTC — empty string on hard error


class ChartOverlayResponse(BaseModel):
    ticker: str
    analysis_date: str                    # 'YYYY-MM-DD'
    signal: str                           # 'BUY' | 'SELL' | 'HOLD'
    entry_price: Optional[float] = None   # None if not parseable from prose
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    expiry_date: Optional[str] = None     # 'YYYY-MM-DD' from options metadata
    strategy_name: Optional[str] = None   # e.g. 'Bull Call Spread'
    options_legs: str = ""                # raw string for action panel display
    final_trade_decision: str = ""        # full text for Analysis back-link


# ---------------------------------------------------------------------------
# Trade execution schemas (Phase 14 — EXEC-01..05)
# ---------------------------------------------------------------------------

class TradeRequest(BaseModel):
    ticker: str
    direction: str                          # "BUY" | "SELL"
    trade_type: str = "equity"              # "equity" | "option"
    strategy_name: Optional[str] = None
    analysis_date: Optional[str] = None
    # Options fields (nullable for equity per D-16)
    options_legs: Optional[str] = None
    strike: Optional[float] = None
    expiry: Optional[str] = None
    contract_type: Optional[str] = None    # "call" | "put"
    # Scoring fields (Phase 15 — SCORE-01)
    confidence_text: Optional[str] = None  # full prose for confidence/target/stop extraction
    # Prediction linking (Epic 5)
    prediction_id: Optional[int] = None


class TradeResponse(BaseModel):
    id: int
    order_id: str
    status: str
    ticker: str
    direction: str
    trade_type: str
    quantity: int
    fill_price: Optional[float] = None
    fill_time: Optional[str] = None
    confidence: Optional[float] = None


class TradeStatusResponse(BaseModel):
    status: str
    fill_price: Optional[float] = None
    fill_time: Optional[str] = None
    close_time: Optional[str] = None        # REQUIRED for CHART-03 exit marker
    rejection_reason: Optional[str] = None
    order_id: Optional[str] = None
    close_price: Optional[float] = None
    pnl_pct: Optional[float] = None
    outcome: Optional[str] = None
    close_reason: Optional[str] = None  # "Target Hit" | "Stop-Loss" | "Manual Close" | "Expired" | null


class BracketTradeRequest(BaseModel):
    ticker: str
    direction: str                        # "BUY" | "SELL"
    trade_type: str = "equity"
    entry_price: Optional[float] = None   # If None or close to market: market order; else: limit
    target_price: float                   # TakeProfitRequest.limit_price
    stop_loss: float                      # StopLossRequest.stop_price
    quantity: int = 100
    tif: str = "GTC"                      # "GTC" | "DAY"
    strategy_name: Optional[str] = None
    analysis_date: Optional[str] = None
    confidence: Optional[float] = None
    confidence_text: Optional[str] = None  # Prose text for confidence extraction
    prediction_id: Optional[int] = None   # Link to predictions table (Epic 5)


class LivePriceResponse(BaseModel):
    ticker: str
    price: float
    open: float
    change_pct: float
    timestamp: str


# ---------------------------------------------------------------------------
# Scoring schemas (Phase 15 — SCORE-02, SCORE-03)
# ---------------------------------------------------------------------------

class ScoreSummaryResponse(BaseModel):
    win_rate: float              # percentage 0-100
    expectancy: float            # average P&L per trade (weighted by win/loss rate)
    avg_winner: float            # average P&L % of winning trades
    avg_loser: float             # average P&L % of losing trades
    profit_factor: float         # sum(winners) / abs(sum(losers)), 0.0 if no losers
    total_trades: int            # all trades in DB
    total_closed: int            # trades with outcome != None
    disclaimer: Optional[str] = None  # present when total_closed < 5


class CalibrationBucket(BaseModel):
    bucket_label: str            # "0-20%", "20-40%", etc.
    bucket_min: int
    bucket_max: int
    actual_win_rate: float       # 0-100
    trade_count: int


class CalibrationResponse(BaseModel):
    buckets: List[CalibrationBucket]
    total_scored: int            # trades with non-null confidence + outcome
    message: Optional[str] = None  # present when insufficient data


# ---------------------------------------------------------------------------
# Dashboard schemas (Phase 16 — DASH-01..05)
# ---------------------------------------------------------------------------

class DashboardSummaryResponse(BaseModel):
    """Per D-06: summary stats endpoint. Win rate never shown alone (STATE.md decision)."""
    total_trades: int
    total_closed: int
    win_rate: float              # percentage 0-100
    expectancy: float
    avg_winner: float
    avg_loser: float
    profit_factor: float
    aggregate_pnl: float         # sum of all pnl_pct for closed trades
    disclaimer: Optional[str] = None  # when total_closed < 5
    avg_risk_reward: Optional[float] = None   # D-16
    avg_r_multiple: Optional[float] = None    # D-17


class DashboardTradeItem(BaseModel):
    """Single row in trade history table. Per D-09 columns."""
    id: int
    ticker: str
    direction: str               # "BUY" | "SELL"
    trade_type: str              # "equity" | "option"
    entry_date: Optional[str]    # analysis_date or fill_time ISO
    outcome: Optional[str]       # "WIN" | "LOSS" | None
    pnl_pct: Optional[float]
    strategy_name: Optional[str]
    is_legacy: bool              # True if no outcome and no pnl — per D-12
    close_reason: Optional[str] = None  # D-19


class DashboardTradesResponse(BaseModel):
    trades: List[DashboardTradeItem]
    total: int


class EquityCurvePoint(BaseModel):
    """Single data point on equity curve. Per D-05: X = close date, Y = cumulative P&L."""
    time: str                    # ISO date string for lightweight-charts
    value: float                 # cumulative P&L percentage


class EquityCurveResponse(BaseModel):
    points: List[EquityCurvePoint]
    total_trades: int
