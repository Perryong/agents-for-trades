---
plan: 260409-uqs
type: execute
wave: 1
depends_on: []
files_modified:
  - tradingagents/graph/propagation.py
  - tradingagents/graph/trading_graph.py
  - tradingagents/agents/analysts/social_media_analyst.py
  - tradingagents/agents/analysts/news_analyst.py
  - tradingagents/agents/analysts/fundamentals_analyst.py
  - tradingagents/llm_clients/google_client.py
autonomous: true
must_haves:
  truths:
    - "propagation.py initial state includes vol_context and all vol_note_* fields"
    - "Stale enable_options=True comment is removed from propagation.py"
    - "trading_graph.py _log_state dict includes vol_context and vol_note_* fields"
    - "social_media_analyst, news_analyst, fundamentals_analyst never reference undefined vol_note"
    - "google_client.py retries 5 times with 5s base delay (not 3x15s)"
  artifacts:
    - path: "tradingagents/graph/propagation.py"
      provides: "Initial state with vol_context and vol_note_* fields"
    - path: "tradingagents/graph/trading_graph.py"
      provides: "_log_state with vol fields included"
    - path: "tradingagents/agents/analysts/social_media_analyst.py"
      provides: "vol_note always defined before use"
    - path: "tradingagents/agents/analysts/news_analyst.py"
      provides: "vol_note always defined before use"
    - path: "tradingagents/agents/analysts/fundamentals_analyst.py"
      provides: "vol_note always defined before use"
    - path: "tradingagents/llm_clients/google_client.py"
      provides: "_MAX_RETRIES=5, _BASE_DELAY=5"
---

<objective>
Fix 5 v2.0 tech debt items and improve Gemini 503 retry handling.

Purpose: Eliminate latent bugs (undefined vol_note variable, missing state fields in logs)
and make Gemini high-demand errors recover faster with more attempts.
Output: 6 patched files, no new tests needed (all changes are mechanical corrections).
</objective>

<context>
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix propagation.py — add vol fields to initial state and fix stale comment</name>
  <files>tradingagents/graph/propagation.py</files>
  <action>
In `create_initial_state()` return dict, after the existing options pipeline block, add the
vol pipeline fields with None defaults:

```python
# Vol-context pipeline fields — None until Vol Context node populates them
"vol_context": None,
"vol_note_market": None,
"vol_note_technical": None,
"vol_note_social": None,
"vol_note_news": None,
"vol_note_fundamentals": None,
```

Also on line 55, update the stale comment on the options pipeline block from:
  `# Options pipeline fields — empty string default, populated only when enable_options=True`
to:
  `# Options pipeline fields — always active (enable_options toggle removed)`

No other changes to this file.
  </action>
  <verify>
    <automated>python -c "from tradingagents.graph.propagation import Propagator; s = Propagator().create_initial_state('AAPL', '2026-01-01'); assert 'vol_context' in s and s['vol_context'] is None; assert 'vol_note_market' in s and s['vol_note_market'] is None; assert 'vol_note_social' in s; assert 'vol_note_news' in s; assert 'vol_note_fundamentals' in s; assert 'vol_note_technical' in s; print('OK')"</automated>
  </verify>
  <done>
    create_initial_state() returns a dict containing vol_context=None and all five
    vol_note_* keys set to None. The stale enable_options=True comment is gone.
  </done>
</task>

<task type="auto">
  <name>Task 2: Fix trading_graph._log_state and analyst vol_note NameError</name>
  <files>
    tradingagents/graph/trading_graph.py
    tradingagents/agents/analysts/social_media_analyst.py
    tradingagents/agents/analysts/news_analyst.py
    tradingagents/agents/analysts/fundamentals_analyst.py
  </files>
  <action>
**trading_graph.py — _log_state dict (lines ~262-268):**
After the existing `"greeks_report"` entry, add:

```python
# Vol-context pipeline fields
"vol_context": final_state.get("vol_context"),
"vol_note_market": final_state.get("vol_note_market"),
"vol_note_technical": final_state.get("vol_note_technical"),
"vol_note_social": final_state.get("vol_note_social"),
"vol_note_news": final_state.get("vol_note_news"),
"vol_note_fundamentals": final_state.get("vol_note_fundamentals"),
```

**social_media_analyst.py — inside `social_media_analyst_node`:**
Before the `if len(result.tool_calls) == 0:` block, add:
```python
vol_note = None
```
Then inside that block, keep `vol_note = extract_vol_note(report)` as-is.
In the return dict, change `"vol_note_social": vol_note if len(result.tool_calls) == 0 else None`
to simply `"vol_note_social": vol_note` (vol_note is already None when there are tool calls).

