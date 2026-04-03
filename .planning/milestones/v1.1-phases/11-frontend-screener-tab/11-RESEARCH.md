# Phase 11: Frontend Screener Tab - Research

**Researched:** 2026-04-02
**Domain:** React 19 / TypeScript / Tailwind CSS v4 frontend feature addition
**Confidence:** HIGH

## Summary

Phase 11 adds a Screener tab to the existing React 19 + Tailwind CSS v4 frontend. The backend is fully built (Phase 10): `POST /api/screen` returns a `ScreenResponse` with `status`, `data` (the serialized `ScreenerResult`), and `screened_at`. The frontend work is purely additive — no existing files are deleted, only extended.

The primary integration challenge is threading pre-fill state from the Screener tab into `ConfigSidebar`. The sidebar currently holds all ticker/config state internally via `useState`. Pre-fill requires either lifting ticker state up to `App.tsx` and passing it as a controlled prop, or adding a `prefillTicker` prop with an effect-based reset. The lift-state-up pattern is cleaner and fits the existing architecture (App already owns `enableOptions`).

The stale indicator (FE-03) is pure frontend logic: compare `screened_at` ISO string against `Date.now()` with a 15-minute threshold. No additional libraries are needed.

**Primary recommendation:** Build a `useScreener` hook mirroring `useAnalysis`, add `WatchlistPanel` + `PickCard` components, lift ticker state to App, and wire the new "Screener" tab into the existing navigation pattern.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Layout & Navigation
- New "Screener" tab alongside existing tabs — clear separation, easy to find
- Card-based WatchlistPanel with ticker, score bar, rationale summary, key metrics — scannable layout
- screened_at timestamp at top of panel with relative time ("5 min ago") + amber stale indicator when results are >15 min old (per FE-03)
- Manual "Refresh" button at top of screener tab to trigger new screen

#### Pick Card Design
- Each card shows: ticker (large), score badge, confidence %, rationale (2-line truncated), volume/momentum metrics
- Score visualization: colored progress bar (green >0.7, yellow 0.4-0.7, red <0.4)
- "Analyze" button on each card pre-fills ticker in analysis config and switches to analysis tab (per FE-02)

#### State & Loading
- Skeleton cards (5 placeholders) + "Screening market..." text during loading
- Empty state: "Click Refresh to screen the market" call-to-action
- Error state: inline error banner with retry button — non-blocking, recoverable

### Claude's Discretion
- Exact card dimensions and spacing
- Animation/transition details
- Tailwind utility class choices for responsive behavior
- Component file organization within frontend/src/components/

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FE-01 | WatchlistPanel component displays ranked screener results with key metrics per pick | `ScreenResponse.data` contains `picks[]` with `ticker`, `score`, `confidence`, `rationale`, `key_metrics` (volume_ratio, momentum_5d); component maps each pick to a `PickCard` |
| FE-02 | User can select a screener pick to pre-populate the analysis config and run the full pipeline | Requires lifting `ticker` state from `ConfigSidebar` to `App.tsx`; "Analyze" button on each card calls a callback with the ticker and switches `activeTab` to the analysis view |
| FE-03 | Stale data indicator shows `screened_at` timestamp prominently | `screened_at` is ISO 8601 UTC string from the API; compare `Date.now() - new Date(screened_at).getTime() > 15 * 60 * 1000` for the amber indicator; relative time formatted with `Intl.RelativeTimeFormat` |
</phase_requirements>

---

## Standard Stack

### Core (already installed — no new dependencies needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.2.4 | UI rendering, hooks | Already in use |
| TypeScript | ~5.9.3 | Type safety | Already in use |
| Tailwind CSS | 4.2.2 | Utility-first styling | Already in use via `@tailwindcss/vite` |
| Vite | 8.0.1 | Dev server + build | Already in use |

### No New Dependencies Required

All capabilities needed (relative time formatting, date comparison, fetch, state management) are available via browser APIs and the existing React + TypeScript stack. Specifically:

