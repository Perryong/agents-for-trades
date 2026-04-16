# Story 4.5: Reasoning Chain — Expandable Agent Breakdown

Status: review

## Story

As a user,
I want to expand a recommendation to see the full agent-by-agent reasoning chain,
so that I understand why the system made this recommendation and can assess agent disagreements.

## Acceptance Criteria

1. **Given** a recommendation card is displayed **When** the user clicks the card body or presses `Enter` **Then** the ReasoningChain component expands inline below the trade specs (150ms height transition)

2. **And** each agent is listed with: name, signal direction + confidence (colored), evidence text

3. **And** dissenting agents are highlighted with amber name color

4. **And** a "Risk Judge Resolution" section at the bottom shows how conflicting signals were resolved and why the strategy was selected

5. **And** clicking again or pressing `Esc` collapses the reasoning chain

6. **And** expanding does not change the card's approval state

## Tasks / Subtasks

- [x] Task 1: Create ReasoningChain component (AC: #1-4)
  - [x] Created ReasoningChain.tsx with signals + expanded props
  - [x] Agent list with name, colored signal badge + confidence, rationale
  - [x] Dissent detection via majority signal comparison, amber name color
  - [x] Risk Judge Resolution section (detects "risk judge" agent or shows majority summary)
  - [x] 150ms max-height CSS transition
- [x] Task 2: Wire expand/collapse into RecommendationCard (AC: #1, #5, #6)
  - [x] Added expanded + onToggleExpand props
  - [x] Card body click toggles expand, action buttons use stopPropagation
  - [x] ReasoningChain renders below TradeSpecGrid
  - [x] Expanding does not change approval state
- [x] Task 3: Wire expand into RecommendationList with Enter/Esc (AC: #1, #5)
  - [x] expandedId state, passed to each card
  - [x] Enter toggles expand on focused card
  - [x] Esc collapses expanded card first, then deselects focus
- [x] Task 4: Build verification (AC: #1-6)
  - [x] tsc --noEmit: zero errors
  - [x] vite build: 210 modules, zero errors

## Dev Notes

### Architecture & Approach

**ReasoningChain component receives `AgentSignalSummary[]` from the recommendation's `agent_signals` field.** Each signal has: agent_name, signal (BUY/SELL/HOLD/bullish/bearish/neutral), confidence, rationale.

**Dissent detection:** Compare each agent's signal to the majority signal. If an agent's signal differs from the mode, it's a dissenter.

**Height transition pattern:**
```tsx
<div className={`transition-[max-height] duration-150 ease-out overflow-hidden ${expanded ? 'max-h-[500px]' : 'max-h-0'}`}>
  {/* content */}
</div>
```

**Risk Judge Resolution:** The last entry in agent_signals typically represents the risk judge's synthesis. If no explicit "Risk Judge" agent exists, show a summary derived from the majority signal.

### File Locations

| File | Action | Purpose |
|------|--------|---------|
| `frontend/src/components/ReasoningChain.tsx` | NEW | Expandable agent breakdown |
| `frontend/src/components/RecommendationCard.tsx` | MODIFY | Add expanded/onToggleExpand props |
| `frontend/src/components/RecommendationList.tsx` | MODIFY | Track expandedId, wire Enter/Esc |

### Previous Story Intelligence (4.4)

- RecommendationCard has onClick, onApprove, onSkip props
- RecommendationList has focusedIndex for keyboard nav, ArrowUp/Down/Esc handlers
- Action buttons use stopPropagation to avoid triggering card click
- Card body click currently toggles focus selection

### Anti-Patterns to Avoid

- **DO NOT** use JavaScript-measured height — use CSS max-height transition
- **DO NOT** change approval state on expand/collapse
- **DO NOT** add new API calls — agent_signals already included in recommendation data

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Transition & Animation Patterns]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.5]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None.

### Completion Notes List

- Created ReasoningChain component with 150ms CSS max-height transition
- Dissent detection via majority signal comparison, dissenting agents highlighted amber
- Risk Judge Resolution section auto-detects "risk judge" agent or shows majority summary
- Wired expand/collapse into RecommendationCard (expanded + onToggleExpand props)
- RecommendationList tracks expandedId, Enter toggles, Esc collapses-then-deselects
- Removed old selected prop from RecommendationCard (replaced by focused + expanded)

### Change Log

- 2026-04-15: Story 4.5 implemented — expandable reasoning chain with dissent + keyboard control

### File List

- `frontend/src/components/ReasoningChain.tsx` — NEW: Expandable agent-by-agent breakdown
- `frontend/src/components/RecommendationCard.tsx` — MODIFIED: Added expanded/onToggleExpand, renders ReasoningChain
- `frontend/src/components/RecommendationList.tsx` — MODIFIED: Added expandedId, Enter/Esc wiring
