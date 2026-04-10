# Phase 1: Multi-Expiry Options Data for Flow & Vol Analysts — Research

**Researched:** 2026-04-10
**Domain:** Python options agent refactor — multi-timeframe chain fetching, term structure metrics
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Reuse `strike_expiry_selector`'s `DTE_BUCKETS` pattern: Short-term (0-5 DTE), Weekly (5-14 DTE), Monthly (14-45 DTE), Longer-term (45-90 DTE)
- Extract `DTE_BUCKETS` to a shared constant (currently defined inside `strike_expiry_selector.create_strike_expiry_selector`)
- Each agent fetches one chain per bucket (closest-to-center expiry), same selection logic as `strike_expiry_selector`
- `options_flow_analyst`: compute flow metrics (P/C ratio, unusual activity, net bias) per DTE bucket; nearest expiry remains "primary" bucket for backward compatibility; report includes per-bucket breakdown
- `volatility_analyst`: compute IV rank/percentile and skew metrics per DTE bucket (not just nearest + furthest); term structure analysis becomes concrete with actual chain data per bucket; `get_historical_iv` stays as-is
- Both agents include a "Term Structure Summary" section in their LLM prompt output
- Per-bucket metrics are clearly labeled with DTE range and expiry date
- Buckets with no available expiry are noted as "No data" (not silently omitted)

### Claude's Discretion
- Exact formatting of per-bucket sections in the report
- Whether to parse all bucket chains into DataFrames or only the ones with data
- Error handling for individual bucket fetch failures (should not block other buckets)

### Deferred Ideas (OUT OF SCOPE)
- Improving yfinance IV quality for same-day expiry (upstream data issue)
- Filtering out deep ITM strikes with unreliable IVs before passing to LLM
- Adding strategy-specific recommendation logic to the final decision agent
</user_constraints>

---

## Summary

This phase expands two existing options analyst agents (`options_flow_analyst` and `volatility_analyst`) to fetch options chains across multiple DTE buckets instead of one or two hard-coded expirations. The pattern already exists and works in `strike_expiry_selector` — the task is to extract the shared `DTE_BUCKETS` constant and replicate the bucket-selection loop in both analyst agents.

The data layer (`route_to_vendor` → `get_options_chain`, `get_options_expirations`) requires no changes. The caching layer (`yfinance_cache.get_cached_text`) handles deduplication automatically — fetching the same expiry across multiple agents in the same run hits the 30-minute cache. The main work is: (1) create `tradingagents/agents/options/constants.py`, (2) refactor `options_flow_analyst` to loop across buckets and build per-bucket flow metrics, (3) refactor `volatility_analyst` to loop across buckets and build per-bucket IV/skew metrics with a proper 4-point term structure, (4) update the LLM prompts and data templates for both agents to include the new "Term Structure Summary" section, (5) update existing tests to cover multi-bucket behavior.

**Primary recommendation:** Implement the bucket loop in both agents following the `strike_expiry_selector` pattern exactly. Extract `DTE_BUCKETS` to `constants.py` first, then update each agent independently. Keep the primary bucket (nearest expiry) as the first bucket so existing tests that only check for the presence of the report key remain valid.

---

## Standard Stack

### Core (no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | already installed | DataFrame operations, per-bucket metric aggregation | Already used throughout all agents |
| yfinance | already installed | Options chain data via `get_options_chain` | Project's primary options data vendor |

No new pip installs required. All work is Python-only refactoring within existing modules.

---

## Architecture Patterns

### Recommended Project Structure (additions only)
```
tradingagents/agents/options/
├── constants.py              # NEW: DTE_BUCKETS shared constant
├── strike_expiry_selector.py # Remove local DTE_BUCKETS, import from constants
├── options_flow_analyst.py   # Refactor: bucket loop, per-bucket metrics
└── volatility_analyst.py     # Refactor: bucket loop, per-bucket IV/skew
```

### Pattern 1: DTE_BUCKETS Shared Constant

**What:** Move the `DTE_BUCKETS` list from inside `create_strike_expiry_selector` to a module-level constant in `constants.py`. Import it in all three agent files.

**What it contains (from `strike_expiry_selector.py` lines 265-270 — authoritative source):**
```python
# tradingagents/agents/options/constants.py
DTE_BUCKETS = [
    {"label": "Short-term (0-5 DTE)", "min": 0, "max": 5, "tag": "SHORT"},
    {"label": "Weekly (5-14 DTE)", "min": 5, "max": 14, "tag": "WEEKLY"},
    {"label": "Monthly (14-45 DTE)", "min": 14, "max": 45, "tag": "MONTHLY"},
    {"label": "Longer-term (45-90 DTE)", "min": 45, "max": 90, "tag": "LONGER"},
]
```