- **Relative time:** `Intl.RelativeTimeFormat` — standard browser API, no library needed
- **API calls:** Native `fetch()` — consistent with `useAnalysis` pattern
- **State:** `useReducer` — consistent with `useAnalysis` pattern
- **Skeleton loading:** CSS animation via Tailwind `animate-pulse` — already used in `ReportPane`

**Installation:** None required.

---

## Architecture Patterns

### Recommended Project Structure (additions only)
```
frontend/src/
├── components/
│   ├── WatchlistPanel.tsx    # new — screener results container (FE-01)
│   ├── PickCard.tsx          # new — individual pick card with Analyze button (FE-01, FE-02)
│   ├── ConfigSidebar.tsx     # MODIFIED — accept prefillTicker prop
│   ├── ReportTabs.tsx        # unchanged
│   ├── ReportPane.tsx        # unchanged
│   └── ProgressStepper.tsx   # unchanged
├── hooks/
│   ├── useScreener.ts        # new — mirrors useAnalysis pattern (FE-01, FE-03)
│   └── useAnalysis.ts        # unchanged
├── types.ts                  # MODIFIED — add ScreenerPick, ScreenerState types
└── App.tsx                   # MODIFIED — add screener tab, lift ticker state
```

### Pattern 1: Top-level Navigation Tabs (two-level tabs)

The existing app uses `activeTab` to switch between analysis report sub-tabs. The Screener feature is a **top-level section**, not a report sub-tab. Two clean approaches:

**Option A (recommended): Separate top-level tab state in App.tsx**
Add a `mainSection: 'analysis' | 'screener'` state alongside `activeTab`. The "Screener" button in the header nav sets `mainSection = 'screener'`. The report tabs only render when `mainSection === 'analysis'`. This keeps clean separation.

**Option B: Inject screener as an activeTab value**
Add `'screener'` as a valid `activeTab` value. The `ReportPane` conditionally renders `WatchlistPanel` when `activeTab === 'screener'`. Simpler but mixes report tabs with screener navigation.

The CONTEXT.md decision "New 'Screener' tab alongside existing tabs" is consistent with either. Option A is architecturally cleaner. Claude's discretion covers this implementation detail.

### Pattern 2: useScreener Hook (mirrors useAnalysis)

```typescript
// Source: modeled on frontend/src/hooks/useAnalysis.ts
type ScreenerStatus = 'idle' | 'loading' | 'done' | 'error';

interface ScreenerState {
  status: ScreenerStatus;
  picks: ScreenerPick[];
  screenedAt: string | null;   // ISO 8601 UTC
  errorMsg: string | null;
}
```

The hook calls `POST /api/screen` with a `ScreenRequest` body (max_picks, universe, llm_provider, quick_think_llm). On success it parses `ScreenResponse.data.picks` into `ScreenerPick[]` and stores `ScreenResponse.screened_at`.

### Pattern 3: Pre-fill Ticker — Lift State Up

`ConfigSidebar` currently owns `ticker` state internally. To support pre-fill from screener picks:

```typescript
// ConfigSidebar.tsx — add controlled prop
interface ConfigSidebarProps {
  onAnalyze: (request: AnalyzeRequest) => void;
  isRunning: boolean;
  prefillTicker?: string;   // new prop
}

export function ConfigSidebar({ onAnalyze, isRunning, prefillTicker }: ConfigSidebarProps) {
  const [ticker, setTicker] = useState(prefillTicker ?? '');

  // Sync when prefillTicker changes (from screener pick selection)
  useEffect(() => {
    if (prefillTicker) setTicker(prefillTicker);
  }, [prefillTicker]);
  // ...
}
```

App.tsx holds `prefillTicker` state. When the user clicks "Analyze" on a pick card:
1. `setPrefillTicker(pick.ticker)` — updates the controlled prop
2. `setMainSection('analysis')` — switches view to analysis

