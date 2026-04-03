# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — Options Pipeline

**Shipped:** 2026-04-02
**Phases:** 7 | **Plans:** 20 | **Sessions:** ~5

### What Was Built
- Complete options trading pipeline: 7 specialist agents (volatility, flow, strategy, strike/expiry, pricing, legs builder, Greeks monitor)
- Tradier + yfinance dual-vendor options data infrastructure with automatic rate-limit fallback
- Stdlib-only Black-Scholes pricing (no scipy dependency)
- Parallel options branch in LangGraph StateGraph alongside equity agents
- Options-aware debators and Risk Manager with 5 enforcement rules
- React + FastAPI visual frontend with SSE streaming, dark mode

### What Worked
- Autonomous phase execution (`/gsd:autonomous --from 4`) completed 4 phases without manual intervention
- TDD pattern consistently caught issues early (stale closure bug in useAnalysis hook found during test writing)
- Factory function pattern (`create_*`) made all agents testable in isolation with mocked LLMs
- Vendor abstraction pattern from equity data translated cleanly to options data
- Wave-based parallelization in planning/execution kept phases moving efficiently

### What Was Inefficient
- Some SUMMARY.md one-liners were empty ("One-liner:") due to summary-extract not finding the field — polluted MILESTONES.md auto-generation
- Phase 4 verifier ran out of tokens on first attempt (recovered with fresh session)
- STATE.md got stale (showed phases 2-6 as "not started" when all were complete) — not updated during autonomous execution
- Tailwind v4 dark mode required `@variant dark` directive that wasn't in the original plan — caught only during manual testing

### Patterns Established
- LangGraph node names use dash separator ("Options - X") to avoid colon restriction
- Angle-bracket placeholders in LLM system prompts avoid LangChain curly-brace template conflicts
- Dual-format leg parser pattern (Phase 4 + Phase 3 formats) for backward compatibility
- `_parse_tabular_string` duplicated per module to keep agents independently importable
- asyncio.Queue bridge pattern for sync-to-async thread-safe SSE streaming

### Key Lessons
1. Tailwind v4 dark mode defaults to `prefers-color-scheme` — class-based toggle needs explicit `@variant dark` in CSS
2. useRef is essential for mutable state in EventSource callbacks to avoid stale closures in React hooks
3. LangGraph reserves ':' in node names — discovered only at runtime, not in docs
4. Zero mid price (bid=ask=0) should be flagged as worst-case (WIDE_SPREAD=True), not silently ignored

### Cost Observations
- Model mix: ~30% opus (planning, verification), ~70% sonnet (execution, research)
- Sessions: ~5 sessions across 3 days
- Notable: Autonomous mode completed 4 phases in a single session — high efficiency for well-defined phases

---

## Milestone: v1.1 — Stock Recommendation System

**Shipped:** 2026-04-03
**Phases:** 5 | **Plans:** 7 | **Sessions:** ~2

### What Was Built
- Screener data layer: chunked yfinance bulk fetch, composite scoring (volume/momentum/unusual activity), NYSE session-boundary cache with 15-min TTL
- LLM screener agent: Pydantic-validated structured output, retry/degradation on malformed JSON, AgentState isolation guard
- POST /api/screen endpoint: async execution via asyncio.to_thread, independent from analysis SSE stream
- React screener tab: WatchlistPanel with PickCard score bars, stale indicator, skeleton loading, select-to-analyze prefill flow
- CLI screen subcommand: Rich table with 7 columns, --max-picks/--json flags

### What Worked
- Full autonomous execution (`/gsd:autonomous --from 8`) completed all 5 phases with minimal intervention
- Phase verifier caught missing `cli/__main__.py` — gap closure was trivial (2 lines) and inline fix avoided a full gap-closure cycle
- TDD approach in Phases 8-10 and 12 consistently caught issues before they compounded
- Separate APIRouter pattern for screener kept SSE stream completely independent (verified by AST-based test)
- Integration checker confirmed all cross-phase wiring in a single pass

### What Was Inefficient
- SUMMARY.md `summary-extract` still produces garbled one-liners — MILESTONES.md required manual cleanup
- Phase 11 VALIDATION.md not Nyquist-compliant (no test framework for frontend) — frontend remains manually-tested only
- VENDOR_METHODS routing registered for screener but unused by primary consumer (screener_agent uses direct import) — overhead without benefit in v1.1
- Phase 11 verification deferred 4 human items that still haven't been tested in browser

### Patterns Established
- `SCORE_BAR_COLOR` static lookup in PickCard avoids Tailwind v4 dynamic class issues
- `useReducer` with typed action discriminated union for complex hook state (useScreener)
- Lazy imports inside FastAPI handler body to avoid startup crashes on missing API keys
- `_validate_not_agent_state()` sentinel guard pattern for type isolation between pipeline outputs

### Key Lessons
1. `cli/__main__.py` is required for `python -m package` invocation — easy to miss when existing CLI uses `python cli/main.py` directly
2. Typer stores `cmd.name = None` when `@app.command()` is called without explicit `name=` — tests checking command names need fallback to `cmd.callback.__name__`
3. Tailwind v4 dynamic classes (e.g., `bg-${color}-500`) don't work — must use static lookup objects with pre-defined class strings
4. Frontend phases without a test framework create persistent Nyquist gaps — consider adding Vitest for v1.2

### Cost Observations
- Model mix: ~25% opus (planning, verification, orchestration), ~75% sonnet (execution, research, integration checks)
- Sessions: ~2 sessions across 2 days
- Notable: Phase 12 (simple CLI command) executed fastest — single plan, single task, minimal cross-phase coupling

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~5 | 7 | First milestone; autonomous execution from Phase 4 onward |
| v1.1 | ~2 | 5 | Full autonomous execution; inline gap closure; integration checker |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | 174 | N/A | 1 (Black-Scholes via math.erf) |
| v1.1 | 203 | N/A | 1 (exchange-calendars for NYSE sessions) |

### Top Lessons (Verified Across Milestones)

1. Autonomous execution works well for phases with clear requirements and existing patterns
2. Manual visual verification catches CSS/framework configuration issues that automated tests miss
3. SUMMARY.md one-liner extraction is unreliable — MILESTONES.md auto-generation needs manual review
4. Frontend without test framework creates persistent verification gaps across milestones
