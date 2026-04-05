---
phase: 01
phase_name: trade-recommendation-sidebar-lock-in-flow
status: draft
created: 2026-04-05
design_system: tailwind-v4-custom
---

# UI-SPEC: Phase 01 — Trade Recommendation Sidebar & Lock-In Flow

## 1. Design System

| Property | Value | Source |
|----------|-------|--------|
| Tool | Tailwind CSS v4 (no shadcn) | `frontend/package.json` |
| Component model | Hand-rolled React TSX | Existing codebase |
| Theme | Dark-first; light mode via `dark:` variant class strategy | `frontend/src/index.css` |
| Icon library | Inline SVG only (no icon package installed) | Existing codebase |
| Registry | Not applicable — no shadcn | — |

---

## 2. Layout Contract

### Focal Points

- **Primary focal point:** `LivePriceHeader` price display — largest text (24px bold), top of sidebar, first element the eye lands on.
- **Secondary focal point:** `ExecuteButton` — full-width, high-contrast, anchored at sidebar bottom; draws action intent after price is registered.

### ChartScreen restructure (D-01)

Current layout: `flex-col` — top bar → chart → bottom `ChartActionPanel`

New layout: `flex-row` — left column (top bar + chart, flex-1) → right sidebar (fixed width, full height)

```
┌─────────────────────────────────────┬──────────────────┐
│  Top Bar (ticker + timeframes)      │                  │
├─────────────────────────────────────┤  Trade Sidebar   │
│                                     │  320px fixed     │
│  Chart (flex-1)                     │                  │
│                                     │                  │
└─────────────────────────────────────┴──────────────────┘
```

- Sidebar width: **320px** fixed (desktop ≥1280px). At viewport <1280px the sidebar collapses to a slide-over drawer triggered by a floating "Trade" button on the chart bottom-right corner.
- The sidebar is present only when `overlay !== null` (active mode). When overlay is null the chart takes full width — identical to current passive mode behaviour.
- `ChartActionPanel` component is deleted entirely; `TradeConfirmModal` logic absorbed inline into the sidebar.

### Sidebar internal layout

Sidebar is a single `flex-col` container with `overflow-y-auto` on the body section:

```
┌──────────────────────────────────┐
│  LIVE PRICE HEADER               │  56px, flex-shrink-0
├──────────────────────────────────┤
│  SIGNAL + AI METADATA            │  auto, flex-shrink-0
├──────────────────────────────────┤
│  ORDER FORM (editable fields)    │  flex-1, overflow-y-auto
│    Entry Price                   │
│    Target Price                  │
│    Stop-Loss                     │
│    Quantity                      │
│    Time-in-Force                 │
│    (Options: collapsed legs)     │
├──────────────────────────────────┤
│  OPEN POSITION PANEL             │  auto, flex-shrink-0
│  (only when position is open)   │
├──────────────────────────────────┤
│  EXECUTE / CLOSE BUTTON          │  56px, flex-shrink-0
└──────────────────────────────────┘
```

---

## 3. Spacing Scale

Multiples of 4px only. Standard set: {4, 8, 16, 24, 32, 48, 64}. No values outside this set.

| Token | px | Tailwind class |
|-------|----|----------------|
| 4 | 4px | `p-1` / `gap-1` |
| 8 | 8px | `p-2` / `gap-2` |
| 16 | 16px | `p-4` / `gap-4` |
| 24 | 24px | `p-6` / `gap-6` |
| 32 | 32px | `p-8` / `gap-8` |
| 48 | 48px | `p-12` |
| 64 | 64px | `p-16` |

**Sidebar-specific spacing:**
- Sidebar outer padding: 16px horizontal, 16px vertical (`px-4 py-4`)
- Between sidebar sections (dividers): 16px gap (`gap-4`)
- Form field rows: 8px vertical gap (`gap-2`)
- Label-to-input gap: 4px (`gap-1`)
- CTA button height: 48px (touch-target minimum — `py-3` with `text-base`)

Exceptions: none.

---

## 4. Typography

Single system font stack: inherit from OS (`font-sans`). No custom web font.

| Role | Size | Weight | Line-height | Tailwind classes |
|------|------|--------|-------------|-----------------|
| Live price (header) | 24px | 700 (bold) | 1.2 | `text-2xl font-bold` |
| Field value / body | 14px | 400 (regular) | 1.5 | `text-sm` |
| Section label / field label | 12px | 400 (regular) | 1.4 | `text-xs uppercase tracking-wide` |
| Supporting / meta | 12px | 400 (regular) | 1.4 | `text-xs` |

**Exactly 3 sizes (24px, 14px, 12px), 2 weights (400 regular + 700 bold).** Section labels and supporting/meta share 12px at weight 400 — differentiated by `uppercase tracking-wide` class on labels only, not by a separate size.

---

