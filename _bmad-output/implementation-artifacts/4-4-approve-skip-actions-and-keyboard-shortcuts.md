# Story 4.4: Approve/Skip Actions and Keyboard Shortcuts

Status: review

## Story

As a user,
I want to approve or skip recommendations with a single action or keyboard shortcut,
so that my morning review is fast and decisive with no confirmation dialogs.

## Acceptance Criteria

1. **Given** a recommendation card is displayed with pending status **When** the user clicks Approve or presses `A` **Then** the card transitions to approved state (subtle green tint, "Approved" replaces actions) **And** the trade is queued for execution via the backend

2. **When** the user clicks Skip or presses `S` **Then** the card is grayed out and moves to the bottom of the list

3. **When** valid_until expires without action **Then** the card transitions to expired state (faded, non-interactive)

4. **And** the status bar updates: "3 approved, 1 skipped, 2 expired"

5. **And** arrow keys navigate between cards, `Enter` expands reasoning (placeholder — actual expand in 4.5), `Esc` collapses

6. **And** no confirmation dialogs are shown for any action

## Tasks / Subtasks

- [x] Task 1: Add Approve/Skip action buttons to RecommendationCard (AC: #1, #2, #6)
  - [x] Added `onApprove`, `onSkip`, `focused` props
  - [x] Compact action buttons for pending cards: "Approve A" (green), "Skip S" (secondary)
  - [x] Buttons use stopPropagation, no confirmation dialogs
- [x] Task 2: Wire approve/skip from RecommendationList to hook (AC: #1, #2)
  - [x] RecommendationList accepts recommendations + onApprove/onSkip as props
  - [x] Re-sorts: pending first, then approved, then skipped/expired at bottom
- [x] Task 3: Add keyboard navigation for recommendation cards (AC: #5)
  - [x] focusedIndex state with ArrowUp/Down, Esc to deselect
  - [x] Visual ring indicator on focused card
  - [x] Input focus guard
- [x] Task 4: Add A/S keyboard shortcuts for approve/skip (AC: #1, #2)
  - [x] A approves focused pending card, S skips it
  - [x] Guards: input focus, pending status, direction exists
- [x] Task 5: Add expiry auto-detection (AC: #3)
  - [x] 60-second interval checks valid_until, transitions to expired
  - [x] Expired cards non-interactive (no action buttons)
- [x] Task 6: Update StatusBar with session summary (AC: #4)
  - [x] StatusBar accepts sessionSummary prop
  - [x] useRecommendations lifted to App.tsx, summary computed via useMemo
  - [x] Format: "3 approved, 1 skipped, 2 expired"
- [x] Task 7: Build verification (AC: #1-6)
  - [x] tsc --noEmit: zero errors
  - [x] vite build: 209 modules, zero errors

## Dev Notes

### Architecture & Approach

**Existing infrastructure from Story 4.3:**
- `useRecommendations` hook already has `approve(id)` and `skip(id)` methods that POST to backend and update local state
- `RecommendationCard` already has status-based styling (approved=green tint, skipped=opacity-50, expired=opacity-30)
- `RecommendationList` already tracks `selectedId` state

**What needs to change:**
- RecommendationCard: add action buttons + callback props
- RecommendationList: pass approve/skip, add keyboard navigation with focusedIndex, re-sort after skip
- useRecommendations: add expiry checking interval
- StatusBar: accept and display session summary prop
- App.tsx: compute summary, lift useRecommendations to App level so StatusBar can access counts

**Key decision — lift useRecommendations to App.tsx:**
The StatusBar needs recommendation counts, but it's outside the Recommendations tab. So `useRecommendations` should be called in App.tsx and passed down to RecommendationList as props.

### Technical Requirements

- No new dependencies
- Keyboard handlers follow existing pattern from Story 4.2 (input focus guard)
- All actions are immediate — no confirmation dialogs per UX spec

### File Locations

| File | Action | Purpose |
|------|--------|---------|
| `frontend/src/components/RecommendationCard.tsx` | MODIFY | Add action buttons + callback props |
| `frontend/src/components/RecommendationList.tsx` | MODIFY | Add keyboard nav, pass approve/skip, re-sort |
| `frontend/src/hooks/useRecommendations.ts` | MODIFY | Add expiry interval |
| `frontend/src/components/StatusBar.tsx` | MODIFY | Add sessionSummary prop |
| `frontend/src/App.tsx` | MODIFY | Lift useRecommendations, compute summary, pass to StatusBar |

### Previous Story Intelligence (4.3)

- useRecommendations already returns { recommendations, loading, error, refresh, approve, skip }
- approve/skip methods do optimistic local state update + POST to backend
- RecommendationCard has STATUS_CLASSES for pending/approved/skipped/expired
- RecommendationList has selectedId state but no focusedIndex for keyboard nav
- Cards are sorted by confidence descending

### Anti-Patterns to Avoid

- **DO NOT** add confirmation dialogs — single action fires immediately
- **DO NOT** add the reasoning chain expand — that's Story 4.5
- **DO NOT** add new API endpoints — approve/skip already exist from 4.3
- **DO NOT** use tabIndex or complex focus management — use state-based focus with visual ring

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Action Hierarchy]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Flow Optimization Principles]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.4]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation.

### Completion Notes List

- Added Approve/Skip action buttons to RecommendationCard with keyboard hints (A/S)
- RecommendationList now accepts props: recommendations, loading, error, onApprove, onSkip
- Sorted display: pending first (by confidence), then approved, then skipped/expired
- Keyboard navigation: ArrowUp/Down with focusedIndex, visual ring, Esc deselect
- A/S shortcuts approve/skip focused pending card with input focus guard
- 60-second expiry interval auto-transitions pending cards past valid_until
- Lifted useRecommendations to App.tsx for StatusBar access
- StatusBar shows session summary: "X approved, Y skipped, Z expired"
- Build clean: tsc + vite

### Change Log

- 2026-04-15: Story 4.4 implemented — approve/skip actions, keyboard shortcuts, session summary

### File List

- `frontend/src/components/RecommendationCard.tsx` — MODIFIED: Added onApprove/onSkip/focused props, action buttons
- `frontend/src/components/RecommendationList.tsx` — MODIFIED: Props-based, keyboard nav, re-sorting
- `frontend/src/hooks/useRecommendations.ts` — MODIFIED: Added 60s expiry interval
- `frontend/src/components/StatusBar.tsx` — MODIFIED: Added sessionSummary prop
- `frontend/src/App.tsx` — MODIFIED: Lifted useRecommendations, computed session summary, passed props
