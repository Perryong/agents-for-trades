# Phase 12: CLI Integration - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a `screen` subcommand to the existing Typer CLI that runs the screener and displays ranked picks in a Rich table. This phase delivers the CLI command only — no backend changes, no frontend changes.

</domain>

<decisions>
## Implementation Decisions

### CLI Command Design
- Command name: `screen` — invoked as `python -m cli screen`
- Flags: `--max-picks N` (default 5, hard cap 10) and `--json` for machine-readable output
- Table columns: Ticker, Score, Confidence, Rationale (truncated to ~60 chars), Volume, Momentum, Sector

### Output & Integration
- Rich spinner "Screening market..." during screening — consistent with existing CLI spinner usage
- Errors displayed in Rich panel with error message and suggestion — matches existing CLI error style
- Command added to `cli/main.py` as a new `@app.command()` — follows existing Typer pattern

### Claude's Discretion
- Exact Rich table styling (colors, borders, alignment)
- Rationale truncation method
- JSON output format details

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cli/main.py` — Typer app with `@app.command()` pattern, Rich console, spinner usage
- `cli/utils.py` — CLI utility functions
- `tradingagents/agents/screener/screener_agent.py` — `run_screener(config, llm)` returns `ScreenerResult`
- `tradingagents/default_config.py` — `DEFAULT_CONFIG` for config dict
- `tradingagents/llm_clients/factory.py` — `create_llm_client()` for LLM instantiation

### Established Patterns
- Typer commands use `@app.command()` decorator in cli/main.py
- Rich tables use `Table()` with `add_column()` / `add_row()`
- Rich spinners via `with Live(Spinner(...))` or `console.status()`
- Config built from DEFAULT_CONFIG + overrides

### Integration Points
- Phase 9: `run_screener(config, llm)` — same function used by API endpoint
- `cli/main.py` — add new command alongside existing `analyze` command

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>
