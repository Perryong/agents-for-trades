# Phase 19: Frontend Restructure - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Remove the options toggle from the frontend, group report tabs into Equity/Options/Decision sections with visual headers, add a collapsible vol context banner at the top of every analyst report tab, and fix any TypeScript compilation errors from Phase 17's type changes.

</domain>

<decisions>
## Implementation Decisions

### Toggle removal (from D-06)
- Remove `enableOptions` state from App.tsx
- Remove `enable_options` from `onAnalyze` callback signature
- `getNodeList()` already takes no arguments (done in Phase 17) — callers must be updated

### Tab grouping (from D-07)
- Group report tabs into 3 visual sections: **Equity** (5) | **Options** (6) | **Decision** (2)
- Use the `group` field already added to REPORT_TABS in Phase 17
- Section headers rendered above the tab row — e.g., small labels or dividers between groups

### Vol context banner (from D-08)
- Collapsible banner pinned at top of every analyst tab (Equity group only)
- Shows the vol narrative paragraph from `state.result.vol_context`
- Uses native HTML `<details>/<summary>` — no component library
- Defaults expanded on first view
- Not shown on Options or Decision tabs — those have their own context

### TypeScript fixes (deferred from Phase 17)
- `App.tsx`: update `getNodeList(enableOptions)` → `getNodeList()`, remove `enableOptions` state, remove `setEnableOptions` from handleAnalyze, always pass full node list
- `ReportTabs.tsx`: replace `optionsOnly` filter with `group`-based section rendering
- `ProgressStepper.tsx`: update props — no `enableOptions` parameter, always show all nodes
- `useAnalysis.ts`: update complete event handler to read vol_context and vol_note_* fields

### Claude's Discretion
- Section header visual design (labels, dividers, colors)
- Vol banner expand/collapse behavior details
- Whether vol_note fields are surfaced in the UI (could show per-analyst vol note under each report)
- Tab ordering within groups (already defined in REPORT_TABS)

</decisions>

<specifics>
## Specific Ideas

- Tab grouping: `[ Equity ]  [ Options ]  [ Decision ]` as small uppercase labels above the tab buttons
- Vol banner: light background (blue-50/blue-900 for dark mode), collapsible via `<details open>`, monospace-ish font for the narrative

</specifics>

<canonical_refs>
## Canonical References

### Frontend files requiring modification
- `frontend/src/App.tsx` — Main app, enableOptions state, getNodeList calls, ProgressStepper/ReportTabs props
- `frontend/src/components/ReportTabs.tsx` — Tab rendering, optionsOnly filter → group-based sections
- `frontend/src/components/ReportPane.tsx` — Add vol context banner prop and rendering
- `frontend/src/components/ProgressStepper.tsx` — enableOptions prop removal
- `frontend/src/hooks/useAnalysis.ts` — Complete event: read vol_context, vol_note_* from state
- `frontend/src/types.ts` — Already updated in Phase 17 (group field, PRE_NODES, vol fields)

### Phase 17 type changes (already done)
- `frontend/src/types.ts` — `getNodeList()` no params, `AnalyzeRequest` no `enable_options`, `REPORT_TABS` has `group` field, `AnalysisResult` has vol fields

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `REPORT_TABS` with `group` field — already defined in Phase 17
- `AnalysisResult` with `vol_context` field — already in types.ts

### Established Patterns
- Tailwind CSS for all styling
- Dark mode via `dark:` prefix classes
- `<details>/<summary>` for collapsible sections (no external deps)

### Integration Points
- `App.tsx` → `ReportTabs` props: remove enableOptions, add vol_context
- `App.tsx` → `ProgressStepper` props: remove enableOptions
- `App.tsx` → `ReportPane` props: add volContext string
- `useAnalysis.ts` → complete event: populate vol_context and vol_note fields in result

</code_context>

<deferred>
## Deferred Ideas

- Per-analyst vol_note display under each report tab — could show "Vol Note: Given elevated IV..." at bottom of each analyst report. Nice-to-have, not required.
- User preference for default expand/collapse state of vol banner — localStorage persistence

</deferred>

---

*Phase: 19-frontend-restructure*
*Context gathered: 2026-04-09*
