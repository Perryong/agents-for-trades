# Phase 4: Pricing, Order Building & Greeks - Research

**Researched:** 2026-03-31
**Domain:** Black-Scholes options pricing, multi-leg order construction, portfolio Greeks aggregation, Python agent factory pattern
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Black-Scholes Inputs & Pricing Agent Data Flow**
- Risk-free rate: config default `0.05` (5%) — simple, deterministic, no extra API call
- Dividend yield: `0.0` default, override from yfinance fundamentals `info["dividendYield"]` if available in state flow
- Time to expiry: calendar days from `trade_date` to expiry date / 365.25 (standard)
- Pricing agent reads Phase 3's `options_legs` string via regex — no Tradier re-fetch for pricing inputs

**options_legs Field & Order Structure**
- Legs builder overwrites the same `options_legs` field — Phase 3's basic contract info replaced with full executable order
- Contract count: fixed 1 contract per leg — position sizing is caller's responsibility
- Limit price: market mid (avg of bid/ask) from parsed options chain data
- Wide bid/ask flag threshold: >10% of mid as stated in ROADMAP

**Greeks Monitor Data Source & Aggregation**
- Greeks data: re-fetch options chain from Tradier for full per-contract gamma/theta/vega; delta already in `options_legs` string but re-fetched for consistency
- Portfolio aggregation: dollar-adjusted — net_delta = Σ(sign × delta × contracts × 100 × underlying_price); sign = +1 BUY, -1 SELL
- Thresholds applied to dollar-adjusted Greeks (matches ROADMAP: delta_heavy = |dollar_delta| > $5,000)
- Graceful fallback when Tradier unavailable: use delta from `options_legs` string, set gamma/theta/vega to 0.0, flag report with "Greeks unavailable — Tradier data required"

### Claude's Discretion
- Exact Black-Scholes implementation details (normal CDF approximation vs scipy.stats.norm)
- Edge verdict thresholds: what constitutes "positive edge" vs "fairly priced" vs "overpriced"
- Exact LLM prompt wording for pricing agent verdict
- Error handling for malformed `options_legs` strings from Phase 3
- Directory structure: `tradingagents/agents/options/utils/` for black_scholes.py

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AGENT-05 | Options pricing agent — computes BS theoretical value per leg, net structure value, market mid, edge ($ and %), one-line verdict | Black-Scholes formula verified; factory pattern documented; regex parsing of Phase 3 options_legs format confirmed |
| AGENT-06 | Options legs builder agent — generates structured multi-leg order with BUY/SELL, contract count, ticker, expiry, strike, option type, limit price; outputs net debit/credit, max profit, max loss, breakeven; flags wide bid/ask | Strategy payoff formulas documented per strategy type; wide spread flag formula documented |
| AGENT-07 | Greeks monitor agent — computes portfolio-level net delta, gamma, theta, vega; flags delta heavy, pin/gamma risk, high decay, vol sensitive | Dollar-adjusted aggregation formula documented; threshold flags documented; Tradier re-fetch pattern confirmed |
| PRICE-01 | Black-Scholes implementation for call and put theoretical value | Formula verified with scipy.stats.norm; both scipy and stdlib math.erf approaches confirmed equivalent |
| PRICE-02 | Risk-free rate sourced from config or fetched | Config default `0.05` locked; no API call needed |
| PRICE-03 | Dividend yield sourced from existing fundamentals data | yfinance info["dividendYield"] key confirmed; fallback to 0.0 locked |
</phase_requirements>

---

## Summary

Phase 4 builds four tightly-coupled components: a Black-Scholes utility module, an options pricing agent, an options legs builder agent, and a Greeks monitor agent. All four follow the established project factory pattern (`def create_X(llm): def node(state): ...; return {"field": result}; return node`) proven across Phases 2 and 3.

The Black-Scholes formula is well-understood and verified. The project already has `scipy` available in the environment, but the implementation can equally use `math.erf` from the stdlib — both produce identical results to 4 decimal places, tested at S=K=150, T=0.25, r=0.05, sigma=0.25. Using `math.erf` avoids adding a dependency not in `pyproject.toml`. The pricing agent is an LLM-backed agent (like volatility_analyst) that reads data prepared in Python and asks the LLM to emit a one-line verdict. The legs builder and Greeks monitor are pure-Python agents (like strike_expiry_selector) — they do all computation in Python and write structured strings; the LLM parameter is accepted for interface compatibility but not used.