**When to use:** Import this from `constants.py` in `strike_expiry_selector.py`, `options_flow_analyst.py`, and `volatility_analyst.py`.

### Pattern 2: Bucket Expiry Selection (from strike_expiry_selector — authoritative)

**What:** For each bucket, filter `exp_with_dte` list to the bucket's DTE range, then pick the expiry whose DTE is closest to the bucket's center point.

```python
# Source: tradingagents/agents/options/strike_expiry_selector.py lines 340-353
from datetime import date
from tradingagents.agents.options.constants import DTE_BUCKETS

trade_date = date.fromisoformat(trade_date_str)

exp_with_dte = []
for exp_str in expirations:
    try:
        exp_date = date.fromisoformat(exp_str)
        dte = (exp_date - trade_date).days
        if dte >= 0:
            exp_with_dte.append((exp_str, dte))
    except (ValueError, TypeError):
        continue

for bucket in DTE_BUCKETS:
    bucket_expiries = [
        (exp, dte) for exp, dte in exp_with_dte
        if bucket["min"] <= dte <= bucket["max"]
    ]
    if not bucket_expiries:
        # Note "No data" for this bucket — do NOT silently skip
        continue

    center = (bucket["min"] + bucket["max"]) / 2.0
    best_exp, best_dte = min(bucket_expiries, key=lambda x: abs(x[1] - center))

    chain_str = route_to_vendor("get_options_chain", ticker, best_exp)
    chain_df = _parse_tabular_string(chain_str)
    # ... compute metrics for this bucket
```

### Pattern 3: Per-Bucket Flow Metrics (options_flow_analyst)

**What:** Call the existing `_compute_flow_metrics(chain_df)` for each bucket's chain. Accumulate results in a list of dicts, one per bucket.

**Current `_compute_flow_metrics` signature (options_flow_analyst.py line 85):**
```python
def _compute_flow_metrics(chain_df: pd.DataFrame) -> dict:
    # Returns: pc_ratio, unusual_count, unusual_top3, net_bias,
    #          total_call_vol, total_put_vol
```

The function is already correct — it operates on a single chain DataFrame. No changes to `_compute_flow_metrics` itself; only the calling code in `options_flow_analyst_node` changes.

**Data content template structure for LLM (new):**
```
Ticker: {ticker}
Analysis date: {trade_date}

## Term Structure Flow Summary

### Short-term (0-5 DTE) — {best_exp} ({best_dte} DTE)
- P/C Ratio: {pc_ratio_str}
- Unusual activity: {unusual_count} contracts
- Net bias: {net_bias}

### Weekly (5-14 DTE) — {best_exp} ({best_dte} DTE)
...

### Monthly (14-45 DTE) — [No data]
...

Primary expiry (nearest bucket): {primary_exp}
Write the flow analysis report for {ticker} on {trade_date}.
```

### Pattern 4: Per-Bucket IV/Skew Metrics (volatility_analyst)

**What:** For each bucket, fetch the chain and compute: median IV (as bucket IV), skew (using existing `_compute_skew`). Replace the current near/far two-point term structure with a four-point structure using the bucket median IVs.

**Current term structure (volatility_analyst.py lines 213-246):**
```python
def _compute_term_structure(near_chain_df, far_chain_df) -> str:
    # Uses near_chain_df["iv"].median() vs far_chain_df["iv"].median()
```

**New approach:** Replace `_compute_term_structure(near_chain_df, far_chain_df)` with a new helper `_compute_multi_bucket_term_structure(bucket_results: list) -> str` that takes the list of `{"label", "median_iv", "dte"}` dicts and builds a narrative describing the shape across all four buckets.

**Alternatively (simpler):** Keep `_compute_term_structure` but use the SHORT bucket as "near" and the longest available bucket as "far". Add a separate "Bucket IV Table" string showing all four bucket IVs for the LLM. The CONTEXT.md says "term structure analysis becomes concrete" — a four-row table serves this purpose without requiring a new helper signature.

