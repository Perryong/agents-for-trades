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

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~5 | 7 | First milestone; autonomous execution from Phase 4 onward |

### Cumulative Quality

| Milestone | Tests | Coverage | Zero-Dep Additions |
|-----------|-------|----------|-------------------|
| v1.0 | 174 | N/A | 1 (Black-Scholes via math.erf) |

### Top Lessons (Verified Across Milestones)

1. Autonomous execution works well for phases with clear requirements and existing patterns
2. Manual visual verification catches CSS/framework configuration issues that automated tests miss