The key complexity in Phase 4 is: (1) regex parsing of Phase 3's `options_legs` string to extract per-leg inputs, (2) computing strategy-specific max profit/max loss/breakeven formulas correctly per strategy type, and (3) the dollar-adjusted Greek aggregation with sign conventions. These are documented in detail below.

**Primary recommendation:** Implement black_scholes.py as pure-Python stdlib (math.erf), keep pricing agent as single-LLM-call (like volatility_analyst), keep legs builder and Greeks monitor as pure-Python (like strike_expiry_selector), and follow all established patterns exactly.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `math` | 3.10+ | `math.erf`, `math.log`, `math.sqrt`, `math.exp` for Black-Scholes | No extra dependency; identical results to scipy |
| `pandas` | >=2.3.0 | Parse tabular chain strings; compute mid prices | Already in use across all agents |
| `langchain_core.prompts.ChatPromptTemplate` | >=0.3.81 | LLM prompt for pricing verdict | Established pattern in volatility_analyst |
| `tradingagents.dataflows.interface.route_to_vendor` | project | Fetch options chain for Greeks re-fetch | Established pattern in strike_expiry_selector |
| `tradingagents.dataflows.config.get_config` | project | Read risk-free rate from config | Established pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `scipy.stats.norm` | available | Normal CDF for Black-Scholes | Available if preferred over math.erf — but math.erf is sufficient |
| `re` (stdlib) | 3.10+ | Regex parsing of options_legs string | Required for pricing agent to extract leg data |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `math.erf` for normal CDF | `scipy.stats.norm.cdf` | scipy is available but not in pyproject.toml deps; math.erf produces identical results |
| Regex parse of options_legs | Re-fetching from Tradier | Re-fetch is locked OUT per CONTEXT.md; regex parse is the mandated approach |

**Installation:** No new dependencies required. All libraries already available in project environment.

**Version verification:** Confirmed via environment check — scipy is installed (available but not used for BS), pandas>=2.3.0 confirmed in pyproject.toml.

---

## Architecture Patterns

### Recommended Project Structure
```
tradingagents/agents/options/
├── utils/
│   ├── __init__.py               # export call_price, put_price
│   └── black_scholes.py          # Black-Scholes math (stdlib only)
├── options_pricing_agent.py      # LLM agent — reads options_legs, emits verdict
├── options_legs_builder.py       # Pure-Python — builds full executable order
├── greeks_monitor.py             # Pure-Python — aggregates and flags Greeks
└── __init__.py                   # add 3 new factory exports
```

### Pattern 1: Pure-Python Factory (legs builder, Greeks monitor)
**What:** Factory accepts llm (unused), inner node does all work in Python, returns `{"field": str}`
**When to use:** When logic is deterministic and numeric — no LLM judgement needed
**Example:**
```python
# Source: established pattern — strike_expiry_selector.py
def create_options_legs_builder(llm):
    def options_legs_builder_node(state: dict) -> dict:
        ticker: str = state["company_of_interest"]
        options_legs: str = state.get("options_legs", "")
        # ... pure Python computation ...
        return {"options_legs": result_str}
    return options_legs_builder_node
```

### Pattern 2: Single-LLM-call Factory (pricing agent)
**What:** Python computes all numeric inputs, then one LLM call writes the verdict prose
**When to use:** When a narrative / interpretive one-liner is needed alongside numbers
**Example:**
```python
# Source: established pattern — volatility_analyst.py
def create_options_pricing_agent(llm):
    def options_pricing_agent_node(state: dict) -> dict:
        # ... Python computes BS values, edge % ...
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", data_content),
        ])
        result = (prompt | llm).invoke({})
        return {"options_pricing_report": result.content}
    return options_pricing_agent_node
```

### Pattern 3: Angle-bracket Placeholders in System Prompts
**What:** Use `<placeholder>` in SYSTEM_PROMPT, not `{placeholder}`
**When to use:** Always — curly braces conflict with LangChain template variable parsing
**Example:**
```python
# Source: established decision — all Phase 2/3 agents
SYSTEM_PROMPT = (
    "Output format: <verdict> — <one-line explanation>"
    # NOT: "{verdict} — {one_line_explanation}"
)
```