**Data content template additions for LLM (new):**
```
## Term Structure (per DTE bucket)
| Bucket | Expiry | DTE | Median IV | Skew |
|--------|--------|-----|-----------|------|
| Short-term (0-5 DTE) | {exp} | {dte} | {iv} | {skew} |
| Weekly (5-14 DTE)    | {exp} | {dte} | {iv} | {skew} |
| Monthly (14-45 DTE)  | No data | — | — | — |
| Longer-term (45-90 DTE) | {exp} | {dte} | {iv} | {skew} |

Near IV (SHORT bucket): {near_iv}
Far IV (LONGER bucket): {far_iv}
Term structure shape: {contango/backwardation/flat}
```

### Pattern 5: Error Isolation Per Bucket (Claude's Discretion)

**What:** Any individual bucket's chain fetch failure (network error, parse failure, empty chain) must not block the other buckets. Wrap each bucket's fetch+compute in try/except.

```python
for bucket in DTE_BUCKETS:
    try:
        chain_str = route_to_vendor("get_options_chain", ticker, best_exp)
        chain_df = _parse_tabular_string(chain_str)
        if chain_df is None or chain_df.empty:
            bucket_results.append({"label": bucket["label"], "error": "No chain data"})
            continue
        metrics = _compute_flow_metrics(chain_df)
        bucket_results.append({"label": bucket["label"], "expiry": best_exp,
                                "dte": best_dte, **metrics})
    except Exception as e:
        bucket_results.append({"label": bucket["label"], "error": str(e)})
```

### Anti-Patterns to Avoid

- **Silent bucket omission:** The spec says "Buckets with no available expiry are noted as 'No data' (not silently omitted)." Do not use `continue` without adding a "No data" entry to the report.
- **Changing the return key:** Both agents must still return `{"options_flow_report": ...}` and `{"volatility_report": ...}`. Do not add new state keys.
- **Modifying the data layer:** `get_options_chain`, `get_options_expirations`, `get_historical_iv` signatures and caching behavior stay untouched.
- **Adding LLM calls per bucket:** The single-LLM-call architecture is a project pattern. All Python metrics are pre-computed, then one LLM call writes the narrative. Do not add per-bucket LLM calls.
- **Breaking `_compute_term_structure`:** If other tests call it directly, keep the two-argument signature. Add the multi-bucket helper as a new function rather than replacing the existing one.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bucket expiry selection | Custom binary search or date arithmetic | The exact pattern from `strike_expiry_selector` lines 340-353 | Already battle-tested with yfinance expirations format; handles edge cases |
| Chain parsing | Custom CSV parser | `_parse_tabular_string` (already in each agent file) | Handles `# SPOT:` metadata line, sentinel strings, whitespace-separated format |
| IV median calculation | Custom numpy percentile | `chain_df["iv"].median()` (pandas) | Already used in `_compute_term_structure` |
| Skew computation | New OTM IV comparator | `_compute_skew(chain_df)` (already in `volatility_analyst.py`) | Delta-based primary path with moneyness fallback already implemented |
| Cache deduplication | Custom request deduplication | `yfinance_cache.get_cached_text` (already active) | Fetching the same expiry twice in one run hits the 30-minute cache |

**Key insight:** The entire fetching pattern, chain parsing, and metric computation already exist and are tested. The planner should plan tasks that wire them together, not rebuild them.

---

## Common Pitfalls

### Pitfall 1: Fetching All Bucket Chains on Every Analysis Run (Performance)
**What goes wrong:** Four `get_options_chain` calls per agent × 2 agents = up to 8 chain fetches per analysis. Without caching awareness, this seems expensive.
**Why it happens:** Developer doesn't realize `yfinance_cache` deduplicates identical (symbol, expiry) pairs within the 30-minute TTL window.
**How to avoid:** The `get_cached_text` cache in `yfinance_cache.py` deduplicates automatically. `strike_expiry_selector` already fetches 4 chains per run and works fine. No special optimization needed.
**Warning signs:** Worrying about this and adding manual deduplication caches that shadow the existing one.

### Pitfall 2: DTE_BUCKETS Overlap at Boundary Values
**What goes wrong:** A 5-DTE expiry could match both "Short-term (0-5 DTE)" and "Weekly (5-14 DTE)" because both use inclusive range checks (`min <= dte <= max`).
**Why it happens:** The CONTEXT.md `DTE_BUCKETS` definition uses `"min": 5, "max": 5` for short-term and `"min": 5` for weekly.
**How to avoid:** The existing `strike_expiry_selector` implementation uses `bucket["min"] <= dte <= bucket["max"]` — a 5-DTE expiry goes into BOTH buckets. This is intentional: the center-distance selection then picks the closer expiry per bucket. Follow the existing code exactly — don't try to "fix" the boundary.
**Warning signs:** Changing boundary conditions to `<` instead of `<=`.

