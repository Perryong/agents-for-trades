# Phase 02: Strategy Agent Enhancement - Research

**Researched:** 2026-04-12
**Domain:** Options strategy registry, rule-based eligibility gate, declarative legs builder
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Include ALL strategies from optopsy's taxonomy — no exclusions. Full list: singles (long/short call/put), straddles/strangles (long/short), vertical spreads (bull/bear call/put), covered/protective (covered call, cash-secured put, protective put, collar), ratio spreads (call/put back/front spreads), butterflies (long/short call/put), condors (long/short call/put), iron strategies (iron condor, iron butterfly, reverse iron condor, reverse iron butterfly), calendar spreads (long/short call/put), diagonal spreads (long/short call/put).
- **D-02:** High-risk strategies (naked shorts, ratio spreads) are NOT excluded but require paper trading guardrails — stop-losses must be enforced for margin-intensive strategies.
- **D-03:** YAML config file, NOT Python dict. Registry is data, not logic — editable without code changes.
- **D-04:** Registry loaded once at startup into a Pydantic model or dataclass for type safety.
- **D-05:** File structure: `strategies/registry.yaml`, `strategies/models.py`, `strategies/gate.py`
- **D-06:** Each registry entry includes: bias, iv_env, legs count, margin_intensive flag, requires_multi_expiry flag, earnings_signal_polarity.
- **D-07:** Gate is internal to the strategy selector node — NOT a separate graph node.
- **D-08:** Hard gates: directional bias, IV environment, DTE availability, capital/margin, liquidity.
- **D-09:** Soft scoring (rank, don't eliminate): theta environment, skew shape, earnings proximity.
- **D-10:** Target shortlist: 3-6 strategies passed to the LLM.
- **D-11:** `available_margin` is a config value in `risk_config.yaml`, optional with safe default.
- **D-12:** If unset, gate excludes ALL margin-intensive strategies by default (fail-safe, not fail-open).
- **D-13:** Override flag `exclude_margin_intensive` available for explicit control.
- **D-14:** Earnings heuristic: `(dte <= 7 AND iv_rank >= 75) OR (dte <= 14 AND iv_rank >= 90)`.
- **D-15:** Registry flags per-strategy whether earnings proximity is a positive or negative signal.
- **D-16:** Declarative registry approach — each strategy defines legs as structured entries: side, type, quantity, strike_offset, expiry.
- **D-17:** Builder iterates legs generically — adding a new strategy = one YAML block, zero new code paths.
- **D-18:** Legs registry can live in the same `registry.yaml` or separate `legs.yaml` — Claude's discretion.
- **D-19:** Selector outputs: anchor_strike, width, near_expiry, far_expiry.
- **D-20:** Legs builder resolves all strikes from `anchor + (offset x width)`.
- **D-21:** Width has a strategy-level default in the registry, overridable by the selector.
- **D-22:** Per-leg strike overrides deferred.
- **D-23:** All strategies must have stop-loss enforcement when executed in paper trading.
- **D-24:** Risk Manager receives full strategy context (margin requirements, max loss profile).

### Claude's Discretion

- Exact YAML schema design for the registry
- How to structure the gate filtering code internally
- Whether legs definitions share the strategy registry file or get their own
- Pydantic vs dataclass for the loaded models
- How to unit test the gate logic

### Deferred Ideas (OUT OF SCOPE)

- Earnings calendar API integration — use heuristic for now, plug in real API later
- Per-leg strike overrides for skew-adjusted positioning — extend selector output later
- Promoting gate to a separate graph node for observability — do later if needed
- Backtesting strategy performance against historical data — separate milestone
</user_constraints>

---

## Summary

This phase replaces the 10-strategy hardcoded selector with a 30+ strategy registry-driven system. The architecture has three layers: (1) a YAML registry defining strategy metadata and leg shapes, (2) a rule-based eligibility gate that filters the registry to 3-6 candidates using market signals from existing state keys, and (3) an LLM strategy selector that chooses from the shortlist. The legs builder and strike/expiry selector are updated to work declaratively from the registry rather than via hardcoded if/elif chains.

The full strategy taxonomy is derived from optopsy (confirmed via GitHub source): 4 singles, 16 spreads (including ratio types), 4 butterflies, 4 condors, 4 iron strategies, 8 calendar/diagonal. Total: 40 named strategy shapes after grouping symmetric long/short pairs. The existing code has heavy if/elif duplication in both `options_legs_builder.py` and `strike_expiry_selector.py` that this phase eliminates.

Key architectural insight from reading the existing code: the current legs builder (`options_legs_builder.py`) uses `_get_strategy_type()` returning a fixed set of 10 strings, and `_compute_payoff()` has a separate branch per strategy. Both functions must be replaced — not extended — by the declarative YAML-driven approach. The current strike/expiry selector similarly uses `_get_leg_types()` with 10 if/elif branches. All three hardcoded dispatch functions become obsolete after this phase.

**Primary recommendation:** Use a single `registry.yaml` with two top-level sections (`strategies:` and `legs:`) to keep strategy metadata and leg definitions colocated, loaded once at module import via a Pydantic v2 model, with gate logic as a pure function in `gate.py` that takes the loaded registry and a `GateContext` dataclass.

---

## Complete Strategy Taxonomy (from optopsy source — HIGH confidence)

### Confirmed from GitHub source

| Category | Strategy Name | Legs | Bias | IV Env | Margin Intensive | Multi-Expiry |
|----------|--------------|------|------|--------|-----------------|--------------|
| Singles | long_call | 1 | bullish | any | false | false |
| Singles | long_put | 1 | bearish | any | false | false |
| Singles | short_call | 1 | bearish/neutral | high | true | false |
| Singles | short_put | 1 | bullish/neutral | high | true | false |
| Spreads | long_call_spread (bull call spread) | 2 | bullish | any | false | false |
| Spreads | short_call_spread (bear call spread) | 2 | bearish | high | false | false |
| Spreads | long_put_spread (bear put spread) | 2 | bearish | any | false | false |
| Spreads | short_put_spread (bull put spread) | 2 | bullish | high | false | false |
| Spreads | long_straddle | 2 | neutral_volatile | low | false | false |
| Spreads | short_straddle | 2 | neutral_quiet | high | true | false |
| Spreads | long_strangle | 2 | neutral_volatile | low | false | false |
| Spreads | short_strangle | 2 | neutral_quiet | high | true | false |
| Spreads | covered_call | 1-option | bullish/neutral | high | false | false |
| Spreads | protective_put | 1-option | bullish/hedge | any | false | false |
| Spreads | collar | 2-option | bullish/hedge | any | false | false |
| Spreads | cash_secured_put | 1 | bullish/neutral | high | false | false |
| Spreads | call_back_spread | 3 | bullish_volatile | any | true | false |
| Spreads | put_back_spread | 3 | bearish_volatile | any | true | false |
| Spreads | call_front_spread | 3 | bearish/neutral | high | true | false |
| Spreads | put_front_spread | 3 | bullish/neutral | high | true | false |
| Butterflies | long_call_butterfly | 3 | neutral | low | false | false |
| Butterflies | short_call_butterfly | 3 | neutral_volatile | any | false | false |
| Butterflies | long_put_butterfly | 3 | neutral | low | false | false |
| Butterflies | short_put_butterfly | 3 | neutral_volatile | any | false | false |
| Condors | long_call_condor | 4 | neutral | low | false | false |
| Condors | short_call_condor | 4 | neutral_volatile | any | false | false |
| Condors | long_put_condor | 4 | neutral | low | false | false |
| Condors | short_put_condor | 4 | neutral_volatile | any | false | false |
| Iron | iron_condor | 4 | neutral | high | false | false |
| Iron | reverse_iron_condor | 4 | neutral_volatile | low | false | false |
| Iron | iron_butterfly | 4 | neutral | high | false | false |
| Iron | reverse_iron_butterfly | 4 | neutral_volatile | low | false | false |
| Calendar | long_call_calendar | 2 | neutral/bullish | low | false | true |
| Calendar | short_call_calendar | 2 | neutral_volatile | high | false | true |
| Calendar | long_put_calendar | 2 | neutral/bearish | low | false | true |
| Calendar | short_put_calendar | 2 | neutral_volatile | high | false | true |
| Diagonal | long_call_diagonal | 2 | bullish | low | false | true |
| Diagonal | short_call_diagonal | 2 | bearish | high | false | true |
| Diagonal | long_put_diagonal | 2 | bearish | low | false | true |
| Diagonal | short_put_diagonal | 2 | bullish | high | false | true |

**Total: 40 strategy shapes** (optopsy has some aliases; protective_put and collar are in spreads.py alongside the 16 listed above)

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pyyaml | installed (stdlib-adjacent) | Load `registry.yaml` | Standard YAML parser for Python; `yaml.safe_load()` for untrusted data |
| pydantic | 2.12.5 (verified) | Typed registry models with validation | Already in project; v2 `model_validate()` API; strict type coercion at load time |
| dataclasses | stdlib | `GateContext` input struct | Zero dependency; pure value object for gate input |
| functools.lru_cache | stdlib | Cache YAML load (loaded once at module level) | No external dep; prevents repeated disk I/O |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | installed | Gate unit tests | All gate tests — pure Python, no LLM mocking needed |
| typing (Literal, List) | stdlib | Type annotations in models | Pydantic v2 requires Literal for enum-like fields |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pyyaml safe_load | tomllib (stdlib 3.11+) | TOML is fine but YAML matches user's example syntax from CONTEXT.md; use YAML |
| Pydantic v2 | Python dataclasses | Pydantic gives free field validation with error messages; worth the zero extra dep cost |
| Single registry.yaml | Separate registry.yaml + legs.yaml | Single file preferred: strategies and their legs are one logical unit; splitting adds indirection for no clear gain |

**Installation:** No new packages needed — pyyaml and pydantic are already installed.

---

## Architecture Patterns

### Recommended Project Structure

```
tradingagents/agents/options/
├── strategies/
│   ├── __init__.py          # exports: load_registry(), REGISTRY
│   ├── registry.yaml        # strategy metadata + leg definitions (one file)
│   ├── models.py            # StrategyMeta, LegDef, StrategyRegistry Pydantic models
│   └── gate.py              # filter_strategies(registry, context) -> list[str]
├── options_strategy_selector.py   # updated: loads registry, calls gate, passes shortlist to LLM
├── strike_expiry_selector.py      # updated: returns anchor_strike, width, near_expiry, far_expiry
├── options_legs_builder.py        # updated: resolves legs from registry LegDef + anchor/width
├── constants.py                   # unchanged: DTE_BUCKETS
└── risk_config.yaml               # NEW: available_margin, exclude_margin_intensive
```

### Pattern 1: YAML Registry Schema

**What:** A single YAML file with two top-level sections. `strategies` maps canonical strategy names to eligibility metadata. `legs` maps the same names to ordered leg definitions.

**When to use:** Always — this is the single source of truth. Code never hardcodes a strategy name except when parsing the LLM's output.

**Example:**
```yaml
# tradingagents/agents/options/strategies/registry.yaml

strategies:
  long_call:
    bias: [bullish]
    iv_env: [any]
    legs_count: 1
    margin_intensive: false
    requires_multi_expiry: false
    earnings_signal: positive   # IV crush after earnings hurts long options
    default_width: 5.0
    soft_score:
      theta_env: negative       # negative theta — bad for hold-heavy theta environments
      skew: neutral

  bull_call_spread:
    bias: [bullish]
    iv_env: [any]
    legs_count: 2
    margin_intensive: false
    requires_multi_expiry: false
    earnings_signal: neutral
    default_width: 5.0
    soft_score:
      theta_env: neutral
      skew: neutral

  iron_condor:
    bias: [neutral]
    iv_env: [high]
    legs_count: 4
    margin_intensive: false
    requires_multi_expiry: false
    earnings_signal: negative   # earnings crushes premium unexpectedly
    default_width: 5.0
    soft_score:
      theta_env: positive       # positive theta — benefits from time decay
      skew: neutral

  long_call_calendar:
    bias: [neutral, bullish]
    iv_env: [low, any]
    legs_count: 2
    margin_intensive: false
    requires_multi_expiry: true
    earnings_signal: positive   # benefits from IV expansion
    default_width: 0.0          # calendars use same strike; width unused
    soft_score:
      theta_env: positive
      skew: neutral

  short_call:
    bias: [bearish, neutral]
    iv_env: [high]
    legs_count: 1
    margin_intensive: true
    requires_multi_expiry: false
    earnings_signal: negative
    default_width: 0.0
    soft_score:
      theta_env: positive
      skew: neutral

legs:
  long_call:
    - {side: buy, type: call, quantity: 1, strike_offset: 0, expiry: near}

  bull_call_spread:
    - {side: buy,  type: call, quantity: 1, strike_offset: 0,  expiry: near}
    - {side: sell, type: call, quantity: 1, strike_offset: +1, expiry: near}

  iron_condor:
    - {side: sell, type: put,  quantity: 1, strike_offset: -1, expiry: near}
    - {side: buy,  type: put,  quantity: 1, strike_offset: -2, expiry: near}
    - {side: sell, type: call, quantity: 1, strike_offset: +1, expiry: near}
    - {side: buy,  type: call, quantity: 1, strike_offset: +2, expiry: near}

  long_call_butterfly:
    - {side: buy,  type: call, quantity: 1, strike_offset: -1, expiry: near}
    - {side: sell, type: call, quantity: 2, strike_offset: 0,  expiry: near}
    - {side: buy,  type: call, quantity: 1, strike_offset: +1, expiry: near}

  long_call_calendar:
    - {side: sell, type: call, quantity: 1, strike_offset: 0, expiry: near}
    - {side: buy,  type: call, quantity: 1, strike_offset: 0, expiry: far}

  long_call_diagonal:
    - {side: sell, type: call, quantity: 1, strike_offset: 0,  expiry: near}
    - {side: buy,  type: call, quantity: 1, strike_offset: +1, expiry: far}
```

### Pattern 2: Pydantic v2 Registry Models

**What:** Type-safe representation of the YAML schema. Loaded once at module level, cached via module-level singleton.

**When to use:** At import time of `strategies/__init__.py`.

```python
# Source: Pydantic v2 docs — verified against installed version 2.12.5
from pydantic import BaseModel
from typing import Literal, List, Optional
from pathlib import Path
import yaml
import functools

BiasType = Literal["bullish", "bearish", "neutral", "neutral_volatile",
                   "neutral_quiet", "bullish_volatile", "bearish_volatile",
                   "bullish_hedge", "any"]
IVEnvType = Literal["low", "high", "any"]
EarningsSignal = Literal["positive", "negative", "neutral"]
ThetaEnvScore = Literal["positive", "negative", "neutral"]
SideType = Literal["buy", "sell"]
OptionTypeStr = Literal["call", "put"]
ExpiryType = Literal["near", "far"]

class SoftScore(BaseModel):
    theta_env: ThetaEnvScore = "neutral"
    skew: ThetaEnvScore = "neutral"

class StrategyMeta(BaseModel):
    bias: List[BiasType]
    iv_env: List[IVEnvType]
    legs_count: int
    margin_intensive: bool
    requires_multi_expiry: bool
    earnings_signal: EarningsSignal = "neutral"
    default_width: float = 5.0
    soft_score: SoftScore = SoftScore()

class LegDef(BaseModel):
    side: SideType
    type: OptionTypeStr
    quantity: int = 1
    strike_offset: int = 0
    expiry: ExpiryType = "near"

class StrategyRegistry(BaseModel):
    strategies: dict[str, StrategyMeta]
    legs: dict[str, List[LegDef]]

@functools.lru_cache(maxsize=1)
def load_registry() -> StrategyRegistry:
    path = Path(__file__).parent / "registry.yaml"
    raw = yaml.safe_load(path.read_text())
    return StrategyRegistry.model_validate(raw)

# Module-level singleton — loaded once
REGISTRY: StrategyRegistry = load_registry()
```

### Pattern 3: Gate Context and Filtering Logic

**What:** A pure function `filter_strategies(registry, context) -> list[str]` that applies hard gates then soft scoring. No LLM calls, no I/O.

**When to use:** Called inside `options_strategy_selector_node` before building the LLM prompt.

```python
# tradingagents/agents/options/strategies/gate.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class GateContext:
    """Parsed signals extracted from state before gate evaluation."""
    bias: str                     # "bullish" | "bearish" | "neutral" | "neutral_volatile"
    iv_rank: float                # 0-100
    iv_env: str                   # "low" | "high" | "any" — derived: iv_rank < 30 → low, > 60 → high
    has_multi_expiry: bool        # True if Phase 1 fetched multiple DTE buckets with data
    available_margin: Optional[float]  # None = unset → exclude all margin_intensive
    exclude_margin_intensive: bool     # explicit override flag
    min_oi_threshold: int         # from config, used for liquidity gate
    near_dte: int                 # DTE of shortest available expiry
    iv_rank_for_earnings: float   # same as iv_rank but named for clarity
    is_earnings_proximity: bool   # derived via heuristic: (dte<=7 AND iv_rank>=75) OR (dte<=14 AND iv_rank>=90)

def _derive_iv_env(iv_rank: float) -> str:
    if iv_rank < 30:
        return "low"
    elif iv_rank > 60:
        return "high"
    return "any"

def filter_strategies(registry, context: GateContext) -> list[str]:
    """Apply hard gates then soft scoring. Returns shortlist of 3-6 strategy names."""
    candidates = []
    scores = {}

    for name, meta in registry.strategies.items():
        # --- Hard gate 1: directional bias ---
        if context.bias not in meta.bias and "any" not in meta.bias:
            continue

        # --- Hard gate 2: IV environment ---
        if context.iv_env not in meta.iv_env and "any" not in meta.iv_env:
            continue

        # --- Hard gate 3: multi-expiry availability ---
        if meta.requires_multi_expiry and not context.has_multi_expiry:
            continue

        # --- Hard gate 4: margin/capital ---
        margin_blocked = (
            context.available_margin is None or
            context.exclude_margin_intensive
        )
        if meta.margin_intensive and margin_blocked:
            continue

        candidates.append(name)

        # --- Soft scoring ---
        score = 0
        # Theta environment signal
        # TODO: derive theta_env from iv_rank + dte context
        # Earnings proximity
        if context.is_earnings_proximity:
            if meta.earnings_signal == "positive":
                score += 1
            elif meta.earnings_signal == "negative":
                score -= 1
        scores[name] = score

    # Sort by score desc, take top 6, ensure at least 3
    ranked = sorted(candidates, key=lambda n: scores.get(n, 0), reverse=True)
    shortlist = ranked[:6]
    if len(shortlist) < 3 and len(candidates) >= 3:
        shortlist = candidates[:3]
    return shortlist
```

### Pattern 4: Updated Strategy Selector Node

**What:** The existing `create_options_strategy_selector` factory is extended to call the gate before constructing the LLM prompt. The gate result replaces the hardcoded STRATEGY_LIST.

**When to use:** The gate runs purely on parsed report text — no additional LLM call. The `GateContext` is built by extracting structured signals from the report strings in state.

```python
def _extract_gate_context(state: dict, config: dict) -> GateContext:
    """Extract structured signals from report strings already in state."""
    vol_report = state.get("volatility_report", "")
    investment_plan = state.get("investment_plan", "")
    # Extract iv_rank via regex from vol_report
    # Extract bias keyword from investment_plan
    # Extract has_multi_expiry from options_flow_report structure
    # Read available_margin and exclude_margin_intensive from config
    ...

def create_options_strategy_selector(llm):
    def options_strategy_selector_node(state: dict) -> dict:
        context = _extract_gate_context(state, get_config())
        shortlist = filter_strategies(REGISTRY, context)

        strategy_list_text = "\n".join(
            f"{i+1}. {name}" for i, name in enumerate(shortlist)
        )
        # Build prompt with dynamic shortlist (3-6 strategies)
        ...
    return options_strategy_selector_node
```

### Pattern 5: Declarative Legs Builder

**What:** The legs builder reads `LegDef` list from registry and resolves each leg's strike as `anchor_strike + (strike_offset * width)`. The `options_strategy` key now contains the canonical registry key name (e.g., `iron_condor`) extracted from the LLM output.

**When to use:** The builder looks up `registry.legs[strategy_key]` and iterates the list generically. No per-strategy code branches.

```python
def _resolve_strike(anchor: float, offset: int, width: float) -> float:
    """Resolve absolute strike from anchor and offset."""
    return round(anchor + (offset * width), 2)

def options_legs_builder_node(state: dict) -> dict:
    strategy_key = _normalize_strategy_key(state.get("options_strategy", ""))
    leg_defs = REGISTRY.legs.get(strategy_key)
    if not leg_defs:
        return {"options_legs": "No order — unknown strategy"}

    anchor = state.get("anchor_strike")
    width = state.get("width", REGISTRY.strategies[strategy_key].default_width)
    near_expiry = state.get("near_expiry")
    far_expiry = state.get("far_expiry")

    resolved_legs = []
    for i, leg in enumerate(leg_defs, 1):
        strike = _resolve_strike(anchor, leg.strike_offset, width)
        expiry = near_expiry if leg.expiry == "near" else far_expiry
        resolved_legs.append({
            "leg_num": i, "side": leg.side, "type": leg.type,
            "quantity": leg.quantity, "strike": strike, "expiry": expiry
        })
    # ... bid/ask lookup and payoff computation unchanged in structure
```

### Pattern 6: Strike/Expiry Selector Anchor+Width Output

**What:** The selector is updated to output `anchor_strike`, `width`, `near_expiry`, `far_expiry` as state keys alongside the existing `options_legs` text output. These new keys feed the declarative legs builder.

**Critical:** The existing `options_legs` string format must remain intact because `options_pricing_agent` and `greeks_monitor` parse it. The new keys are additive, not replacements.

```python
return {
    "options_legs": formatted_leg_string,   # existing consumers unchanged
    "anchor_strike": selected_anchor,       # NEW: for declarative builder
    "width": effective_width,               # NEW: from strategy registry default_width
    "near_expiry": near_exp_str,            # NEW: best expiry from shortest bucket
    "far_expiry": far_exp_str,              # NEW: second expiry for multi-expiry strategies
}
```

### Pattern 7: Risk Config YAML

**What:** A new `risk_config.yaml` file under `tradingagents/agents/options/` (or project root) holding capital/margin config. Loaded by `get_config()` flow or directly by the gate.

```yaml
# tradingagents/agents/options/risk_config.yaml
available_margin: null          # null = unset → fail-safe (exclude all margin_intensive)
exclude_margin_intensive: false # explicit override: true forces exclusion even if margin set
paper_trading_stop_loss_pct: 0.50  # close position when loss reaches 50% of max_loss
```

### Anti-Patterns to Avoid

- **Extending the old if/elif chains:** `_get_strategy_type()`, `_get_leg_types()`, and `_compute_payoff()` should be deleted and replaced — not extended. Extending perpetuates the maintenance problem this phase exists to solve.
- **Loading YAML on every node invocation:** Load once at module level via `lru_cache` or module-level singleton. YAML I/O per request adds latency across every graph run.
- **Regex parsing of LLM strategy output inside the legs builder:** The LLM returns a string like `"iron condor -- rationale"`. Normalize it to a registry key in the selector's output (e.g., strip rationale, lowercase, replace spaces with underscores). The legs builder should receive a clean key, not raw LLM text.
- **Passing gate context as raw state strings to the gate function:** Extract structured signals (`iv_rank`, `bias`, `has_multi_expiry`) from report strings in one place (`_extract_gate_context`) before calling the gate. The gate itself should be a pure function that never parses strings.
- **Adding `anchor_strike` / `width` / `near_expiry` / `far_expiry` to the AgentState TypedDict before the type system is updated:** The state dict already exists; new keys can be added without breaking existing consumers if AgentState is updated consistently.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML parsing | Custom text parser | `yaml.safe_load()` from pyyaml | Handles multiline, anchors, type coercion; already installed |
| Registry field validation | Manual isinstance checks | Pydantic v2 `model_validate()` | Gives typed errors at load time, not runtime surprises |
| Payoff formula registry | Custom payoff formula engine | Expand `_compute_payoff()` with generic debit/credit/spread-width formula covering all 40 strategies | 40 strategies reduce to ~6 payoff templates: single debit, single credit, debit spread, credit spread, butterfly, calendar |
| Strategy name normalization | Regex soup | Simple string processing: `.lower().replace(" ", "_").replace("-", "_")` + a lookup dict for aliases | LLM returns human names; registry uses snake_case keys; one alias map handles all variants |

**Key insight:** The payoff computation does NOT need 40 separate functions. All strategies fall into generic payoff templates based on their leg structure. The declarative legs list itself carries enough information to compute net debit/credit; only max_profit and max_loss formulas need strategy-level categorization, which reduces to 6 categories.

---

## Common Pitfalls

### Pitfall 1: IV Environment Boundary Ambiguity
**What goes wrong:** IV rank of 45 (mid-range) fails both `low` and `high` gates, leaving too few candidates.
**Why it happens:** Strict threshold split with no `any` escape valve.
**How to avoid:** Registry uses `[any]` for strategies that work in all IV environments (e.g., long_call, long_put). Gate treats `any` as always-pass. IV thresholds: < 30 = low, > 60 = high, 30-60 = any matches all strategies with `any` or `high` or `low` in their list.
**Warning signs:** Shortlist fewer than 3 strategies in testing with mid-range IV rank.

### Pitfall 2: Bias Extraction from LLM Report Text Is Brittle
**What goes wrong:** `investment_plan` text says "cautiously bullish" but gate extracts `bullish` fine. Later it says "leaning toward long" and extraction fails, defaulting to `neutral`.
**Why it happens:** Regex-based extraction from free-text LLM output is inherently fragile.
**How to avoid:** Use a set of inclusive keyword patterns: any of ["bullish", "long", "buy", "upside"] → `bullish`; any of ["bearish", "short", "sell", "downside"] → `bearish`; no clear signal → `neutral`. This is sufficient for the hard gate; LLM context window carries the nuance.
**Warning signs:** Gate consistently passes/blocks the same strategies regardless of investment plan content.

### Pitfall 3: Backward Compatibility Break in `options_legs` String Format
**What goes wrong:** Downstream agents (`options_pricing_agent`, `greeks_monitor`) parse the `options_legs` string using `LEG_PATTERN` regex. If the declarative builder changes the string format, those agents silently fail with "No order — contract selection failed".
**Why it happens:** `options_pricing_agent.py` and `greeks_monitor.py` both use `LEG_PATTERN = re.compile(r"LEG\s+(\d+):\s+(BUY|SELL)...")`.
**How to avoid:** The new legs builder must emit EXACTLY the same string format: `LEG N: BUY/SELL CALL/PUT {ticker} {expiry} ${strike} delta={d} OI={oi} [PASS|LIQUIDITY FAIL]`. The existing format is a de-facto wire protocol. Changing it is out of scope for this phase.
**Warning signs:** Run `test_options_legs_builder.py` against the new builder; all existing format assertions must still pass.

### Pitfall 4: AgentState TypedDict Not Updated for New Keys
**What goes wrong:** `anchor_strike`, `width`, `near_expiry`, `far_expiry` written by selector but not declared in `AgentState` TypedDict causes LangGraph type-checking failures or silent key loss.
**Why it happens:** LangGraph state management validates key names against the declared TypedDict in some configurations.
**How to avoid:** Update `tradingagents/agents/utils/agent_states.py` to include the four new optional keys (`Optional[float]`, `Optional[str]`) before wiring the updated nodes.
**Warning signs:** State keys missing when legs builder tries to read them.

### Pitfall 5: Calendar/Diagonal Strategies with Missing Far Expiry
**What goes wrong:** `requires_multi_expiry: true` strategies pass the gate when `has_multi_expiry: true`, but the far expiry chosen by the selector has no liquid chain.
**Why it happens:** Gate checks data availability in aggregate; the actual far chain lookup happens in the selector.
**How to avoid:** The strike/expiry selector already returns `None` for buckets with no chain data. For multi-expiry strategies, the selector should only populate `far_expiry` if a liquid chain exists there. If not, return `LIQUIDITY FAIL` same as single-expiry failures.
**Warning signs:** `far_expiry` is set but legs builder generates legs with no valid bid/ask for the far leg.

### Pitfall 6: STRATEGY_LIST Import Used in Tests
**What goes wrong:** `test_options_strategy_selector.py:test_strategy_list_has_ten_entries` imports `STRATEGY_LIST` and asserts `len == 10`. This test will fail after migration.
**Why it happens:** Tests were written for the old hardcoded list.
**How to avoid:** Update the test to check registry length (>= 30) and remove the exact-count assertion. The test `test_output_contains_valid_strategy_name` also uses `STRATEGY_LIST` — update it to check against registry keys.
**Warning signs:** CI breaks on existing test file that worked before the phase.

---

## Code Examples

### Registry YAML Loading

```python
# Source: pyyaml docs + pydantic v2 model_validate pattern (confirmed working)
import yaml
import functools
from pathlib import Path

@functools.lru_cache(maxsize=1)
def load_registry() -> StrategyRegistry:
    path = Path(__file__).parent / "registry.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return StrategyRegistry.model_validate(raw)
```

### Strategy Key Normalization (LLM output → registry key)

```python
# Simple normalization — covers all optopsy strategy names
_ALIAS_MAP = {
    "bull call spread": "long_call_spread",
    "bear put spread": "long_put_spread",
    "bear call spread": "short_call_spread",
    "bull put spread": "short_put_spread",
    "cash-secured put": "cash_secured_put",
    "cash secured put": "cash_secured_put",
    "calendar spread": "long_call_calendar",  # legacy fallback
}

def _normalize_strategy_key(llm_output: str) -> str:
    """Extract strategy name from 'name -- rationale' LLM output and normalize to registry key."""
    name_part = llm_output.split("--")[0].strip().lower()
    if name_part in _ALIAS_MAP:
        return _ALIAS_MAP[name_part]
    return name_part.replace(" ", "_").replace("-", "_")
```

### Payoff Template Dispatch (replacing 10-branch _compute_payoff)

```python
# 6 payoff templates cover all 40 strategies based on leg structure
def _compute_payoff_generic(leg_defs: list, legs_data: list, net_debit_credit: float) -> dict:
    """Generic payoff using leg structure analysis."""
    buy_legs = [l for l in legs_data if l["action"] == "BUY"]
    sell_legs = [l for l in legs_data if l["action"] == "SELL"]
    is_net_debit = net_debit_credit > 0

    if len(leg_defs) == 1:
        # Single leg: debit (long) or credit (short)
        return _single_leg_payoff(legs_data[0], net_debit_credit)
    elif len(leg_defs) == 2 and len(set(l["option_type"] for l in legs_data)) == 1:
        # Two legs, same option type: vertical spread
        return _vertical_spread_payoff(legs_data, net_debit_credit)
    elif len(leg_defs) == 2 and len(set(l["option_type"] for l in legs_data)) == 2:
        # Two legs, mixed types: straddle/strangle/calendar
        return _vol_spread_payoff(legs_data, net_debit_credit)
    elif len(leg_defs) == 3:
        # Three legs: butterfly wing or ratio spread
        return _three_leg_payoff(legs_data, net_debit_credit)
    elif len(leg_defs) == 4:
        # Four legs: condor or iron family
        return _four_leg_payoff(legs_data, net_debit_credit)
    else:
        return {"max_profit": "complex", "max_loss": abs(net_debit_credit), "breakeven": "N/A"}
```

### Gate Unit Test Pattern

```python
# No LLM mocking needed — gate is a pure function
def test_gate_excludes_bearish_strategies_for_bullish_bias():
    registry = load_registry()
    context = GateContext(
        bias="bullish", iv_rank=45.0, iv_env="any",
        has_multi_expiry=True, available_margin=None,
        exclude_margin_intensive=False, min_oi_threshold=100,
        near_dte=30, iv_rank_for_earnings=45.0, is_earnings_proximity=False,
    )
    shortlist = filter_strategies(registry, context)
    assert all(
        "bearish" not in registry.strategies[name].bias
        for name in shortlist
    ), f"Bearish strategies leaked into bullish shortlist: {shortlist}"
    assert 3 <= len(shortlist) <= 6
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded STRATEGY_LIST of 10 | YAML registry of 40 strategies | This phase | Adding a strategy = one YAML block |
| if/elif dispatch in _get_strategy_type() | Registry key lookup | This phase | Deletes ~80 lines of dispatch code |
| _compute_payoff() with 10 branches | 6 generic payoff templates + leg structure | This phase | Covers all 40 strategies, ~60% code reduction |
| Single strategy string from LLM | Normalized registry key extracted from LLM output | This phase | Deterministic downstream routing |
| Strike selector outputs only options_legs string | Outputs anchor_strike + width + near/far_expiry | This phase | Enables declarative multi-leg construction |

**Deprecated/outdated after this phase:**
- `STRATEGY_LIST` constant in `options_strategy_selector.py`: replaced by registry keys
- `_get_strategy_type()` in `options_legs_builder.py`: replaced by `_normalize_strategy_key()`
- `_get_leg_types()` in `strike_expiry_selector.py`: replaced by registry `legs[key]` lookup
- `_compute_payoff()` in `options_legs_builder.py`: replaced by generic payoff templates

---

## Open Questions

1. **Where does `risk_config.yaml` live?**
   - What we know: D-11 says "config value in `risk_config.yaml`"; config system reads from `DEFAULT_CONFIG` dict in `default_config.py`
   - What's unclear: Should `risk_config.yaml` feed into `set_config()` at startup, or be a standalone YAML loaded directly by the gate? The existing config system uses `get_config()` but there is no existing YAML-loading path in it.
   - Recommendation: Add `available_margin` and `exclude_margin_intensive` as keys in `DEFAULT_CONFIG` (defaulting to `None` and `False`), and optionally load from `risk_config.yaml` in the same `strategies/__init__.py` load step. This avoids plumbing changes to the config system.

2. **Does AgentState TypedDict need explicit `Optional` keys for anchor_strike, width, near_expiry, far_expiry?**
   - What we know: LangGraph allows extra keys in state dicts, but typed state graphs may reject undeclared keys
   - What's unclear: Whether this project's LangGraph graph (in `setup.py`) uses strict TypedDict validation or plain dicts
   - Recommendation: Read `tradingagents/agents/utils/agent_states.py` at plan-writing time and add the four new keys as `Optional` fields. Defensive and zero-cost.

3. **How precise must `_extract_gate_context()` signal extraction be?**
   - What we know: Reports are free-text LLM output. IV rank appears in volatility_report as "IV Rank: N". Bias appears in investment_plan as directional language.
   - What's unclear: Edge cases where IV rank is not present (no volatility data) or bias is ambiguous.
   - Recommendation: Default to `iv_env="any"` when IV rank is unparseable, and `bias="neutral"` when no clear directional signal. These defaults are conservative and prevent gate from over-filtering.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (confirmed installed, 8 tests pass in 1.91s) |
| Config file | `pytest.ini` or pyproject.toml (check at plan time) |
| Quick run command | `pytest tests/agents/test_options_strategy_selector.py tests/agents/test_options_legs_builder.py tests/agents/test_strike_expiry_selector.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GATE-01 | Hard gate excludes bias-mismatched strategies | unit | `pytest tests/agents/test_strategy_gate.py::test_gate_bias_hard_gate -x` | Wave 0 |
| GATE-02 | Hard gate excludes margin_intensive when available_margin=None | unit | `pytest tests/agents/test_strategy_gate.py::test_gate_margin_failsafe -x` | Wave 0 |
| GATE-03 | Hard gate excludes multi_expiry strategies when only one expiry available | unit | `pytest tests/agents/test_strategy_gate.py::test_gate_multi_expiry -x` | Wave 0 |
| GATE-04 | Soft scoring boosts earnings-positive strategies near earnings | unit | `pytest tests/agents/test_strategy_gate.py::test_gate_soft_earnings_score -x` | Wave 0 |
| GATE-05 | Shortlist is 3-6 strategies in normal conditions | unit | `pytest tests/agents/test_strategy_gate.py::test_gate_shortlist_size -x` | Wave 0 |
| REG-01 | YAML registry loads without error and validates Pydantic models | unit | `pytest tests/agents/test_strategy_registry.py::test_registry_loads -x` | Wave 0 |
| REG-02 | All 40 strategies present in registry | unit | `pytest tests/agents/test_strategy_registry.py::test_registry_completeness -x` | Wave 0 |
| REG-03 | Every strategy in `strategies` has a matching entry in `legs` | unit | `pytest tests/agents/test_strategy_registry.py::test_registry_legs_coverage -x` | Wave 0 |
| LEGS-01 | Declarative builder resolves iron_condor to 4 legs with correct strike offsets | unit | `pytest tests/agents/test_options_legs_builder.py::test_declarative_iron_condor -x` | Wave 0 |
| LEGS-02 | Declarative builder resolves calendar spread using near/far expiry keys | unit | `pytest tests/agents/test_options_legs_builder.py::test_declarative_calendar_spread -x` | Wave 0 |
| LEGS-03 | Declarative builder output string matches existing LEG_PATTERN format | unit | `pytest tests/agents/test_options_legs_builder.py::test_leg_string_format_compat -x` | Wave 0 |
| SEL-01 | Updated selector node returns options_strategy key (regression) | unit | `pytest tests/agents/test_options_strategy_selector.py -x` | ✅ (update test_strategy_list_has_ten_entries) |
| SEL-02 | Strike/expiry selector emits anchor_strike, width, near_expiry, far_expiry keys | unit | `pytest tests/agents/test_strike_expiry_selector.py::test_anchor_width_output -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/agents/test_strategy_gate.py tests/agents/test_strategy_registry.py -x -q`
- **Per wave merge:** `pytest tests/agents/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/agents/test_strategy_gate.py` — covers GATE-01 through GATE-05
- [ ] `tests/agents/test_strategy_registry.py` — covers REG-01 through REG-03
- [ ] New test functions in `tests/agents/test_options_legs_builder.py` — covers LEGS-01 through LEGS-03
- [ ] New test function in `tests/agents/test_strike_expiry_selector.py` — covers SEL-02
- [ ] Update `tests/agents/test_options_strategy_selector.py` — fix `test_strategy_list_has_ten_entries` (asserts len==10, will fail after migration)

---

## Sources

### Primary (HIGH confidence)
- GitHub: `goldspanlabs/optopsy` — singles.py, spreads.py, butterflies.py, condors.py, iron_strategies.py, calendar.py — confirmed strategy names, leg definitions, quantities
- Source code: `tradingagents/agents/options/options_strategy_selector.py` — 10-strategy list, current factory pattern
- Source code: `tradingagents/agents/options/options_legs_builder.py` — _get_strategy_type, _compute_payoff dispatch
- Source code: `tradingagents/agents/options/strike_expiry_selector.py` — _get_leg_types, current output format
- Source code: `tradingagents/agents/managers/risk_manager.py` — options context section, stop-loss rules
- Pydantic v2 docs (verified version 2.12.5 installed): `model_validate()`, `BaseModel`, `Literal`

### Secondary (MEDIUM confidence)
- Optopsy README (inferred from source structure) — 46 strategy count reference; actual unique shapes confirmed at 40 after reviewing all 6 files

### Tertiary (LOW confidence)
- None — all critical claims verified against source files or installed packages

---

## Metadata

**Confidence breakdown:**
- Strategy taxonomy: HIGH — verified by reading all 6 optopsy strategy source files directly
- Standard stack: HIGH — pyyaml and pydantic confirmed installed; no new packages needed
- Architecture patterns: HIGH — derived from reading all referenced source files; patterns are deterministic refactoring, not speculation
- Pitfalls: HIGH — derived from reading existing test files and downstream parser code; backward compat risk is concrete
- Gate logic: MEDIUM — bias/IV extraction from free-text LLM reports has inherent variability; defaults documented

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable domain — pyyaml/pydantic APIs do not change frequently)