### Pattern 4: Regex Parsing of options_legs String
**What:** Phase 3 outputs a structured string; Phase 4 extracts data via regex
**Phase 3 output format (input to Phase 4):**
```
LEG 1: BUY CALL AAPL 2026-05-10 $150.0 delta=0.30 OI=300 [PASS]
LEG 2: SELL CALL AAPL 2026-05-10 $155.0 delta=0.22 OI=200 [PASS]
```
**Regex pattern to extract per-leg fields:**
```python
import re
LEG_PATTERN = re.compile(
    r"LEG\s+(\d+):\s+(BUY|SELL)\s+(CALL|PUT)\s+(\S+)\s+(\S+)\s+\$([0-9.]+)"
    r"\s+delta=([0-9.]+)\s+OI=(\d+)\s+\[(PASS|LIQUIDITY FAIL)\]"
)
```

### Pattern 5: Parse Tabular String for bid/ask
**What:** The `_parse_tabular_string` helper (duplicated locally, per established pattern) parses the chain data for bid/ask prices to compute mid
**When to use:** Options legs builder reads chain data to get bid/ask; Greeks monitor reads chain for gamma/theta/vega
**Note:** Duplicate locally in each module — do NOT share via import (established decision Phase 2)

### Anti-Patterns to Avoid
- **Shared utils import:** Do not `from .utils import _parse_tabular_string` — duplicate locally per established pattern
- **Curly-brace LLM placeholders:** `{variable}` in SYSTEM_PROMPT breaks LangChain — use `<variable>` or plain text
- **Writing to state["messages"]:** Return dict must NOT contain `messages` key
- **Re-fetching from Tradier in pricing agent:** Locked decision — pricing agent reads from `options_legs` string only
- **scipy import in black_scholes.py:** Not in pyproject.toml; use `math.erf` for stdlib-only implementation

---

## Black-Scholes Implementation Details

### Formula (verified working — tested 2026-03-31)
```python
# Source: verified via Python REPL — math.erf produces identical results to scipy.stats.norm.cdf
import math

def _norm_cdf(x: float) -> float:
    """Standard normal CDF using math.erf (stdlib — no scipy dependency)."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def call_price(S: float, K: float, T: float, r: float, q: float, sigma: float) -> float:
    """Black-Scholes call price.
    S: underlying price, K: strike, T: time to expiry (years),
    r: risk-free rate, q: dividend yield, sigma: implied volatility
    """
    if T <= 0 or sigma <= 0:
        return max(S * math.exp(-q * T) - K * math.exp(-r * T), 0.0)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * math.exp(-q * T) * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)

def put_price(S: float, K: float, T: float, r: float, q: float, sigma: float) -> float:
    """Black-Scholes put price."""
    if T <= 0 or sigma <= 0:
        return max(K * math.exp(-r * T) - S * math.exp(-q * T), 0.0)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return K * math.exp(-r * T) * _norm_cdf(-d2) - S * math.exp(-q * T) * _norm_cdf(-d1)
```

**T=0 edge case:** When expiry date equals trade_date, T=0. Return intrinsic value (max(S-K,0) for call). Do not divide by zero.

**T computation (locked):**
```python
from datetime import date
T = (date.fromisoformat(expiry) - date.fromisoformat(trade_date)).days / 365.25
```

---

## Options Legs Builder: Payoff Formulas

The legs builder must compute max_profit, max_loss, and breakeven for the structured order. These are deterministic math per strategy type. The pricing agent's `options_pricing_report` (including market mids from chain data) is the input source.

**Key inputs per leg from Phase 3 options_legs + chain re-parse:**
- action (BUY/SELL), option_type (CALL/PUT), strike, mid_price (from bid/ask)
- For BUY: debit paid; for SELL: credit received
- net_debit = sum(mid × sign) where sign = +1 for BUY, -1 for SELL (debit positive = cost)

**Strategy payoffs (examples for planner):**