### Pattern 4: Stale Indicator Logic

```typescript
// Source: browser Intl API — no library needed
function getRelativeTime(isoString: string): string {
  const diffMs = Date.now() - new Date(isoString).getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return rtf.format(-diffMin, 'minute');
  return rtf.format(-Math.floor(diffMin / 60), 'hour');
}

function isStale(isoString: string): boolean {
  return Date.now() - new Date(isoString).getTime() > 15 * 60 * 1000;
}
```

### Pattern 5: Score Color Class Mapping

```typescript
// Derives Tailwind color class from score value
function scoreColorClass(score: number): string {
  if (score >= 0.7) return 'bg-green-500';
  if (score >= 0.4) return 'bg-yellow-400';
  return 'bg-red-500';
}
```

### Pattern 6: Skeleton Loading (consistent with ReportPane)

Tailwind `animate-pulse` is already used in `ReportPane`. Use same pattern for skeleton cards:

```tsx
// 5 skeleton placeholders during loading
{Array.from({ length: 5 }).map((_, i) => (
  <div key={i} className="animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700 h-32" />
))}
```

### API Contract (verified from source)

`POST /api/screen` request body:
```json
{
  "max_picks": 5,
  "universe": "sp500",
  "llm_provider": "openai",
  "quick_think_llm": "gpt-5-mini"
}
```

`POST /api/screen` response shape (from `api/schemas.py` + `screener_agent.py`):
```typescript
interface ScreenResponse {
  status: 'success' | 'partial' | 'error';
  screened_at: string;   // ISO 8601 UTC, empty string on hard error
  data: {
    picks: Array<{
      ticker: string;
      score: number;       // [0.0, 1.0]
      rationale: string;
      confidence: number;  // [0.0, 1.0]
      key_metrics: {
        volume_ratio?: number;
        momentum_5d?: number;
        // may also contain volume_score / momentum_score on degraded path
        [key: string]: number | undefined;
      };
      sector: string | null;
      market_cap: string | null;
    }>;
    screened_at: string;
    candidate_count: number;
    model_used: string;
    error: string | null;   // non-null on partial degradation
  };
}
```

The `screened_at` is available at two levels: top-level `ScreenResponse.screened_at` (preferred, always set on success/partial) and inside `data.screened_at`. Use top-level.

### Anti-Patterns to Avoid

- **Modifying REPORT_TABS to include screener:** REPORT_TABS maps to `AnalysisResult` keys. The screener has a completely different data shape — it must not be shoehorned into the report tab system.
- **Fetching on mount automatically:** The CONTEXT.md decision specifies "Click Refresh to screen the market" empty state — the screener should NOT auto-fetch on mount (would surprise users with a 5-8s delay).
- **Storing screened_at as a Date object:** Store as ISO string, parse only at render time to avoid stale reference issues.
- **Polling for freshness:** The stale indicator is a one-time display check at render time (>15 min old), not a polling mechanism. No `setInterval` needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Relative time display | Custom date formatting logic | `Intl.RelativeTimeFormat` (browser built-in) | Handles pluralization, locale, edge cases |
| Score progress bar | Custom SVG/canvas chart | CSS `width` + Tailwind color utilities | Score is a simple 0-1 value; a `<div>` with dynamic width is sufficient and matches app's no-charting-library constraint |
| Loading skeleton | Third-party skeleton lib | Tailwind `animate-pulse` + `<div>` | Already used in `ReportPane` — keeps consistency |

**Key insight:** This phase is a pure composition task — assemble existing patterns into new components. No new libraries, no charting, no complex state management beyond what `useAnalysis` already demonstrates.

---

## Common Pitfalls

### Pitfall 1: Tab Navigation Collision
**What goes wrong:** Adding 'screener' to the `activeTab` state that also controls which report sub-tab is active causes the analysis tab bar to show a broken "Screener" tab alongside Market/Technical/etc.
**Why it happens:** `REPORT_TABS` and the report pane both read from `activeTab`.
**How to avoid:** Use a separate `mainSection` state for the top-level Screener vs. Analysis switch. Keep `activeTab` purely for report sub-tab selection.
**Warning signs:** `REPORT_TABS.find(t => t.id === activeTab)` returning `undefined` and `reportContent` being null.

