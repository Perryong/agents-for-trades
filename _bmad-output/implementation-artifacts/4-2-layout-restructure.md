# Story 4.2: Layout Restructure — Header, Primary, Side Panel, Status Bar

Status: review

## Story

As a user,
I want the app layout restructured into a professional terminal layout,
so that I have persistent context (positions, stats) alongside the primary content area.

## Acceptance Criteria

1. **Given** the current layout structure **When** the layout is restructured **Then** the header bar is 40px with compact tab navigation (Recommendations | Chart | Track Record)

2. **And** the primary content area is flexible width, changes content based on active tab

3. **And** the side panel is fixed at 320px, always visible, showing placeholder sections for active positions and quick stats (actual data wired in Stories 4.6)

4. **And** the status bar is 28px at the bottom showing placeholder text for session summary and system health (actual data wired in Story 4.7)

5. **And** panels are separated by 1px border-subtle lines, no drop shadows

6. **And** minimum viewport is 1280px width

7. **And** tab switching is instant (no animation) and accessible via keyboard shortcuts `1`, `2`, `3`

## Tasks / Subtasks

- [x] Task 1: Restructure App.tsx layout into header + primary + side panel + status bar (AC: #1-5)
  - [x] Replace the current left sidebar (w-80 ConfigSidebar) with a top header bar (h-[40px])
  - [x] Move tab navigation into the 40px header bar — tabs: "Recommendations", "Chart", "Track Record"
  - [x] Rename `mainSection` values: 'analysis' → 'recommendations', remove 'screener' (merged into recommendations), keep 'chart' and 'trackrecord'
  - [x] Create a flex layout: header (40px fixed) → middle (flex-1, contains primary + side panel) → status bar (28px fixed)
  - [x] Primary content area: flex-1, changes based on active tab
  - [x] Side panel: w-[320px] fixed, always visible, right side, border-l border-border-subtle
  - [x] Status bar: h-[28px] fixed at bottom, border-t border-border-subtle, bg-bg-primary
  - [x] Ensure all panel separators are 1px border-border-subtle, no drop shadows
- [x] Task 2: Move ConfigSidebar into the Recommendations tab content area (AC: #2)
  - [x] ConfigSidebar is no longer a permanent left sidebar — moved into recommendations tab
  - [x] Layout the recommendations tab as: ConfigSidebar (left, w-80) + analysis results (right, flex-1)
  - [x] Preserve all existing analysis flow: ProgressStepper, ReportTabs, ReportPane, Signal Banner
- [x] Task 3: Create placeholder SidePanel component (AC: #3)
  - [x] Create `frontend/src/components/SidePanel.tsx`
  - [x] Render two sections: "Positions" (empty state: "No open positions") and "Quick Stats" (placeholder 2x2 grid with dashes)
  - [x] Use design tokens: bg-bg-secondary, text-text-primary/secondary, border-border-subtle
  - [x] Fixed width 320px, full height of middle area, overflow-y-auto
- [x] Task 4: Create placeholder StatusBar component (AC: #4)
  - [x] Create `frontend/src/components/StatusBar.tsx`
  - [x] Render 28px bar: left = session summary placeholder, right = green health dot + "Online"
  - [x] 11px text, text-text-tertiary color
  - [x] Keep existing GlobalStatusBar for running analysis indicator
- [x] Task 5: Add keyboard shortcuts for tab switching (AC: #7)
  - [x] Add a `useEffect` with `keydown` listener on `document`
  - [x] `1` → Recommendations, `2` → Chart, `3` → Track Record
  - [x] Only fire when no input/textarea/select is focused
  - [x] No animation on tab switch — instant content swap
- [x] Task 6: Set minimum viewport width (AC: #6)
  - [x] Add `min-w-[1280px]` to the root layout div
- [x] Task 7: Build verification (AC: #1-7)
  - [x] Run `tsc --noEmit` with zero errors
  - [x] Run `vite build` with zero errors — 204 modules, 166ms
  - [x] Layout: header (40px) + middle (primary + side panel 320px) + status bar (28px)
  - [x] Keyboard shortcuts 1/2/3 implemented in useEffect
  - [x] Side panel always visible via SidePanel component in flex layout

## Dev Notes

### Architecture & Approach

**Layout restructure from sidebar-first to header-first:**

Current layout (Story 4.1 state):
```
┌──────────┬─────────────────────────────────────┐
│ Config   │ Tab Bar                              │
│ Sidebar  ├─────────────────────────────────────┤
│ (w-80)   │ Content (analysis/screener/chart/    │
│          │          trackrecord)                │
└──────────┴─────────────────────────────────────┘
```

Target layout (Story 4.2):
```
┌─────────────────────────────────────────────────┐
│ Header (40px) — TradingAgents + Tab Nav          │
├──────────────────────────────┬──────────────────┤
│ Primary Content (flex-1)      │ Side Panel       │
│                               │ (320px)          │
│ Tab-dependent:                │                  │
│ - Recommendations (Config +  │ - Positions       │
│   Analysis flow)              │ - Quick Stats    │
│ - Chart                       │                  │
│ - Track Record                │                  │
├──────────────────────────────┴──────────────────┤
│ Status Bar (28px) — session summary, health      │
└─────────────────────────────────────────────────┘
```

**Key decisions:**
- The ConfigSidebar moves INTO the Recommendations tab content (not removed)
- The side panel is a new permanent right panel (placeholder now, data in 4.6)
- The status bar is a new permanent bottom bar (placeholder now, data in 4.7)
- The existing GlobalStatusBar (analysis progress) stays as an overlay/banner above content when analysis is running
- Tab names change: "Analysis" → "Recommendations", "Screener" removed (to be merged later)

### Technical Requirements

- **React 19** — no new libraries needed
- **Tailwind CSS v4** with design tokens from Story 4.1
- New components: `SidePanel.tsx`, `StatusBar.tsx`
- Modified: `App.tsx` (major restructure)

### File Locations

| File | Action | Purpose |
|------|--------|---------|
| `frontend/src/App.tsx` | MAJOR MODIFY | Complete layout restructure |
| `frontend/src/components/SidePanel.tsx` | NEW | Placeholder right panel |
| `frontend/src/components/StatusBar.tsx` | NEW | Compact bottom status bar |
| `frontend/src/components/GlobalStatusBar.tsx` | NO CHANGE | Kept for running analysis indicator |

### Previous Story Intelligence (4.1)

**Key learnings from Story 4.1:**
- All components now use design token classes (bg-bg-base, text-text-primary, etc.)
- `dark` prop removed from ChartScreen, ChartContainer, TrackRecordScreen
- Dark mode toggle removed — permanent dark theme via tokens
- Tailwind v4 `@theme` block in `index.css` defines all tokens
- Nav tabs in App.tsx already refactored to use `.map()` pattern

**Files that were modified and their current state:**
- `App.tsx` — already uses token classes, tabs use `.map()` loop, no dark toggle
- All components use `bg-bg-*`, `text-text-*`, `border-border-*` token classes

### Keyboard Shortcut Pattern

```tsx
useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    const tag = (document.activeElement?.tagName ?? '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
    
    switch (e.key) {
      case '1': setMainSection('recommendations'); break;
      case '2': setMainSection('chart'); break;
      case '3': setMainSection('trackrecord'); break;
    }
  };
  document.addEventListener('keydown', handleKeyDown);
  return () => document.removeEventListener('keydown', handleKeyDown);
}, []);
```

### UX Spec Layout Reference

```
┌─────────────────────────────────────────────────────┐
│ Header Bar (40px) — status, last run, nav tabs      │
├──────────────────────────────┬──────────────────────┤
│                              │                      │
│  Primary Content Area        │  Side Panel (320px)  │
│  (flexible width)            │                      │
│                              │  - Active positions  │
│  - Recommendations           │  - Quick stats       │
│  - Chart view                │  - Config access     │
│  - Track record              │                      │
│                              │                      │
├──────────────────────────────┴──────────────────────┤
│ Status Bar (28px) — session summary, system health  │
└─────────────────────────────────────────────────────┘
```

- Header: 40px, compact, tab navigation
- Side panel: Fixed 320px, always visible
- Primary area: Flexible width
- Status bar: 28px bottom
- Panels separated by 1px border-subtle lines, not gaps or shadows
- No drop shadows

[Source: _bmad-output/planning-artifacts/ux-design-specification.md#Spacing & Layout Foundation]

### Anti-Patterns to Avoid

- **DO NOT** add drop shadows — flat design, 1px borders only
- **DO NOT** animate tab switches — instant content swap
- **DO NOT** make the side panel collapsible — always visible per spec
- **DO NOT** add new data fetching in this story — SidePanel and StatusBar are placeholders
- **DO NOT** change any component internals — only move them around in the layout
- **DO NOT** remove ConfigSidebar — move it into the Recommendations tab content area

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Spacing & Layout Foundation]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Navigation Patterns]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.2]
- [Source: _bmad-output/planning-artifacts/architecture.md#Frontend Architecture]
- [Source: _bmad-output/implementation-artifacts/4-1-design-token-system-and-global-restyle.md#Completion Notes]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation.

### Completion Notes List

- Complete layout restructure from sidebar-first to header-first terminal layout
- Header: 40px with "TradingAgents" brand + 3-tab navigation (Recommendations | Chart | Track Record)
- Renamed mainSection from 'analysis'→'recommendations', removed 'screener' section
- ConfigSidebar moved from permanent left sidebar into Recommendations tab content
- Created SidePanel.tsx: 320px fixed right panel with Positions + Quick Stats placeholders
- Created StatusBar.tsx: 28px compact bottom bar with session summary placeholder + green health dot
- Added keyboard shortcuts (1/2/3) for tab switching with input focus guard
- Set min-w-[1280px] on root layout
- All panel separators use 1px border-border-subtle, no shadows
- Build passes clean: tsc + vite (204 modules, 166ms)

### Change Log

- 2026-04-15: Story 4.2 implemented — layout restructure with header, side panel, status bar

### File List

- `frontend/src/App.tsx` — MODIFIED: Complete layout restructure (header + primary + side panel + status bar)
- `frontend/src/components/SidePanel.tsx` — NEW: 320px fixed right panel with placeholder positions + stats
- `frontend/src/components/StatusBar.tsx` — NEW: 28px compact bottom status bar