| Strategy | max_profit | max_loss | breakeven |
|----------|-----------|---------|-----------|
| Long call | unlimited (flag as "unlimited") | net_debit | strike + net_debit |
| Long put | strike - net_debit (if > 0) | net_debit | strike - net_debit |
| Bull call spread | (K_high - K_low) - net_debit | net_debit | K_low + net_debit |
| Bear put spread | (K_high - K_low) - net_debit | net_debit | K_high - net_debit |
| Iron condor | net_credit | spread_width - net_credit | two breakevens |
| Long straddle | unlimited (upside), strike - net_debit (downside) | net_debit | two breakevens |
| Long strangle | unlimited (upside), put_strike - net_debit (downside) | net_debit | two breakevens |
| Covered call | net_credit + (strike - underlying) | underlying - net_credit | underlying - net_credit |
| Cash-secured put | net_credit | strike - net_credit | strike - net_credit |
| Calendar spread | complex (vega play) | net_debit | flag as "near term expiry dependent" |

**Wide spread flag:**
```python
spread = ask - bid
mid = (bid + ask) / 2.0
is_wide = (spread / mid) > 0.10 if mid > 0 else False
flag = "[WIDE_SPREAD]" if is_wide else "[OK]"
```

**Final options_legs output format (locked in CONTEXT.md):**
```
LEG 1: BUY CALL AAPL 2026-05-10 $150.00 limit=8.45 qty=1 [OK]
LEG 2: SELL CALL AAPL 2026-05-10 $155.00 limit=5.20 qty=1 [OK]
NET: debit=3.25 max_profit=1.75 max_loss=3.25 breakeven=153.25
```

---

## Greeks Monitor: Dollar Aggregation

**Dollar-adjusted formulas:**
```python
# For each leg in the parsed options_legs:
sign = +1 if action == "BUY" else -1

# Dollar delta (per leg, 1 contract = 100 shares)
dollar_delta_leg = sign * delta * 1 * 100 * underlying_price
# Portfolio net
net_dollar_delta = sum(dollar_delta_leg for all legs)

# Gamma is not dollar-adjusted in threshold (threshold is raw 0.10)
net_gamma = sum(sign * gamma * 1 * 100 for all legs)  # per $1 move

# Dollar theta: theta is already per day per contract (100 shares)
net_dollar_theta = sum(sign * theta * 1 * 100 for all legs)  # negative = decay

# Dollar vega: vega is per 1% IV move per contract (100 shares)
net_dollar_vega = sum(sign * vega * 1 * 100 for all legs)
```

**Threshold flags (locked per REQUIREMENTS):**
```python
flags = []
if abs(net_dollar_delta) > 5000:
    flags.append("DELTA_HEAVY")
# DTE = (expiry - trade_date).days
if net_gamma > 0.10 and dte <= 5:
    flags.append("PIN_RISK")
if net_dollar_theta < -200:
    flags.append("HIGH_DECAY")
if abs(net_dollar_vega) > 500:
    flags.append("VOL_SENSITIVE")
```

**Fallback (Tradier unavailable):**
- Use delta from parsed `options_legs` string (Phase 3 includes delta=X)
- Set gamma=0.0, theta=0.0, vega=0.0 for all legs
- Append to report: `"Greeks unavailable — Tradier data required"`
- Still compute and flag dollar_delta if possible

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Normal CDF | Custom polynomial approximation | `math.erf` (stdlib) | Accurate, tested, zero dependencies |
| Options chain parsing | Custom CSV parser | `pd.read_csv(StringIO(s), sep=r'\s+', engine='python')` | Already established in all agents — proven with whitespace-aligned tables |
| State field merging | Custom merge logic | Return dict with only the changed key — LangGraph merges automatically | LangGraph's StateGraph handles state merging; writing messages or other fields is out-of-scope for these agents |
| Strategy type detection | ML or fuzzy match | Simple substring matching via `strategy.lower()` | Already proven reliable in strike_expiry_selector._get_leg_types() — same logic should be extended/reused |

**Key insight:** The project has proven that substring matching on `strategy.lower()` is sufficient for all 10 known strategies — no fuzzy matching or ML needed.

---

## Common Pitfalls

### Pitfall 1: T=0 Division in Black-Scholes
**What goes wrong:** When trade_date equals expiry date (e.g. same-day expiry), T=0 causes division by zero in `sigma * math.sqrt(T)`
**Why it happens:** Calendar calculation returns 0 days; test cases using same-day or near-term expiries can trigger this
**How to avoid:** Guard at top of call_price / put_price: `if T <= 0 or sigma <= 0: return intrinsic value`
**Warning signs:** `ZeroDivisionError` or `ValueError: math domain error` in log(S/K) when S=K and T=0