### Pitfall 2: Pre-fill Ticker Not Visible to User
**What goes wrong:** After clicking "Analyze" on a pick card, the screener view switches to the analysis section but the ticker input visually appears empty because `ConfigSidebar` state hasn't updated yet.
**Why it happens:** React state updates are asynchronous; if the section switch and state update happen in the same event, the render may not reflect the new value.
**How to avoid:** Set `prefillTicker` state before switching `mainSection`. React batches state updates in event handlers (React 18+), so both happen in the same commit, and the rendered sidebar will show the correct ticker.
**Warning signs:** Ticker input blank after navigation but API call includes the correct ticker.

### Pitfall 3: screened_at Empty String on Error
**What goes wrong:** Calling `new Date('').getTime()` returns `NaN`, making `isStale()` return `false` incorrectly (NaN comparisons are always false).
**Why it happens:** The API returns `screened_at: ""` on hard errors (schema-documented behavior).
**How to avoid:** Guard before parsing: `if (!screened_at) return`. Only display timestamp UI when `screened_at` is non-empty.
**Warning signs:** Stale indicator never showing on re-renders after an error + subsequent success.

### Pitfall 4: key_metrics Shape Varies Between Normal and Degraded Picks
**What goes wrong:** Assuming `key_metrics.volume_ratio` and `key_metrics.momentum_5d` always exist; the graceful degradation path in the screener agent uses `volume_score` and `momentum_score` instead.
**Why it happens:** The backend has two code paths for `key_metrics` (normal LLM path vs. auto-select fallback).
**How to avoid:** Use optional access everywhere: `pick.key_metrics?.volume_ratio ?? pick.key_metrics?.volume_score`. Display whichever metric is available, or `—` if neither.
**Warning signs:** Metric cells showing `undefined` or `NaN`.

### Pitfall 5: Tailwind v4 Dynamic Class Purging
**What goes wrong:** Dynamic class construction like `` `bg-${color}-500` `` gets purged by Tailwind v4 at build time because the full class string never appears in source.
**Why it happens:** Tailwind v4 scans source for complete class strings; dynamically-assembled strings are not detected.
**How to avoid:** Use a lookup object with complete class strings: `const COLOR_MAP = { green: 'bg-green-500', yellow: 'bg-yellow-400', red: 'bg-red-500' }`. This is how the existing codebase handles dynamic coloring (see `App.tsx` signal banner).
**Warning signs:** Color works in dev mode but disappears in `vite build` output.

---

## Code Examples

### useScreener Hook Structure
```typescript
// Source: modeled on frontend/src/hooks/useAnalysis.ts pattern
import { useReducer, useCallback } from 'react';
import type { ScreenerState, ScreenerPick } from '../types';

type ScreenerAction =
  | { type: 'FETCH_START' }
  | { type: 'FETCH_SUCCESS'; picks: ScreenerPick[]; screenedAt: string }
  | { type: 'FETCH_ERROR'; message: string }
  | { type: 'RESET' };

function reducer(state: ScreenerState, action: ScreenerAction): ScreenerState {
  switch (action.type) {
    case 'FETCH_START':
      return { ...state, status: 'loading', errorMsg: null };
    case 'FETCH_SUCCESS':
      return { status: 'done', picks: action.picks, screenedAt: action.screenedAt, errorMsg: null };
    case 'FETCH_ERROR':
      return { ...state, status: 'error', errorMsg: action.message };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

export function useScreener() {
  const [state, dispatch] = useReducer(reducer, initialState);

  const runScreen = useCallback(async () => {
    dispatch({ type: 'FETCH_START' });
    try {
      const res = await fetch('/api/screen', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ max_picks: 5, universe: 'sp500', llm_provider: 'openai', quick_think_llm: 'gpt-5-mini' }),
      });
      if (!res.ok) {
        dispatch({ type: 'FETCH_ERROR', message: `API error ${res.status}` });
        return;
      }
      const json = await res.json();
      if (json.status === 'error') {
        dispatch({ type: 'FETCH_ERROR', message: json.data?.error ?? 'Screener error' });
        return;
      }
      dispatch({ type: 'FETCH_SUCCESS', picks: json.data.picks, screenedAt: json.screened_at });
    } catch (err) {
      dispatch({ type: 'FETCH_ERROR', message: err instanceof Error ? err.message : String(err) });
    }
  }, []);

  return { state, runScreen };
}
```

