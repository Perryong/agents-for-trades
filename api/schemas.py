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