### Pitfall 2: Put Delta Sign Convention in Regex Parse
**What goes wrong:** Phase 3 stores `delta=0.30` for puts (absolute value), but the actual put delta is negative (-0.30). Dollar-delta aggregation uses wrong sign if not adjusted.
**Why it happens:** `_format_leg` in strike_expiry_selector.py outputs `abs(row["delta"])` for puts
**How to avoid:** When parsing `options_legs` for puts, apply negative sign: `delta_val = -float(m.group(7)) if option_type == "PUT" else float(m.group(7))`
**Warning signs:** Greeks monitor shows incorrect net delta direction for put-bearing strategies

### Pitfall 3: Missing bid/ask Columns in Chain Data
**What goes wrong:** The options chain tabular string may not have bid/ask columns if fetched via yfinance fallback (yfinance options chain may have different column names)
**Why it happens:** Tradier returns bid/ask; yfinance may return lastPrice but not always bid/ask
**How to avoid:** Check for `bid` and `ask` columns before computing mid; fallback to `lastPrice` or mark limit as "N/A" with [WIDE_SPREAD] flag
**Warning signs:** KeyError on "bid" or "ask" in chain_df

### Pitfall 4: LLM Verdict Hallucinating Strategy Name
**What goes wrong:** Pricing agent LLM output contains extra text before/after the verdict, breaking downstream consumers
**Why it happens:** LLMs tend to add preamble even when instructed not to
**How to avoid:** System prompt must use exact same "no preamble, no postamble" constraint as all other agents; output format with angle-bracket example; store raw `result.content` as the report string (not parsed further)
**Warning signs:** `options_pricing_report` starts with "As a" or "Based on"

### Pitfall 5: wide_spread Division by Zero
**What goes wrong:** If mid=0 (both bid and ask are 0, or missing), division `spread/mid` throws ZeroDivisionError
**Why it happens:** Zero-bid/ask contracts are real (no market makers)
**How to avoid:** Guard: `if mid > 0 else flag as [WIDE_SPREAD]` (treat zero mid as worst case)
**Warning signs:** ZeroDivisionError in legs builder for illiquid strikes

### Pitfall 6: Iron Condor Direction Convention
**What goes wrong:** Iron condor has 4 legs — the sign convention for net_credit calculation must be correct (SELL legs generate credit, BUY legs cost)
**Why it happens:** Complex multi-leg strategies are easy to get backwards
**How to avoid:** Verify with a known iron condor: SELL put at K1 + BUY put at K2 (K2 < K1) + SELL call at K3 + BUY call at K4 (K4 > K3). Net = (sell_put_mid - buy_put_mid) + (sell_call_mid - buy_call_mid). Positive = net credit.
**Warning signs:** Iron condor shows net_debit > 0 when it should always be a credit strategy

---

## State Extension

Add to `tradingagents/agents/utils/agent_states.py` (class `AgentState`):
```python
# Phase 4 additions
options_pricing_report: Annotated[str, "Pricing report from the Options Pricing Agent"]
greeks_report: Annotated[str, "Greeks report from the Greeks Monitor"]
```
`options_legs` field already exists (added in GRAPH-02 scope, present in current AgentState). The legs builder OVERWRITES it (no new field needed).

---

## Integration Points (verified from codebase)

