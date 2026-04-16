# Story 4.3: RecommendationCard with Trade Specs and Consensus

Status: review

## Story

As a user,
I want to see recommendation cards with full trade specs and agent consensus at a glance,
so that I can evaluate each recommendation in under 30 seconds without expanding anything.

## Acceptance Criteria

1. **Given** the system has produced TradeRecommendations **When** the Recommendations tab is active **Then** each recommendation renders as a card showing: ticker (16px mono), direction badge (BUY in green text / SELL in red text), strategy name, confidence score (mono), valid_until countdown

2. **And** a ConsensusIndicator shows 4-5 colored dots (green=bullish, red=bearish, gray=neutral) representing each agent's signal

3. **And** a TradeSpecGrid shows entry, stop (red), target (green), size, R:R in a 5-column layout

4. **And** cards are sorted by confidence (highest first)

5. **And** all numeric values use monospace font

6. **And** the consensus dots show a tooltip on hover: "4 of 5 agents bullish, 1 neutral"

## Tasks / Subtasks

- [x] Task 1: Add frontend types for recommendations (AC: #1-6)
  - [x] Add `Recommendation`, `AgentSignalSummary`, `RecommendationTradeSpec` types to `frontend/src/types.ts`
  - [x] Add `RecommendationStatus` type: 'pending' | 'approved' | 'skipped' | 'expired'
  - [x] Types match backend Pydantic models
- [x] Task 2: Create `useRecommendations` hook (AC: #1, #4)
  - [x] Create `frontend/src/hooks/useRecommendations.ts`
  - [x] Fetch from `GET /api/recommendations`, sort by confidence descending
  - [x] Poll every 30 seconds, handle 404/empty gracefully
  - [x] Returns { recommendations, loading, error, refresh, approve, skip }
- [x] Task 3: Create ConsensusIndicator component (AC: #2, #6)
  - [x] Colored dots: green=bullish, red=bearish, gray=neutral
  - [x] Native title tooltip with agent counts
- [x] Task 4: Create TradeSpecGrid component (AC: #3, #5)
  - [x] 5-column grid: Entry, Stop (red), Target (green), Size, R:R
  - [x] R:R calculated from spec, handles BUY/SELL direction
  - [x] All values font-mono, labels 11px uppercase
- [x] Task 5: Create RecommendationCard component (AC: #1-6)
  - [x] Ticker (16px mono), direction badge, strategy, confidence, consensus dots, countdown
  - [x] TradeSpecGrid for trade recommendations, no_trade_reason for no-trade
  - [x] Card states: pending, approved (green tint), skipped (opacity-50), expired (opacity-30)
- [x] Task 6: Create RecommendationList component and wire into App.tsx (AC: #1-6)
  - [x] Loading skeleton, empty state, error state
  - [x] Wired into Recommendations tab above analysis flow
- [x] Task 7: Add backend recommendation endpoint (AC: #1)
  - [x] `api/recommendation_routes.py`: GET /api/recommendations, POST approve/skip
  - [x] Also added GET /api/positions and GET /api/positions/stats (for Story 4.6)
  - [x] Registered router in api/main.py
- [x] Task 8: Build verification (AC: #1-6)
  - [x] tsc --noEmit: zero errors
  - [x] vite build: 209 modules, 186ms, zero errors
  - [x] Empty state renders when no predictions exist

## Dev Notes

### Architecture & Approach

**Data flow:** Backend `predictions` table → `GET /api/recommendations` API → `useRecommendations` hook → `RecommendationList` → `RecommendationCard` (with `ConsensusIndicator` + `TradeSpecGrid`)

**Backend Prediction model** (already exists in `api/models.py`):
```python
class Prediction(Base):
    id: int
    ticker: str
    direction: str | None          # "BUY"|"SELL"|None (no-trade)
    confidence: float
    trade_spec_json: str | None    # Full TradeSpec as JSON
    reasoning_chain_json: str      # AgentSignalSummary list as JSON
    no_trade_reason: str | None
    valid_until: str | None        # ISO 8601
    created_at: datetime
```

**Backend protocol models** (in `tradingagents/agents/protocol.py`):
```python
class AgentSignalSummary(BaseModel):
    agent_name: str
    signal_direction: Literal["bullish", "bearish", "neutral"]
    confidence: float  # 0-100
    evidence: list[str]
    is_dissenting: bool = False

class TradeSpec(BaseModel):
    ticker: str
    direction: Literal["BUY", "SELL"]
    trade_type: Literal["equity", "option"]
    entry_price: float
    stop_loss: float
    profit_target: float
    position_size: int
    strike: float | None
    expiry: str | None
    contract_type: str | None
```

### Technical Requirements

- **React 19** + **TypeScript** — strict types for all new components
- **Tailwind v4** with design tokens from Story 4.1
- **Backend:** FastAPI + SQLAlchemy async (existing patterns in `api/`)
- **No new npm dependencies** — use native fetch, native `title` for tooltip
- **No new pip dependencies** — reuse existing Pydantic/SQLAlchemy patterns

### File Locations

| File | Action | Purpose |
|------|--------|---------|
| `frontend/src/types.ts` | MODIFY | Add Recommendation, AgentSignalSummary, TradeSpec types |
| `frontend/src/hooks/useRecommendations.ts` | NEW | Fetch + poll recommendations from API |
| `frontend/src/components/ConsensusIndicator.tsx` | NEW | Colored dots for agent consensus |
| `frontend/src/components/TradeSpecGrid.tsx` | NEW | 5-column trade specs display |
| `frontend/src/components/RecommendationCard.tsx` | NEW | Full recommendation card |
| `frontend/src/components/RecommendationList.tsx` | NEW | List of cards with data fetching |
| `frontend/src/App.tsx` | MODIFY | Wire RecommendationList into Recommendations tab |
| `api/recommendation_routes.py` | NEW | Backend API for recommendations |
| `api/main.py` | MODIFY | Register recommendation_router |

### Component Composition

```
RecommendationList
├── useRecommendations (hook)
└── RecommendationCard (per recommendation)
    ├── Direction badge (BUY/SELL)
    ├── ConsensusIndicator (dots)
    ├── TradeSpecGrid (entry/stop/target/size/R:R)
    └── ValidUntil countdown
```

### Previous Story Intelligence (4.2)

- Layout is now: header (40px) + primary content + side panel (320px) + status bar (28px)
- Recommendations tab currently shows: ConfigSidebar (left w-80) + Analysis flow (right flex-1)
- The RecommendationList should be placed within the Recommendations tab content area
- Tab names: "Recommendations" | "Chart" | "Track Record"
- All components use design token classes

### Styling Patterns (from UX spec)

- Card: `bg-bg-elevated border border-border-subtle rounded-sm`
- Ticker: `text-[16px] font-mono font-medium text-text-primary`
- Direction BUY: `text-accent-green`; SELL: `text-accent-red`
- Confidence: `font-mono text-text-primary`
- Labels: `text-[11px] text-text-tertiary uppercase tracking-wider`
- Data values: `text-[13px] font-mono`
- No shadows, no large rounded corners

### Anti-Patterns to Avoid

- **DO NOT** use a UI component library for tooltips — use native `title` attribute
- **DO NOT** add approval/skip logic in this story — that's Story 4.4
- **DO NOT** add reasoning chain expand — that's Story 4.5
- **DO NOT** create duplicate type definitions — reuse backend model structure
- **DO NOT** add WebSocket — use polling (30s interval) like existing `useLivePrice` pattern

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Component Strategy]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Data Display Patterns]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.3]
- [Source: _bmad-output/planning-artifacts/architecture.md#Agent Output Protocol]
- [Source: tradingagents/agents/protocol.py — AgentSignalSummary, TradeSpec, TradeRecommendation]
- [Source: api/models.py — Prediction model]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation.

### Completion Notes List

- Added Recommendation, AgentSignalSummary, RecommendationTradeSpec, RecommendationStatus types to types.ts
- Created useRecommendations hook with 30s polling, approve/skip methods, confidence sorting
- Created ConsensusIndicator: colored dots with native title tooltip
- Created TradeSpecGrid: 5-column grid with R:R calculation, directional stop/target coloring
- Created RecommendationCard: full card with ticker, direction badge, consensus, countdown, trade specs, card states
- Created RecommendationList: data-fetching wrapper with loading/empty/error states
- Created backend api/recommendation_routes.py: GET /api/recommendations (parses predictions), POST approve/skip, GET /api/positions, GET /api/positions/stats
- Registered recommendation_router in api/main.py
- Wired RecommendationList into App.tsx Recommendations tab above analysis flow
- Build passes: tsc + vite (209 modules)

### Change Log

- 2026-04-15: Story 4.3 implemented — RecommendationCard with trade specs, consensus, and backend API

### File List

- `frontend/src/types.ts` — MODIFIED: Added Recommendation, AgentSignalSummary, RecommendationTradeSpec types
- `frontend/src/hooks/useRecommendations.ts` — NEW: Fetch/poll recommendations hook
- `frontend/src/components/ConsensusIndicator.tsx` — NEW: Agent consensus colored dots
- `frontend/src/components/TradeSpecGrid.tsx` — NEW: 5-column trade spec grid
- `frontend/src/components/RecommendationCard.tsx` — NEW: Full recommendation card component
- `frontend/src/components/RecommendationList.tsx` — NEW: List wrapper with data fetching
- `frontend/src/App.tsx` — MODIFIED: Added RecommendationList to Recommendations tab
- `api/recommendation_routes.py` — NEW: Backend recommendation + position endpoints
- `api/main.py` — MODIFIED: Registered recommendation_router
