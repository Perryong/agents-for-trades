# Phase 11: Frontend Screener Tab - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a "Screener" tab to the React frontend that displays ranked stock picks from the POST /api/screen endpoint and lets users select a pick to pre-populate and launch the analysis pipeline. This phase delivers frontend changes only — no backend changes, no CLI changes.

</domain>

<decisions>
## Implementation Decisions

### Layout & Navigation
- New "Screener" tab alongside existing tabs — clear separation, easy to find
- Card-based WatchlistPanel with ticker, score bar, rationale summary, key metrics — scannable layout
- screened_at timestamp at top of panel with relative time ("5 min ago") + amber stale indicator when results are >15 min old (per FE-03)
- Manual "Refresh" button at top of screener tab to trigger new screen

### Pick Card Design
- Each card shows: ticker (large), score badge, confidence %, rationale (2-line truncated), volume/momentum metrics
- Score visualization: colored progress bar (green >0.7, yellow 0.4-0.7, red <0.4)
- "Analyze" button on each card pre-fills ticker in analysis config and switches to analysis tab (per FE-02)

### State & Loading
- Skeleton cards (5 placeholders) + "Screening market..." text during loading
- Empty state: "Click Refresh to screen the market" call-to-action
- Error state: inline error banner with retry button — non-blocking, recoverable

### Claude's Discretion
- Exact card dimensions and spacing
- Animation/transition details
- Tailwind utility class choices for responsive behavior
- Component file organization within frontend/src/components/

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/App.tsx` — main app with tab state management, dark mode, useAnalysis hook
- `frontend/src/components/ConfigSidebar.tsx` — config form with ticker input, analyst selection
- `frontend/src/components/ReportTabs.tsx` — existing tab navigation pattern
- `frontend/src/hooks/useAnalysis.ts` — analysis state management + API call pattern
- `frontend/src/types.ts` — REPORT_TABS, AnalyzeRequest types
- Tailwind CSS v4 with dark mode support via `dark:` prefix

### Established Patterns
- Components in `frontend/src/components/` as named exports
- Hooks in `frontend/src/hooks/` with `use*` prefix
- Tab state managed in App.tsx with `activeTab` + `setActiveTab`
- API calls use fetch() with JSON parsing
- Dark mode via `dark:bg-gray-800` Tailwind classes + localStorage persistence

### Integration Points
- App.tsx — needs screener tab in navigation + screener panel rendering
- ConfigSidebar.tsx — needs to accept pre-filled ticker from screener pick
- POST /api/screen (Phase 10) — data source for screener results

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>
