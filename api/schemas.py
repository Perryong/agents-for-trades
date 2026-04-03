from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class AnalyzeRequest(BaseModel):
    ticker: str
    date: str  # "YYYY-MM-DD"
    analysts: List[str] = ["market", "technical", "social", "news", "fundamentals"]
    enable_options: bool = False
    llm_provider: str = "openai"
    deep_think_llm: str = "gpt-5.2"
    quick_think_llm: str = "gpt-5-mini"

    def config_dict(self) -> Dict[str, Any]:
        from tradingagents.default_config import DEFAULT_CONFIG
        cfg = dict(DEFAULT_CONFIG)
        cfg["enable_options"] = self.enable_options
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
