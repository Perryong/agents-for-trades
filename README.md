# TradingAgents

AI-powered multi-agent trading analysis framework built with LangGraph. Orchestrates specialist analyst, debater, trader, and risk management agents to produce actionable trade recommendations for equities and options.

## Features

- **Multi-agent analysis pipeline**: 5 equity analysts (market, technical, social, news, fundamentals) + 7 options agents (volatility, flow, strategy, strike/expiry, pricing, legs, Greeks) running in parallel
- **Vol-aware analysis**: Volatility context pre-fetched and injected into all analysts with per-analyst directive strength
- **Bull/bear debate**: Configurable rounds of investment debate with research manager judgment
- **Risk management**: Three-way risk debate (aggressive/conservative/neutral) + exposure-gated risk judge with regime awareness
- **Market regime detection**: Breadth scoring, macro regime classification (Broadening/Concentration/Contraction/Inflationary/Transitional), exposure management
- **Multiple screener strategies**: Momentum, VCP, CANSLIM, Earnings Momentum, Custom Watchlist with strategy picker
- **Paper trading**: Alpaca bracket orders (OCO with take-profit + stop-loss) with auto-execution from recommendation approval
- **React frontend**: Dark-mode terminal aesthetic with 4-screen app (Recommendations, Screener, Chart, Track Record), TradingView charts, brokerage-style trade sidebar
- **Recommendation cards**: Separate equity/options cards with approve-to-execute flow
- **Performance tracking**: Win rate, P&L, equity curve, agent performance, calibration chart
- **Multi-provider LLM support**: OpenAI, Anthropic, Google, xAI, OpenRouter, Ollama
- **Knowledge wiki**: LLM-maintained research knowledge base (Karpathy's LLM Wiki pattern)

## Architecture

```
                    +------------------+
                    |   React Frontend |  (Vite + TailwindCSS)
                    |   localhost:5173  |
                    +--------+---------+
                             |
                    +--------v---------+
                    |  FastAPI Backend  |  (SSE streaming, REST API)
                    |   localhost:8000  |
                    +--------+---------+
                             |
          +------------------+------------------+
          |                  |                  |
   +------v------+   +------v------+   +------v------+
   | Equity Agents|   |Options Agents|  | Screener    |
   | (5 analysts) |   | (7 agents)  |  | (5 strategies)|
   +------+------+   +------+------+   +-------------+
          |                  |
   +------v------------------v------+
   | Bull/Bear Debate -> Trader     |
   | -> Risk Debate -> Risk Judge   |
   +--------------------------------+
          |
   +------v------+
   | Alpaca Paper |
   | Trading API  |
   +--------------+
```

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** and **npm** (for the frontend)
- API key for at least one LLM provider (OpenAI recommended)
- Optional: Alpaca paper trading account (for trade execution)

## Installation

### 1. Clone and enter the project

```bash
git clone https://github.com/Perryong/agents-for-trades.git
cd agents-for-trades
```

### 2. Install Python dependencies

Using uv (recommended):

```bash
uv sync
```

Or using pip with a virtual environment:

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -e .
```

### 3. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
# LLM Provider (at least one required)
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# GOOGLE_API_KEY=AI...
# XAI_API_KEY=xai-...
# OPENROUTER_API_KEY=sk-or-...

# Alpaca Paper Trading (optional — required for trade execution)
ALPACA_PAPER_KEY=PK...
ALPACA_PAPER_SECRET=...

# Optional
# TRADIER_API_KEY=...          # Alternative options data provider
# YFINANCE_PROXY=http://...    # Proxy for yfinance requests
# TRADINGAGENTS_RESULTS_DIR=./results
```

## Running

### Start both backend and frontend

**Terminal 1 — Backend (FastAPI):**

```bash
uvicorn api.main:app --reload --port 8000
```

**Terminal 2 — Frontend (Vite dev server):**

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

### CLI mode (no frontend)

```bash
python -m cli.main analyze
```

You'll be prompted for ticker, date, analyst selection, LLM provider, and models.

### Programmatic usage

```python
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "openai"
config["quick_think_llm"] = "gpt-4o-mini"
config["deep_think_llm"] = "gpt-4o"

ta = TradingAgentsGraph(
    selected_analysts=["market", "technical", "news", "fundamentals", "social"],
    config=config,
)

state, decision = ta.propagate("AAPL", "2026-04-16")
print(decision)
ta.close()  # Clean up checkpoint connections
```

## Using the Frontend

### Analysis Screen
1. Enter a ticker symbol and click **Analyze**
2. Watch real-time progress as agents complete via SSE streaming
3. Review agent reports in the tabbed panel (Equity | Options | Decision)

### Recommendations Screen
- After analysis, recommendations appear as separate **Equity** and **Options** cards
- Click **Approve** to auto-submit a paper trade to Alpaca (bracket order with TP/SL)
- Click **Skip** to dismiss
- Cards show trade specs, agent consensus, confidence, and countdown timer

### Screener Screen
- Select a screening strategy: Momentum, VCP, CANSLIM, Earnings, Watchlist
- Configure max picks and run the screener
- Click a pick to navigate to the Chart screen for that ticker

### Chart Screen
- TradingView-style candlestick charts with 5 timeframe presets
- Brokerage-style trade sidebar with Market/Limit order type toggle
- Options and equity trades with separate entry flows
- Live price streaming, position P&L tracking
- Chart overlays show entry, stop-loss, and target price lines

### Track Record Screen
- Win rate, expectancy, profit factor, equity curve
- Trade history table with close-reason tracking
- Confidence calibration chart
- Agent performance metrics

## Configuration

Runtime configuration is manageable from the UI (Config sidebar) or via the API:

```bash
# Read all config
curl http://localhost:8000/api/config

# Update a value
curl -X PUT http://localhost:8000/api/config/min_confidence_threshold \
  -H "Content-Type: application/json" \
  -d '{"value": 70}'
```

Key configuration options:
- `min_confidence_threshold` (0-100): Minimum confidence to generate a recommendation
- `stop_loss_pct` (0-50): Default stop-loss percentage
- `max_position_pct` (0-100): Max allocation per trade
- `max_portfolio_exposure_pct` (0-100): Total portfolio exposure limit
- `agent_weight_*` (0.0-1.0): Per-agent weight in the risk judge synthesis
- `watchlist`: JSON array of ticker symbols for custom watchlist screening
- `schedule_time`: Pre-market analysis trigger time (HH:MM, US/Eastern)

## Market Regime & Exposure

The system detects market regime and adjusts recommendations:

```bash
# Current regime
curl http://localhost:8000/api/regime

# Exposure recommendation  
curl http://localhost:8000/api/exposure
```

- **Broadening**: Standard thresholds, full new entries allowed
- **Concentration**: +5 confidence threshold, -15% position sizing
- **Contraction**: +10 confidence threshold, -30% position sizing, REDUCE_ONLY posture
- **CASH_PRIORITY**: No new entries — only exit/hedge recommendations

## Knowledge Wiki

The `wiki/` directory contains an LLM-maintained research knowledge base following [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

- Drop research papers/articles into `knowledgebase/`
- Ask Claude to ingest them — it reads, summarizes, cross-references, and files into the wiki
- Query the wiki for synthesized answers with citations
- `wiki/app-notes/` contains actionable improvements derived from research

Currently ingested: 7 research papers covering options microstructure, retail investor behavior, RL hedging, multi-agent LLM trading, algorithmic collusion, and learning externalities.

## Project Structure

```
agents-for-trades/
  api/                    # FastAPI backend (routes, models, schemas)
  cli/                    # Typer CLI for terminal-based analysis
  frontend/               # React + Vite + TailwindCSS frontend
  tradingagents/
    agents/               # Agent implementations
      analysts/           # 5 equity analysts
      managers/           # Risk manager with regime/exposure gating
      options/            # 7 options pipeline agents
      screener/           # Screener strategies + registry
      utils/              # Signal extraction, aggregation, protocol
    dataflows/            # Data retrieval (yfinance, Tradier, Alpha Vantage)
    execution/            # ExecutionBackend protocol + PaperBackend (Alpaca)
    graph/                # LangGraph orchestration
    llm_clients/          # Multi-provider LLM adapters
    services/             # Regime detection, breadth scoring, exposure, scheduling
  wiki/                   # LLM-maintained knowledge base
  knowledgebase/          # Raw research sources (PDFs, articles)
  tests/                  # Test suite
```

## License

MIT