| File | Change |
|------|--------|
| `tradingagents/agents/utils/agent_states.py` | Add `options_pricing_report` and `greeks_report` fields to `AgentState` |
| `tradingagents/agents/options/__init__.py` | Add 3 imports + 3 exports: `create_options_pricing_agent`, `create_options_legs_builder`, `create_greeks_monitor` |
| `tradingagents/agents/__init__.py` | Verify options factories are re-exported (check existing pattern) |
| New: `tradingagents/agents/options/utils/__init__.py` | Empty or export `call_price`, `put_price` |
| New: `tradingagents/agents/options/utils/black_scholes.py` | Black-Scholes implementation |
| New: `tradingagents/agents/options/options_pricing_agent.py` | AGENT-05 |
| New: `tradingagents/agents/options/options_legs_builder.py` | AGENT-06 |
| New: `tradingagents/agents/options/greeks_monitor.py` | AGENT-07 |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (confirmed in pyproject.toml) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` testpaths=["tests"] |
| Quick run command | `python -m pytest tests/agents/ -q --tb=short` |
| Full suite command | `python -m pytest tests/ -q --tb=short` |

**Current suite status:** 90 passed (confirmed 2026-03-31).

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRICE-01 | call_price and put_price return correct BS values | unit | `python -m pytest tests/agents/test_black_scholes.py -x` | Wave 0 |
| PRICE-01 | T=0 guard returns intrinsic value | unit | `python -m pytest tests/agents/test_black_scholes.py::test_t_zero_guard -x` | Wave 0 |
| PRICE-02 | risk_free_rate defaults to 0.05 from config | unit | `python -m pytest tests/agents/test_options_pricing_agent.py::test_risk_free_rate_default -x` | Wave 0 |
| PRICE-03 | dividend yield falls back to 0.0 if not in state | unit | `python -m pytest tests/agents/test_options_pricing_agent.py::test_dividend_yield_fallback -x` | Wave 0 |
| AGENT-05 | Factory returns callable | unit | `python -m pytest tests/agents/test_options_pricing_agent.py::test_factory_returns_callable -x` | Wave 0 |
| AGENT-05 | Returns dict with options_pricing_report key | unit | `python -m pytest tests/agents/test_options_pricing_agent.py::test_returns_pricing_report -x` | Wave 0 |
| AGENT-05 | No messages key in return dict | unit | `python -m pytest tests/agents/test_options_pricing_agent.py::test_no_messages_written -x` | Wave 0 |
| AGENT-05 | Edge verdict: positive edge when BS > mid by >5% | unit | `python -m pytest tests/agents/test_options_pricing_agent.py::test_positive_edge_verdict -x` | Wave 0 |
| AGENT-06 | Factory returns callable | unit | `python -m pytest tests/agents/test_options_legs_builder.py::test_factory_returns_callable -x` | Wave 0 |
| AGENT-06 | Returns dict with options_legs key | unit | `python -m pytest tests/agents/test_options_legs_builder.py::test_returns_options_legs -x` | Wave 0 |
| AGENT-06 | No messages key in return dict | unit | `python -m pytest tests/agents/test_options_legs_builder.py::test_no_messages_written -x` | Wave 0 |
| AGENT-06 | Wide spread flag when (ask-bid)/mid > 0.10 | unit | `python -m pytest tests/agents/test_options_legs_builder.py::test_wide_spread_flag -x` | Wave 0 |
| AGENT-06 | NET summary line contains debit, max_profit, max_loss, breakeven | unit | `python -m pytest tests/agents/test_options_legs_builder.py::test_net_summary_line -x` | Wave 0 |
| AGENT-07 | Factory returns callable | unit | `python -m pytest tests/agents/test_greeks_monitor.py::test_factory_returns_callable -x` | Wave 0 |
| AGENT-07 | Returns dict with greeks_report key | unit | `python -m pytest tests/agents/test_greeks_monitor.py::test_returns_greeks_report -x` | Wave 0 |
| AGENT-07 | No messages key in return dict | unit | `python -m pytest tests/agents/test_greeks_monitor.py::test_no_messages_written -x` | Wave 0 |
| AGENT-07 | DELTA_HEAVY flag when \|dollar_delta\| > 5000 | unit | `python -m pytest tests/agents/test_greeks_monitor.py::test_delta_heavy_flag -x` | Wave 0 |
| AGENT-07 | PIN_RISK flag when gamma > 0.10 and DTE <= 5 | unit | `python -m pytest tests/agents/test_greeks_monitor.py::test_pin_risk_flag -x` | Wave 0 |
| AGENT-07 | HIGH_DECAY flag when theta < -200 | unit | `python -m pytest tests/agents/test_greeks_monitor.py::test_high_decay_flag -x` | Wave 0 |
| AGENT-07 | VOL_SENSITIVE flag when \|dollar_vega\| > 500 | unit | `python -m pytest tests/agents/test_greeks_monitor.py::test_vol_sensitive_flag -x` | Wave 0 |
| AGENT-07 | Graceful fallback when Tradier unavailable | unit | `python -m pytest tests/agents/test_greeks_monitor.py::test_tradier_fallback -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/agents/ -q --tb=short`
- **Per wave merge:** `python -m pytest tests/ -q --tb=short`
- **Phase gate:** Full suite green (currently 90 passed) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/agents/test_black_scholes.py` — covers PRICE-01 (call_price, put_price, T=0 guard, known values)
- [ ] `tests/agents/test_options_pricing_agent.py` — covers AGENT-05, PRICE-02, PRICE-03
- [ ] `tests/agents/test_options_legs_builder.py` — covers AGENT-06
- [ ] `tests/agents/test_greeks_monitor.py` — covers AGENT-07

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| scipy for normal CDF | `math.erf` from stdlib | Available since Python 3.2 | Zero additional dependencies |
| Complex agent message threading | Single-pass factory pattern (Python compute + optional LLM call) | Established Phases 2–3 | Simpler, testable, no MessagesPlaceholder needed |