## 5. Color Contract

Theme is dark-first. All colors reference Tailwind gray-* and semantic colors consistent with existing screens.

### 60/30/10 Split

| Role | Color | Usage | Tailwind |
|------|-------|-------|----------|
| 60% Dominant surface | `gray-900` (#111827) | Sidebar background, chart background | `bg-gray-900` |
| 30% Secondary surface | `gray-800` (#1f2937) | Section cards, input backgrounds, header strip | `bg-gray-800` |
| 10% Accent | Blue-600 (#2563eb) | Active state, primary CTA (Execute button when idle) | `bg-blue-600` |

### Semantic Colors

| Semantic | Color | Reserved for |
|----------|-------|-------------|
| Positive / Buy | `green-600` (#16a34a) / `green-400` text | BUY signal badge, positive P&L, filled state indicator |
| Negative / Sell | `red-600` (#dc2626) / `red-400` text | SELL signal badge, negative P&L, rejected/error states |
| Warning | `amber-600` (#d97706) / `yellow-400` text | Submitted/pending state, paper trading disclaimer banner |
| Border / divider | `gray-700` (#374151) | All dividers, input borders, card borders |
| Muted text | `gray-400` (#9ca3af) | Labels, meta, placeholders |
| Body text | `gray-100` (#f3f4f6) | Primary readable text on dark surfaces |
| Destructive confirm | `red-600` bg + `white` text | "Close Position" confirmation only |

### Accent Reserved-For List

`blue-600` accent is reserved ONLY for:
1. "Execute Paper Trade" button idle state
2. Active timeframe selector button
3. Ticker drill-down links in trade history

Do NOT use blue-600 for: P&L values, signal badges, form inputs, section headers.

---

## 6. Component Inventory

### 6.1 TradeSidebar (new)

Replaces `ChartActionPanel`. Right-rail panel mounted inside `ChartScreen` when `overlay !== null`.

**Props:**
```ts
interface TradeSidebarProps {
  overlay: ChartOverlay;               // AI recommendation data
  tradeStatus: TradeStatus | null;     // Current order lifecycle state
  isSubmitting: boolean;
  onExecute: (params: BracketOrderParams) => Promise<void>;
  onClosePosition: () => void;
  livePrice: LivePriceData | null;     // From new useLivePrice hook
  onViewAnalysis: () => void;
}
```

**Sections:**
- `LivePriceHeader` — current price (24px bold), day change as `+X.XX (Y.YY%)` colored green/red
- `SignalMetadata` — SignalBadge (existing pattern), analysis date, strategy name, confidence chip
- `OrderForm` — 5 editable fields (see 6.2)
- `OptionsLegsPanel` — collapsed accordion, only when `overlay.options_legs` has content
- `OpenPositionPanel` — live P&L display, only when `tradeStatus?.status === 'filled'`
- `ExecuteButton` — single CTA area, changes render based on order lifecycle state

### 6.2 OrderForm fields

Each field: label row (12px regular uppercase tracking-wide) + input row (14px, `bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-gray-100`).

| Field | Type | AI pre-fill source | User editable |
|-------|------|--------------------|--------------|
| Entry Price | number input | `overlay.entry_price` | Yes (D-02) |
| Target Price | number input | `overlay.take_profit` | Yes (D-02) |
| Stop-Loss | number input | `overlay.stop_loss` | Yes (D-02) |
| Quantity | number input | 100 (default) | Yes (D-02) |
| Time-in-Force | select (GTC / DAY) | AI-determined (D-11) | Yes (D-02) |

Input focus ring: `focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent`

### 6.3 OptionsLegsPanel

Collapsed by default. Toggle shows full options legs text in a monospace block.

- Collapsed state: strategy type label + chevron-down icon (inline SVG 16x16)
- Expanded state: `font-mono text-xs text-gray-300 whitespace-pre-wrap bg-gray-900 rounded p-3`
- Expand/collapse uses local `useState` — no animation required

### 6.4 OpenPositionPanel (D-05)

Only rendered when `tradeStatus?.status === 'filled'`.

Layout: two rows
- Row 1: "Open Position" label (12px gray-400 uppercase tracking-wide) + fill price (14px gray-100)
- Row 2: "Live P&L" label (12px gray-400 uppercase tracking-wide) + P&L value (14px, green-400 if positive, red-400 if negative, formatted as `+$X.XX (+Y.YY%)`)

P&L calculation: `(livePrice.price - tradeStatus.fill_price) * quantity` for BUY; inverse for SELL.
Display both dollar amount and percentage. Show both (D-06, Claude's Discretion resolved: show both).

### 6.5 ExecuteButton / lifecycle states

Single slot at sidebar bottom. State machine:

| `tradeStatus.status` | Render |
|----------------------|--------|
| `idle` (no order yet) | Blue-600 "Execute Paper Trade" button, full width, 48px tall |
| `submitted` | Amber-600 strip: spinner + "Order Submitted..." — disabled, non-clickable |
| `filled` | Green-700 strip: "Filled @ $XX.XX" (fill price). Then shows separate red "Close Position" button below |
| `rejected` | Red-700 "Rejected: {reason}" + gray "Retry Order" button |
| `error` | Red-700 "Error" + gray "Retry Order" button |

"Close Position" button (D-06): `bg-red-700 hover:bg-red-600 text-white text-sm font-medium`, full width, 44px. Requires inline confirmation — clicking turns button into a `flex` row: `["Cancel Close" (gray-700 flex-1)] ["Confirm Close" (red-600 flex-1)]`. No modal. Timeout: none (user must explicitly cancel or confirm).

### 6.6 SignalBadge (existing — reuse)

Pattern already established in `ChartActionPanel.tsx`. Copy to sidebar as-is:
- BUY: `bg-green-600 text-white px-2 py-0.5 rounded text-xs font-bold`
- SELL: `bg-red-600 text-white px-2 py-0.5 rounded text-xs font-bold`
- HOLD: `bg-gray-500 text-white px-2 py-0.5 rounded text-xs font-bold`

### 6.7 LivePriceHeader (new, D-03)

Polling interval: 5 seconds via `setInterval` in `useLivePrice` hook (REST polling, not WebSocket — deferred per CONTEXT.md deferred section).

Layout:
```
$XXX.XX          +X.XX (+Y.YY%)
                 [or -X.XX (-Y.YY%)]
```
- Price: `text-2xl font-bold text-gray-100`
- Change: `text-sm` colored `text-green-400` (positive) or `text-red-400` (negative)
- Background: `bg-gray-800 rounded-lg px-4 py-3 mb-4`

### 6.8 Dashboard table updates (D-15, D-16, D-17, D-19)

In `TrackRecordScreen`, trade history table gains a new "Close Reason" column after "Outcome":

| Close Reason values | Display |
|---------------------|---------|
| `"Target Hit"` | `bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400` badge |
| `"Stop-Loss"` | `bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400` badge |
| `"Manual Close"` | `bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300` badge |
| `"Expired"` | `bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400` badge |
| `null` (open/pending) | `--` in muted gray-400 |

Summary stat cards added (use existing `StatCard` component pattern):
- "Risk-Reward" card: value formatted as `X.XX:1`, no color class (neutral)
- "Avg R-Multiple" card: value formatted as `+X.XX` (green-600/red-600 based on sign)

---

## 7. Interaction Contracts

### 7.1 Form field editing

- All OrderForm fields start pre-filled from AI data
- User can edit any field — no confirmation needed for edits
- Fields retain user edits until "Execute" is clicked (no auto-reset on price updates)
- After a fill (`status === 'filled'`), all form fields become `disabled` + `opacity-50 cursor-not-allowed`
- After a fill, only "Close Position" is interactive

### 7.2 Execute flow

1. User reviews/edits fields
2. User clicks "Execute Paper Trade"
3. Button immediately changes to amber "Order Submitted..." (no intermediate modal — modal absorbed into sidebar, D-02)
4. On fill: button area becomes green "Filled @ $XX.XX" + red "Close Position" button appears
5. On rejection: red rejection reason + gray "Retry Order" button

No separate confirmation modal. The editable sidebar IS the confirmation surface. The previous `TradeConfirmModal` component is deleted.

### 7.3 Close Position inline confirmation

1. User clicks "Close Position" (red-700 button)
2. Button row splits into: "Cancel Close" (gray-700) | "Confirm Close" (red-600) — no animation, instant DOM swap
3. On "Confirm Close": submits market sell order via `onClosePosition`, shows spinner in button slot
4. On "Cancel Close": reverts to single "Close Position" button

### 7.4 Options legs collapse

- Default: collapsed (shows strategy label + chevron-down)
- Click: expands to show full legs text
- Second click: collapses
- State is local — resets on ticker change

### 7.5 Sidebar vs passive mode

- `overlay === null`: sidebar not rendered, chart takes 100% width — identical to current passive mode
- `overlay !== null` at viewport ≥1280px: chart + 320px sidebar side-by-side
- `overlay !== null` at viewport <1280px: chart full width + floating "Trade" button (bottom-right, `fixed`-positioned, blue-600, 44x44px touch target). Clicking opens sidebar as a slide-over drawer from the right with a semi-transparent `bg-black/60` backdrop.

---

## 8. Copywriting Contract

### Primary CTA

| State | Label |
|-------|-------|
| Idle | "Execute Paper Trade" |
| Submitted | "Order Submitted..." |
| Filled | "Filled @ $XX.XX" |
| Rejected | "Rejected: {reason}" |
| Error | "Error" |

### Secondary CTA

| Action | Label |
|--------|-------|
| Close open position | "Close Position" |
| Confirm close | "Confirm Close" |
| Cancel close | "Cancel Close" |
| Retry after rejection | "Retry Order" |

### Empty / Null states

| Scenario | Copy |
|----------|------|
| No overlay (passive mode, no ticker) | "Enter a ticker symbol to view chart" (existing) |
| Overlay loaded but live price unavailable | "Price unavailable" in gray-400, 12px |
| No open position (filled section hidden) | Section not rendered — no copy needed |
| Close reason null in dashboard table | "--" (existing pattern) |

### Error states

| Error | Copy |
|-------|------|
| Order rejected by Alpaca | "Rejected: {rejection_reason from API}" |
| Network error on execute | "Error" + "Retry Order" button (no detail — consistent with existing error pattern) |
| Live price fetch failure | silently show "--" for price; do not display an error banner |
| Bracket order partial fill | "Filled @ $XX.XX" (treat as normal fill; stop/target legs tracked by Alpaca) |

### Destructive action confirmation

| Action | Approach | Copy |
|--------|----------|------|
| Close Position | Inline two-button confirmation (no modal) | "Confirm Close" / "Cancel Close" |
| Delete legacy trades (D-18) | Backend migration script only — no UI confirmation surface needed in this phase |

### Paper trading disclaimer

Persistent yellow banner at top of `TrackRecordScreen` (existing, unchanged):
"Paper Trading Results -- Not Real Money"

No equivalent banner needed in sidebar — sidebar header shows "Paper" label in 12px `text-gray-400` next to the ticker name.

---

## 9. Accessibility

- All interactive elements: minimum 44x44px touch target
- Form inputs: associated `<label>` via `htmlFor` / `id`
- ExecuteButton disabled states: `aria-disabled="true"` + `disabled` attribute + `cursor-not-allowed`
- Close Position confirmation: `aria-label="Confirm close position"` on confirm button
- Sidebar slide-over (mobile): `role="dialog"` + `aria-modal="true"` + focus trap while open
- SignalBadge: `aria-label="Signal: BUY"` (or SELL/HOLD)
- Live price region: `aria-live="polite"` on the price element (screen reader announces updates)
- Color not the only indicator: P&L values always show +/- prefix in addition to green/red color

---

## 10. Animation & Motion

- No layout animations for sidebar entry on desktop (instant render when overlay loads)
- Sidebar slide-over on mobile: CSS `transition: transform 300ms ease-out` (`translate-x-full` → `translate-x-0`)
- Spinner: existing `animate-spin` pattern from `ChartActionPanel.tsx`
- Button state transitions: `transition-colors` only (existing pattern)
- No skeleton loading in sidebar — show pre-filled AI values instantly; live price shows "--" until first poll resolves

---

## 11. Pre-Population Audit

| Decision | Spec section | Source |
|----------|-------------|--------|
| D-01 Sidebar replaces ChartActionPanel | §2 Layout | CONTEXT.md |
| D-02 All fields editable | §6.2, §7.1 | CONTEXT.md |
| D-03 Live price streaming | §6.7, §7 | CONTEXT.md |
| D-04 Options as collapsed legs | §6.3 | CONTEXT.md |
| D-05 Live P&L in sidebar | §6.4 | CONTEXT.md |
| D-06 Close Position button | §6.5, §7.3 | CONTEXT.md |
| D-07 No trade history in sidebar | §6.1 (absent section) | CONTEXT.md |
| D-15 Close reason field | §6.8 | CONTEXT.md |
| D-16 Risk-reward ratio | §6.8 | CONTEXT.md |
| D-17 Avg R-multiple | §6.8 | CONTEXT.md |
| D-19 Close reason column | §6.8 | CONTEXT.md |
| Sidebar width 320px | §2 | Claude's Discretion (CONTEXT.md) |
| Polling 5s interval | §6.7 | Claude's Discretion (CONTEXT.md) |
| P&L: dollar + percentage both | §6.4 | Claude's Discretion (CONTEXT.md) |
| No modal for execute confirmation | §7.2 | Claude's Discretion — sidebar IS the confirmation surface |
| Inline two-button close confirmation | §7.3 | Claude's Discretion (CONTEXT.md) |
| Dark-first Tailwind v4 | §3, §5 | Existing codebase (`index.css`, existing components) |
| gray-900/800/700 surfaces | §5 | Existing codebase (all components) |
| blue-600 accent | §5 | Existing codebase (timeframe buttons, TrackRecordScreen) |
| green-600/red-600 semantic | §5 | Existing codebase (SignalBadge, direction badges) |

---

## 12. Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending

---

*Phase: 01-trade-recommendation-sidebar-lock-in-flow*
*UI-SPEC created: 2026-04-05*
*Status: draft — awaiting gsd-ui-checker validation*