### Pitfall 3: Breaking Existing Tests When Signature of `_compute_term_structure` Changes
**What goes wrong:** `test_volatility_analyst.py` directly imports `_compute_term_structure` and tests it with `(near_df, far_df)` args. If you replace the function signature, 3 tests break.
**Why it happens:** The existing tests (`test_term_structure_contango`, `test_term_structure_backwardation`, `test_term_structure_returns_na_for_none`) call the function directly.
**How to avoid:** Keep `_compute_term_structure(near_chain_df, far_chain_df)` intact. Add `_compute_multi_bucket_term_structure(bucket_results)` as a new function. Use the new one in the node, keep the old one for backward compat and existing tests.
**Warning signs:** Removing `_compute_term_structure` entirely.

### Pitfall 4: The Short-Term (0-5 DTE) Bucket Has Known Data Quality Issues
**What goes wrong:** Same-day expiry (0 DTE) causes yfinance to return `iv=0.000010` for many contracts. The `MIN_IV_THRESHOLD = 0.005` in `y_finance_options.py` correctly rejects these, causing `None` Greeks. The `_compute_skew` function may return "N/A" for this bucket.
**Why it happens:** Black-Scholes breaks down for very short time-to-expiry with near-zero IV values (documented in CONTEXT.md).
**How to avoid:** This is expected behavior. Do not attempt to fix it in this phase (deferred). When a bucket's skew or median IV is "N/A", note it as "N/A" in the report. The LLM will handle the narrative appropriately.
**Warning signs:** Adding special IV filtering or skew computation for 0-DTE chains.

### Pitfall 5: `volatility_analyst` Imports `yfinance` Directly
**What goes wrong:** The `_compute_hv30` function in `volatility_analyst.py` imports `yfinance` at the module level (`import yfinance as yf`). Tests mock `yf` via `patch("tradingagents.agents.options.volatility_analyst.yf", mock_yf)`. New tests for multi-bucket behavior must continue to mock `yf` the same way.
**Why it happens:** Historical volatility uses price history, not options chain data, and is not routed through `route_to_vendor`.
**How to avoid:** Keep `_compute_hv30` unchanged. New tests that exercise the multi-bucket node must include the `yf` mock.

### Pitfall 6: `options_flow_analyst` Builds the LLM Data String Inline
**What goes wrong:** The current code in `options_flow_analyst_node` builds the `data_content` string inline with f-strings (lines 251-260). When adding per-bucket sections, this grows complex and error-prone.
**Why it happens:** Unlike `volatility_analyst` which uses a `DATA_TEMPLATE` constant, `options_flow_analyst` has no template.
**How to avoid:** Either introduce a `_build_flow_data_content(ticker, trade_date, bucket_results)` helper that returns the multi-bucket string, keeping the node function clean. Or use a DATA_TEMPLATE with a `{bucket_sections}` placeholder. Either works — this falls under Claude's Discretion.

---

## Code Examples

### Existing working bucket loop (authoritative reference)
```python
# Source: tradingagents/agents/options/strike_expiry_selector.py lines 340-408
for bucket in DTE_BUCKETS:
    bucket_expiries = [
        (exp, dte) for exp, dte in exp_with_dte
        if bucket["min"] <= dte <= bucket["max"]
    ]
    if not bucket_expiries:
        report_sections.append(
            f"\n### {bucket['label']}\nNo expirations available in this window."
        )
        continue

    center = (bucket["min"] + bucket["max"]) / 2.0
    best_exp, best_dte = min(bucket_expiries, key=lambda x: abs(x[1] - center))

    chain_str = route_to_vendor("get_options_chain", ticker, best_exp)
    chain_df = _parse_tabular_string(chain_str)

    if chain_df is None or chain_df.empty:
        report_sections.append(
            f"\n### {bucket['label']}\nNo chain data for {best_exp} ({best_dte} DTE)."
        )
        continue
    # ... process chain_df
```

### Existing flow metrics function (no changes needed)
```python
# Source: tradingagents/agents/options/options_flow_analyst.py line 85
def _compute_flow_metrics(chain_df: pd.DataFrame) -> dict:
    # Returns: pc_ratio, unusual_count, unusual_top3, net_bias,
    #          total_call_vol, total_put_vol
```

### Existing skew function (no changes needed)
```python
# Source: tradingagents/agents/options/volatility_analyst.py line 156
def _compute_skew(chain_df: Optional[pd.DataFrame]) -> str:
    # Delta-based primary, moneyness-quartile fallback
    # Returns: "Put skew elevated (+X.XX%)" | "Call skew elevated" | "Flat skew" | "N/A"
```

