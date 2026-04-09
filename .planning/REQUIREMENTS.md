# Requirements: TradingAgents v2.0 Vol-Aware Analysis Pipeline

**Defined:** 2026-04-09
**Core Value:** Every analyst reasons with volatility awareness, producing connected, vol-informed decisions that flow through to the final trade recommendation.

## v2.0 Requirements

### Vol Context Pipeline

- [ ] **VOL-01**: Vol Context node computes IV rank, IV/HV ratio, P/C ratio, and skew narrative from yfinance data
- [ ] **VOL-02**: Vol Context node runs before all equity analysts as a visible graph node in the progress stepper
- [ ] **VOL-03**: Vol Context output stored in `state["vol_context"]` as a narrative paragraph with soft directive
- [ ] **VOL-04**: Vol Context fetch is non-blocking — analysts run without vol context if fetch fails, failure flagged in state

### Analyst Integration

- [ ] **ANALYST-01**: All 5 equity analysts receive vol context narrative in their prompt via `prompt.partial()` injection
- [ ] **ANALYST-02**: System message directive strength varies per analyst role (Market=Strong, Technical/Social=Moderate, News/Fundamentals=Weak)
- [ ] **ANALYST-03**: Each analyst produces a `vol_note` field (1 sentence) referencing how vol context influenced their analysis, extracted via regex

### Options Always-On

- [ ] **OPT-01**: `enable_options` toggle removed from frontend ConfigSidebar — options always enabled
- [ ] **OPT-02**: Backend always runs full options pipeline — no conditional `if enable_options` blocks in setup.py
- [ ] **OPT-03**: `getNodeList()` returns all nodes (equity + options + vol context) unconditionally

### Frontend Restructure

- [ ] **UI-01**: Report tabs grouped into 3 visual sections with headers: Equity (5) | Options (6) | Decision (2)
- [ ] **UI-02**: Collapsible vol context banner pinned at top of every analyst report tab, showing the vol narrative
- [ ] **UI-03**: Progress stepper includes "Vol Context" node as the first node before analysts

## Future Requirements

- **VOL-05**: Structured output enforcement for `vol_note` via function calling (if regex extraction proves unreliable)
- **VOL-06**: Vol regime detection (low/normal/elevated/extreme) with automatic analyst behavior adjustment
- **VOL-07**: Vol context caching across multi-ticker runs (shared market-wide vol context)

## Out of Scope

| Feature | Reason |
|---------|--------|
| LLM-generated vol narrative | Anti-feature — adds latency and token cost for a computable summary; pure Python is faster and deterministic |
| Blocking vol fetch on failure | Anti-feature — would halt entire pipeline for data availability issues |
| Per-analyst divergent vol narratives | Anti-feature — defeats the "connected decisions" goal; all analysts must see identical facts |
| Backtesting the vol-aware pipeline | Deferred to v2.1+; requires historical vol data infrastructure |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| VOL-01 | TBD | Pending |
| VOL-02 | TBD | Pending |
| VOL-03 | TBD | Pending |
| VOL-04 | TBD | Pending |
| ANALYST-01 | TBD | Pending |
| ANALYST-02 | TBD | Pending |
| ANALYST-03 | TBD | Pending |
| OPT-01 | TBD | Pending |
| OPT-02 | TBD | Pending |
| OPT-03 | TBD | Pending |
| UI-01 | TBD | Pending |
| UI-02 | TBD | Pending |
| UI-03 | TBD | Pending |

**Coverage:**
- v2.0 requirements: 13 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 13

---
*Requirements defined: 2026-04-09*
*Last updated: 2026-04-09 after initial definition*