---

## Open Questions

1. **Underlying price source for Greeks dollar-adjustment**
   - What we know: dollar-delta = sign × delta × contracts × 100 × underlying_price; underlying_price needed
   - What's unclear: `AgentState` does not have an `underlying_price` field; Phase 3 does not store it
   - Recommendation: Parse from Phase 3 `options_legs` — the Tradier chain string includes `underlying` column; alternatively, Greeks monitor can call `route_to_vendor("get_stock_data", ticker)` to get current price. The re-fetch of options chain for greeks (locked decision) will include the `underlying` column in Tradier data — use that as underlying_price.

2. **Dividend yield from state vs re-fetch**
   - What we know: Locked decision says override from `info["dividendYield"]` if available in state flow
   - What's unclear: `AgentState` doesn't currently have a `fundamentals_report` field that would expose dividendYield as a Python float; `fundamentals_report` is a string
   - Recommendation: Default to 0.0 (locked). If `fundamentals_report` string contains "dividendYield", extract via regex. This is low-risk — dividend yield rarely changes pricing significantly.

3. **LLM unused in legs builder and Greeks monitor but required as parameter**
   - What we know: Interface compatibility requires `llm` param (established pattern)
   - What's unclear: Should a docstring note "LLM parameter accepted but not used" explicitly (as done in strike_expiry_selector)?
   - Recommendation: Yes — copy the same docstring pattern from strike_expiry_selector.py exactly

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `volatility_analyst.py`, `strike_expiry_selector.py`, `options_strategy_selector.py` — factory patterns, LLM invocation, tabular string parsing
- Direct code inspection of `agent_states.py` — confirmed `options_legs` field exists; `options_pricing_report` and `greeks_report` absent (need adding)
- Direct code inspection of `interface.py` — confirmed `route_to_vendor("get_options_chain", ticker, expiry)` signature
- Python REPL verification — Black-Scholes formula with both `math.erf` and `scipy.stats.norm.cdf` produce identical results (call=8.3976, put=6.5343 for S=K=150, T=0.25, r=0.05, sigma=0.25)
- Test suite run — 90 tests passing; test patterns confirmed from existing test files

### Secondary (MEDIUM confidence)
- `pyproject.toml` inspection — confirmed scipy available in environment (not listed in project deps but installed); confirmed pandas>=2.3.0, langchain-core>=0.3.81
- `conftest.py` inspection — confirmed Tradier chain data structure with `greeks.delta/gamma/theta/vega/smv_vol/mid_iv` fields; confirmed bid/ask present in Tradier data

### Tertiary (LOW confidence)
- Strategy payoff formulas (max profit/loss/breakeven) derived from standard options theory — well-known, not verified against an authoritative single source, but mathematically standard

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified from codebase and environment checks
- Architecture: HIGH — directly derived from existing agent implementations
- Pitfalls: HIGH — most derived from actual code analysis (delta sign convention, T=0 guard verified); LOW only for LLM hallucination pitfall (standard concern)
- Payoff formulas: MEDIUM — standard options theory, not verified against official docs
- Test patterns: HIGH — directly derived from existing 90-test suite

**Research date:** 2026-03-31
**Valid until:** 2026-05-01 (stable domain — Black-Scholes math does not change; LangChain pattern may drift but is pinned by pyproject.toml)