### Existing term structure function (keep, do not remove)
```python
# Source: tradingagents/agents/options/volatility_analyst.py line 213
def _compute_term_structure(near_chain_df, far_chain_df) -> str:
    # Used by 3 existing tests — keep intact
```

### New multi-bucket term structure helper (add alongside existing)
```python
def _compute_multi_bucket_term_structure(bucket_results: list) -> str:
    """Build a term structure description from per-bucket median IV values.

    bucket_results: list of dicts, each with keys:
        label (str), median_iv (float | None), dte (int)
    Returns a markdown table string for inclusion in LLM data content.
    """
    lines = ["| Bucket | DTE | Median IV | Skew |",
             "|--------|-----|-----------|------|"]
    for b in bucket_results:
        iv_str = f"{b['median_iv']:.1%}" if b.get("median_iv") else "N/A"
        skew_str = b.get("skew", "N/A")
        lines.append(
            f"| {b['label']} | {b.get('dte', '—')} | {iv_str} | {skew_str} |"
        )
    return "\n".join(lines)
```

### Test pattern for multi-bucket node (follows existing style)
```python
# Source pattern: tests/agents/test_options_flow_analyst.py
def _make_route_side_effect_multi_bucket(expirations=None, chain_str=VALID_CHAIN_STR):
    if expirations is None:
        expirations = ["2026-04-11", "2026-04-17", "2026-05-16", "2026-07-18"]
        # ^--- 1 DTE, 7 DTE, 36 DTE, 99 DTE — covers SHORT, WEEKLY, MONTHLY, outside LONGER

    def _side_effect(method, *args, **kwargs):
        if method == "get_options_expirations":
            return expirations
        elif method == "get_options_chain":
            return chain_str
        return ""

    return _side_effect
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | none detected (run from project root) |
| Quick run command | `pytest tests/agents/test_options_flow_analyst.py tests/agents/test_volatility_analyst.py -x -q` |
| Full suite command | `pytest tests/ -x -q --ignore=tests/graph` |

### Phase Requirements → Test Map

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| `options_flow_analyst` returns `options_flow_report` with per-bucket sections | unit | `pytest tests/agents/test_options_flow_analyst.py -x -q` | Partial — existing tests cover single-expiry; new tests needed for multi-bucket |
| `volatility_analyst` returns `volatility_report` with 4-bucket IV table | unit | `pytest tests/agents/test_volatility_analyst.py -x -q` | Partial — existing tests cover near+far; new tests needed for multi-bucket |
| Bucket with no available expiry is noted as "No data" (not silently omitted) | unit | `pytest tests/agents/test_options_flow_analyst.py::test_missing_bucket_noted -x` | No — Wave 0 gap |
| Individual bucket fetch failure does not block other buckets | unit | `pytest tests/agents/test_options_flow_analyst.py::test_bucket_fetch_failure_isolated -x` | No — Wave 0 gap |
| `DTE_BUCKETS` exported from `constants.py` and matches expected 4 entries | unit | `pytest tests/agents/test_constants.py -x` | No — Wave 0 gap |
| Existing single-expiry tests still pass (backward compatibility) | unit | `pytest tests/agents/test_options_flow_analyst.py tests/agents/test_volatility_analyst.py -x` | Yes — existing |
| `_compute_term_structure(near, far)` signature unchanged | unit | `pytest tests/agents/test_volatility_analyst.py::test_term_structure_contango -x` | Yes — existing |

### Sampling Rate
- **Per task commit:** `pytest tests/agents/test_options_flow_analyst.py tests/agents/test_volatility_analyst.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q --ignore=tests/graph`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/agents/test_constants.py` — verify `DTE_BUCKETS` exported correctly with 4 entries
- [ ] `tests/agents/test_options_flow_analyst.py::test_multi_bucket_sections_present` — verify per-bucket labels appear in output
- [ ] `tests/agents/test_options_flow_analyst.py::test_missing_bucket_noted_as_no_data` — verify "No data" string for empty bucket
- [ ] `tests/agents/test_options_flow_analyst.py::test_bucket_fetch_failure_isolated` — verify one bucket's exception doesn't crash node
- [ ] `tests/agents/test_volatility_analyst.py::test_multi_bucket_iv_table_present` — verify 4-bucket table in data content
- [ ] `tests/agents/test_volatility_analyst.py::test_missing_bucket_noted_in_vol_report` — verify "No data" in vol report for empty bucket