### Score Progress Bar (Tailwind-safe)
```tsx
// Source: Tailwind v4 safe dynamic classes pattern (see App.tsx signal banner)
const SCORE_BAR_COLOR: Record<'green' | 'yellow' | 'red', string> = {
  green: 'bg-green-500',
  yellow: 'bg-yellow-400',
  red: 'bg-red-500',
};

function scoreColor(score: number): 'green' | 'yellow' | 'red' {
  if (score >= 0.7) return 'green';
  if (score >= 0.4) return 'yellow';
  return 'red';
}

// Usage in JSX:
<div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
  <div
    className={`${SCORE_BAR_COLOR[scoreColor(pick.score)]} h-2 rounded-full transition-all`}
    style={{ width: `${Math.round(pick.score * 100)}%` }}
  />
</div>
```

### ConfigSidebar Pre-fill Integration
```typescript
// Source: React 19 controlled input pattern
// In ConfigSidebar.tsx — add to existing props interface:
interface ConfigSidebarProps {
  onAnalyze: (request: AnalyzeRequest) => void;
  isRunning: boolean;
  prefillTicker?: string;  // ADD
}

// In ConfigSidebar function body — add useEffect:
import { useState, useEffect } from 'react';

useEffect(() => {
  if (prefillTicker) {
    setTicker(prefillTicker.toUpperCase());
  }
}, [prefillTicker]);
```