**news_analyst.py — same pattern:**
Before the `if len(result.tool_calls) == 0:` block, add:
```python
vol_note = None
```
Simplify return: `"vol_note_news": vol_note`

**fundamentals_analyst.py — same pattern:**
Before the `if len(result.tool_calls) == 0:` block, add:
```python
vol_note = None
```
Simplify return: `"vol_note_fundamentals": vol_note`

Note: market_analyst.py and technical_analyst.py already assign vol_note unconditionally
outside the if-block — do NOT touch those files.
  </action>
  <verify>
    <automated>python -c "
import ast, sys
files = [
    'tradingagents/agents/analysts/social_media_analyst.py',
    'tradingagents/agents/analysts/news_analyst.py',
    'tradingagents/agents/analysts/fundamentals_analyst.py',
]
for f in files:
    src = open(f).read()
    assert 'vol_note = None' in src, f'{f}: missing vol_note = None guard'
    assert 'if len(result.tool_calls) == 0 else None' not in src, f'{f}: ternary still present'
    print(f'OK: {f}')
"
</automated>
  </verify>
  <done>
    _log_state dict contains all six vol_* fields using .get() safe access.
    All three fragile analysts initialize vol_note=None before the conditional block;
    the redundant ternary `else None` is removed. No NameError can occur.
  </done>
</task>

<task type="auto">
  <name>Task 3: Tune google_client.py retry parameters for faster 503 recovery</name>
  <files>tradingagents/llm_clients/google_client.py</files>
  <action>
Change the two module-level constants at the top of the file:

From:
```python
_MAX_RETRIES = 3
_BASE_DELAY = 15  # seconds
```

To:
```python
_MAX_RETRIES = 5
_BASE_DELAY = 5  # seconds
```

This gives retry delays of 5s, 10s, 20s, 40s, 80s (total ~155s max wait before
fallback) instead of the current 15s, 30s, 60s (105s, only 3 chances). More
attempts with shorter initial delays catches transient 503 spikes faster while
the longer later delays still respect sustained high-demand windows.

No other changes to this file.
  </action>
  <verify>
    <automated>python -c "
import tradingagents.llm_clients.google_client as gc
assert gc._MAX_RETRIES == 5, f'Expected 5, got {gc._MAX_RETRIES}'
assert gc._BASE_DELAY == 5, f'Expected 5, got {gc._BASE_DELAY}'
print('OK: _MAX_RETRIES=5, _BASE_DELAY=5')
"
</automated>
  </verify>
  <done>
    google_client.py has _MAX_RETRIES=5 and _BASE_DELAY=5. Retry schedule is
    5s/10s/20s/40s/80s before triggering the model fallback chain.
  </done>
</task>

</tasks>

<verification>
Run all three automated checks sequentially to confirm all fixes are in place:

```bash
python -c "from tradingagents.graph.propagation import Propagator; s = Propagator().create_initial_state('AAPL', '2026-01-01'); assert 'vol_context' in s and s['vol_context'] is None; assert all(k in s for k in ['vol_note_market','vol_note_technical','vol_note_social','vol_note_news','vol_note_fundamentals']); print('propagation OK')"

python -c "
files = ['tradingagents/agents/analysts/social_media_analyst.py','tradingagents/agents/analysts/news_analyst.py','tradingagents/agents/analysts/fundamentals_analyst.py']
for f in files:
    src = open(f).read()
    assert 'vol_note = None' in src
    assert 'else None' not in src.split('vol_note')[1].split('return')[0] if 'vol_note' in src else True
    print(f'OK: {f}')
"

python -c "import tradingagents.llm_clients.google_client as gc; assert gc._MAX_RETRIES == 5 and gc._BASE_DELAY == 5; print('google_client OK')"
```

Also grep to confirm stale comment is gone:
```bash
grep -n "enable_options=True" tradingagents/graph/propagation.py && echo "FAIL: stale comment remains" || echo "OK: comment removed"
```
</verification>

<success_criteria>
- propagation.py create_initial_state() returns vol_context=None and vol_note_{market,technical,social,news,fundamentals}=None
- propagation.py line ~55 comment no longer mentions "enable_options=True"
- trading_graph.py _log_state dict includes vol_context and all five vol_note_* fields via .get()
- social_media_analyst.py, news_analyst.py, fundamentals_analyst.py each have `vol_note = None` before the tool_calls conditional; the `else None` ternary is removed
- google_client.py _MAX_RETRIES=5 and _BASE_DELAY=5
</success_criteria>

<output>
No SUMMARY.md needed — this is a quick fix plan. Commit with:
`fix(tech-debt): v2.0 audit fixes — vol state init, log fields, analyst vol_note guard, gemini retry tuning`
</output>
