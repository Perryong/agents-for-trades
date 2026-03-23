# TradingAgents (agents-for-trades)

Multi-agent LLM trading analysis framework built with LangGraph.

This project orchestrates a team of analyst, researcher, trader, and risk agents to generate a final trade decision for a ticker on a target date.

## What It Does

- Runs a configurable multi-stage analysis pipeline:
  - Analyst Team: market, technical, social, news, fundamentals
  - Research Team: bull vs bear debate + research manager judgment
  - Trading Team: trader plan generation
  - Risk Management: aggressive/conservative/neutral debate + portfolio judgment
- Supports multiple LLM providers:
  - OpenAI, Anthropic, Google, xAI, OpenRouter, Ollama
- Supports provider-level model selection for both:
  - quick-think model (fast steps)
  - deep-think model (manager/judge steps)
- Routes data tools through abstract interfaces (stock, technicals, fundamentals, news)
- Provides an interactive rich CLI for live run progress and report output

## Project Layout

- `cli/`
  - `main.py`: Typer CLI app entrypoint (`tradingagents analyze`)
  - `utils.py`: interactive prompts for ticker/date/models/provider/depth
  - `stats_handler.py`: callback metrics for LLM/tool usage
- `tradingagents/`
  - `default_config.py`: default runtime config
  - `graph/`
    - `trading_graph.py`: orchestration facade (`TradingAgentsGraph`)
    - `setup.py`: LangGraph node/edge wiring
    - `conditional_logic.py`: flow control for tool calls/debate loops
    - `propagation.py`: initial graph state + invoke args
    - `reflection.py`: memory/reflection update hooks
    - `signal_processing.py`: parse final decision signal
  - `agents/`: role-specific agent implementations
  - `agents/utils/agent_utils.py`: abstract tool exports consumed by graph
  - `dataflows/`: vendor-backed data retrieval (yfinance/alpha_vantage)
  - `llm_clients/`: provider adapters and model validation
- `main.py`: programmatic example run (non-CLI)
- `test.py`: local performance test helper for dataflow function

## Execution Flow

```text
START
  -> Selected Analyst Nodes (sequential, tool-call loop per analyst)
  -> Bull Researcher <-> Bear Researcher (debate rounds)
  -> Research Manager
  -> Trader
  -> Aggressive/Conservative/Neutral Risk Debate (rounds)
  -> Risk Judge (Portfolio decision)
  -> END
```

Flow implementation is defined in `tradingagents/graph/setup.py` and controlled by `tradingagents/graph/conditional_logic.py`.

## Requirements

- Python 3.10+
- API key(s) for your selected provider (except local Ollama)
- Windows/macOS/Linux terminal with UTF-8 support (Rich output)

## Installation

### 1) Create and activate a virtual environment

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

Optional editable install (enables `tradingagents` console script from `pyproject.toml`):

```bash
pip install -e .
```

## Environment Variables

The project loads `.env` automatically in both `main.py` and `cli/main.py`.

Set variables based on your chosen provider:

- OpenAI: `OPENAI_API_KEY`
- Anthropic: `ANTHROPIC_API_KEY`
- Google: `GOOGLE_API_KEY`
- xAI: `XAI_API_KEY`
- OpenRouter: `OPENROUTER_API_KEY`
- Optional output override: `TRADINGAGENTS_RESULTS_DIR`

Example `.env`:

```env
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_google_key
XAI_API_KEY=your_xai_key
OPENROUTER_API_KEY=your_openrouter_key
TRADINGAGENTS_RESULTS_DIR=./results
```

Only include keys for providers you actually use.

## Running

### Interactive CLI (recommended)

If installed editable:

```bash
tradingagents analyze
```

Or run directly:

```bash
python -m cli.main analyze
```

During CLI run, you will be prompted for:

- ticker symbol
- analysis date
- analyst subset
- research depth (affects debate loop counts)
- LLM provider
- quick-think model
- deep-think model
- provider-specific reasoning/thinking mode

### Programmatic run (example script)

```bash
python main.py
```

This path uses `TradingAgentsGraph.propagate(...)` directly and prints final decision.

## Output Artifacts

### CLI outputs

Default base: `./results` (or `TRADINGAGENTS_RESULTS_DIR`)

Per run:

- `results/<TICKER>/<YYYY-MM-DD>/message_tool.log`
- `results/<TICKER>/<YYYY-MM-DD>/reports/*.md`
- Optional saved full report folder from post-run prompt

### Graph state logs (programmatic `propagate` path)

- `eval_results/<TICKER>/TradingAgentsStrategy_logs/full_states_log_<DATE>.json`

## Configuration Model

Default configuration lives in `tradingagents/default_config.py`.

Notable keys:

- `llm_provider`
- `quick_think_llm`
- `deep_think_llm`
- `backend_url`
- `max_debate_rounds`
- `max_risk_discuss_rounds`
- `max_recur_limit`
- `data_vendors` (category-level vendor routing)
- `tool_vendors` (per-tool override)

Example override (Python):

```python
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "openai"
config["quick_think_llm"] = "gpt-5-mini"
config["deep_think_llm"] = "gpt-5.2"
config["max_debate_rounds"] = 3
config["max_risk_discuss_rounds"] = 3

ta = TradingAgentsGraph(
    selected_analysts=["market", "technical", "news"],
    debug=True,
    config=config,
)

state, decision = ta.propagate("NVDA", "2026-03-22")
print(decision)
```

## Data Vendor Routing

Tool calls are abstracted in `tradingagents/agents/utils/agent_utils.py` and resolved through `tradingagents/dataflows/`.

Defaults are yfinance-based in `default_config.py`. You can switch categories/tools to alpha_vantage where supported.

## Troubleshooting

- Provider auth errors:
  - Verify correct API key environment variable for selected provider.
- Model not accepted by provider:
  - Check model/provider pairing in `tradingagents/llm_clients/validators.py` and CLI selection.
- Local Ollama issues:
  - Ensure Ollama server is running at `http://localhost:11434/v1`.
- Empty/partial reports:
  - Increase research depth to allow more debate rounds.

## Development Notes

- Package script entrypoint is defined in `pyproject.toml`:
  - `tradingagents = "cli.main:app"`
- For quick experimentation, `main.py` is the easiest direct entry.
- `test.py` is a lightweight local dataflow performance test, not a formal test suite.

## License

No license file is currently present in this repository. Add one if you plan to distribute publicly.