### Stale Indicator
```tsx
// Source: MDN Intl.RelativeTimeFormat, browser-standard API
function getRelativeTime(isoString: string): string {
  const diffMs = Date.now() - new Date(isoString).getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return 'just now';
  const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
  if (diffMin < 60) return rtf.format(-diffMin, 'minute');
  return rtf.format(-Math.floor(diffMin / 60), 'hour');
}

function isStale(isoString: string): boolean {
  if (!isoString) return false;
  return Date.now() - new Date(isoString).getTime() > 15 * 60 * 1000;
}

// Usage:
{screenedAt && (
  <span className={isStale(screenedAt) ? 'text-amber-500' : 'text-gray-500 dark:text-gray-400'}>
    Screened {getRelativeTime(screenedAt)}
    {isStale(screenedAt) && ' (stale)'}
  </span>
)}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| moment.js for relative time | `Intl.RelativeTimeFormat` (built-in) | ES2020 / ~2020 | No dependency needed |
| Manual CSS for progress bars | Tailwind utility classes with inline width | Tailwind v2+ | Simpler, no custom CSS |
| `React.FC<Props>` generic | Function declaration with typed props inline | React 18+ community standard | No difference in practice; project already uses function declaration style |

**Deprecated/outdated:**
- `React.FC` type annotation: project does not use it (see all components) — follow same pattern
- `moment.js` / `dayjs` for simple relative time: overkill when `Intl.RelativeTimeFormat` exists

---

## Open Questions

1. **Top-level tab navigation implementation**
   - What we know: `activeTab` controls report sub-tab; "Screener" is a peer section
   - What's unclear: Whether to use `mainSection` state or hijack `activeTab`
   - Recommendation: Use separate `mainSection: 'analysis' | 'screener'` state in App.tsx (Claude's discretion)

2. **ScreenRequest config exposure in the UI**
   - What we know: `ScreenRequest` accepts `llm_provider` and `quick_think_llm`
   - What's unclear: Should the screener tab expose LLM settings or hardcode defaults?
   - Recommendation: Hardcode defaults for v1.1 (`openai` / `gpt-5-mini`) — the screener is a one-click action, not a configurable pipeline. Avoids UI complexity.

3. **Partial status ("partial") display**
   - What we know: Backend returns `status: "partial"` when LLM parse failed + auto-selection was used; picks are still valid
   - What's unclear: Should the UI surface this to the user?
   - Recommendation: Show a subtle "Auto-selected (LLM unavailable)" note below the panel header when `status === 'partial'`. Non-blocking — picks are usable.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None detected in frontend — no Jest/Vitest config found |
| Config file | None — Wave 0 gap |
| Quick run command | N/A until framework installed |
| Full suite command | N/A until framework installed |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FE-01 | WatchlistPanel renders picks with ticker, score, confidence, rationale, metrics | manual smoke | open dev server, click Refresh | ❌ Wave 0 |
| FE-01 | Skeleton cards render during loading state | manual smoke | trigger loading state | ❌ Wave 0 |
| FE-01 | Empty state renders when no picks | manual smoke | check initial render | ❌ Wave 0 |
| FE-02 | Clicking Analyze on a pick pre-fills ticker and switches to analysis section | manual smoke | click Analyze button | ❌ Wave 0 |
| FE-03 | screened_at displays as relative time | manual smoke | check timestamp display | ❌ Wave 0 |
| FE-03 | Amber stale indicator appears when results >15 min old | manual smoke | mock old screened_at | ❌ Wave 0 |

**Note:** The frontend project has no test framework installed (no Jest, Vitest, or testing-library found). All validation is manual smoke testing against the running dev server. This is consistent with the existing frontend which also has no tests.

### Sampling Rate
- **Per task commit:** `cd frontend && npm run build` (TypeScript compile check — fast, catches type errors)
- **Per wave merge:** `cd frontend && npm run build && npm run lint`
- **Phase gate:** Build passes + manual smoke of all 3 requirements before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] No test framework — manual smoke testing is the validation path (acceptable given project pattern)
- [ ] TypeScript compilation via `npm run build` serves as the automated correctness gate

---

## Sources

### Primary (HIGH confidence)
- Direct source read: `frontend/src/App.tsx` — tab state, dark mode, component composition
- Direct source read: `frontend/src/hooks/useAnalysis.ts` — hook pattern with useReducer
- Direct source read: `frontend/src/components/ConfigSidebar.tsx` — ticker state, AnalyzeRequest shape
- Direct source read: `frontend/src/components/ReportTabs.tsx` — tab navigation pattern
- Direct source read: `frontend/src/types.ts` — REPORT_TABS, AnalyzeRequest, AnalysisResult
- Direct source read: `api/schemas.py` — ScreenRequest, ScreenResponse verified shapes
- Direct source read: `tradingagents/agents/screener/screener_agent.py` — TopPick, ScreenerResult fields, graceful degradation path
- Direct source read: `frontend/package.json` — confirmed React 19, Tailwind CSS v4, no test framework
- MDN Intl.RelativeTimeFormat — browser-standard API, ES2020

### Secondary (MEDIUM confidence)
- Tailwind CSS v4 class purging behavior — documented behavior; verified by App.tsx pattern using full class strings in conditional expressions

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — read directly from package.json and existing source
- Architecture: HIGH — patterns derived from reading existing hooks and components verbatim
- API contract: HIGH — read directly from api/schemas.py and screener_agent.py
- Pitfalls: HIGH (Tailwind purge, empty screened_at) / MEDIUM (pre-fill timing) — based on known React and Tailwind behaviors
- Validation: HIGH — confirmed no test framework present

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable stack — React, Tailwind, TypeScript change slowly)