---

## Key Implementation Facts

### File Change Map

| File | Change Type | What Changes |
|------|-------------|--------------|
| `tradingagents/agents/options/constants.py` | CREATE | `DTE_BUCKETS` constant |
| `tradingagents/agents/options/strike_expiry_selector.py` | EDIT | Remove local `DTE_BUCKETS`, import from `constants` |
| `tradingagents/agents/options/options_flow_analyst.py` | EDIT | Replace `expirations[0]` single-fetch with bucket loop; update `data_content` |
| `tradingagents/agents/options/volatility_analyst.py` | EDIT | Replace `expirations[0]` and `expirations[-1]` fetches with bucket loop; add `_compute_multi_bucket_term_structure`; update `DATA_TEMPLATE` |
| `tests/agents/test_options_flow_analyst.py` | EDIT | Add multi-bucket tests |
| `tests/agents/test_volatility_analyst.py` | EDIT | Add multi-bucket tests |
| `tests/agents/test_constants.py` | CREATE | DTE_BUCKETS structure tests |

**Files that do NOT change:**
- `tradingagents/dataflows/y_finance_options.py` — no data layer changes
- `tradingagents/dataflows/interface.py` — no routing changes
- `tradingagents/agents/options/options_pricing_agent.py` — reads `options_legs` state, not flow/vol reports
- `tradingagents/agents/options/options_legs_builder.py` — reads `options_legs` state
- `tradingagents/agents/options/greeks_monitor.py` — reads `options_legs` state

### Current State Confirmed by Code Audit

**`options_flow_analyst.py` line 201:**
```python
chain_str: str = route_to_vendor("get_options_chain", ticker, expirations[0])
```
This single fetch becomes the bucket loop. The `_compute_flow_metrics` function requires no changes.

**`volatility_analyst.py` lines 297-300:**
```python
if expirations:
    near_chain_str = route_to_vendor("get_options_chain", ticker, expirations[0])
    if len(expirations) > 1:
        far_chain_str = route_to_vendor("get_options_chain", ticker, expirations[-1])
```
These two fetches become the bucket loop. `_compute_skew` and `_compute_term_structure` helpers are reused.

**`strike_expiry_selector.py` lines 265-270:** `DTE_BUCKETS` defined inside factory function — must be moved to module level in `constants.py` and imported.

### Downstream Agent Impact Assessment

`options_pricing_agent`, `options_legs_builder`, and `greeks_monitor` do NOT read `options_flow_report` or `volatility_report` from state. They read `options_legs`. These agents are unaffected by this phase.

The debator, risk manager, and final decision agents receive the `options_flow_report` and `volatility_report` as context. Making these reports richer (adding term structure sections) is the entire goal — no interface contract changes, just richer report strings.

---

## Sources

### Primary (HIGH confidence — direct code audit)
- `tradingagents/agents/options/strike_expiry_selector.py` — DTE_BUCKETS definition (lines 265-270), bucket loop pattern (lines 340-408)
- `tradingagents/agents/options/options_flow_analyst.py` — single-expiry fetch (line 201), `_compute_flow_metrics` signature (line 85)
- `tradingagents/agents/options/volatility_analyst.py` — near+far fetch (lines 297-300), helper function signatures
- `tradingagents/dataflows/y_finance_options.py` — `get_options_chain` cache TTL (30 min), `MIN_IV_THRESHOLD` (line 123)
- `tradingagents/dataflows/yfinance_cache.py` — `get_cached_text` deduplication behavior
- `tests/agents/test_options_flow_analyst.py` — existing test patterns, mock patterns
- `tests/agents/test_volatility_analyst.py` — existing test patterns, `_compute_term_structure` direct-call tests

### Secondary (HIGH confidence — CONTEXT.md)
- `.planning/phases/01-multi-expiry-options-data-for-flow-and-vol-analysts-to-support-complex-strategies/01-CONTEXT.md` — locked decisions, known data quality issues documented from 2026-04-10 investigation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, existing codebase fully audited
- Architecture: HIGH — pattern exists verbatim in `strike_expiry_selector.py`; copied, not invented
- Pitfalls: HIGH — identified from direct code reading (existing test file, MIN_IV_THRESHOLD, boundary conditions)
- Test gaps: HIGH — test files read directly; Wave 0 gaps are precise

**Research date:** 2026-04-10
**Valid until:** 2026-05-10 (stable codebase, no external API changes expected)
