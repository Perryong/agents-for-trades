import os

DEFAULT_CONFIG = {
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv("TRADINGAGENTS_RESULTS_DIR", "./results"),
    "data_cache_dir": os.path.join(
        os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
        "dataflows/data_cache",
    ),
    # LLM settings
    "llm_provider": "openai",
    "deep_think_llm": "gpt-5.2",
    "quick_think_llm": "gpt-5-mini",
    "backend_url": "https://api.openai.com/v1",
    # Provider-specific thinking configuration
    "google_thinking_level": None,      # "high", "minimal", etc.
    "openai_reasoning_effort": None,    # "medium", "high", "low"
    # Debate and discussion settings
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
    "max_recur_limit": 100,
    # Data vendor configuration
    # Category-level configuration (default for all tools in category)
    "data_vendors": {
        "core_stock_apis": "yfinance",       # Options: alpha_vantage, yfinance
        "technical_indicators": "yfinance",  # Options: alpha_vantage, yfinance
        "technical_pattern": "yfinance",     # Options: yfinance
        "fundamental_data": "yfinance",      # Options: alpha_vantage, yfinance
        "news_data": "yfinance",             # Options: alpha_vantage, yfinance
        "options_data": "yfinance",          # Options: tradier, yfinance
        "screener_data": "yfinance",         # Options: yfinance
    },
    # Tool-level configuration (takes precedence over category-level)
    "tool_vendors": {
        # Example: "get_stock_data": "alpha_vantage",  # Override category default
    },
    # Options configuration
    "enable_options": False,            # Off by default — additive, non-breaking
    "options_vendor": "yfinance",        # Primary vendor for options data (tradier needs API key)
    "options_delta_target": 0.30,       # Target delta for contract selection (Phase 3)
    "options_dte_window": [0, 90],      # DTE range [min, max] — multi-timeframe buckets handle sub-ranges
    "options_min_oi": 100,              # Minimum open interest filter
    "available_margin": None,            # Float or None; None = fail-safe (exclude all margin_intensive)
    "exclude_margin_intensive": False,   # Explicit override: True forces exclusion even if margin is set
}
