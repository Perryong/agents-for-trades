# Story 4.1: Design Token System and Global Restyle

Status: review

## Story

As a user,
I want the app restyled with a professional dark-mode terminal aesthetic,
so that the interface feels clean, dense, and purposeful instead of bubbly.

## Acceptance Criteria

1. **Given** the frontend uses default Tailwind styling **When** design tokens are implemented **Then** CSS custom properties are defined for all color tokens:
   - `--bg-base`: #131313
   - `--bg-primary`: #1c1c1c
   - `--bg-secondary`: #232323
   - `--bg-elevated`: #2a2a2a
   - `--bg-hover`: #333333
   - `--border-subtle`: #2e2e2e
   - `--border-default`: #3a3a3a
   - `--text-primary`: #e0e0e0
   - `--text-secondary`: #888888
   - `--text-tertiary`: #555555
   - `--accent-green`: #3ecf8e
   - `--accent-red`: #f56565
   - `--accent-amber`: #eab308
   - `--accent-blue`: #3b82f6

2. **And** Inter font is loaded for sans-serif, JetBrains Mono for monospace

3. **And** spacing scale uses 4px base (4, 8, 12, 16, 24, 32px)

4. **And** border-radius is 2px default, 4px for buttons/inputs — no large rounded corners

5. **And** all existing components are restyled to use the new tokens

6. **And** the app renders with dark mode as default and only theme — remove the light/dark toggle entirely

## Tasks / Subtasks

- [x] Task 1: Define CSS custom properties in `index.css` (AC: #1)
  - [x] Add `:root` block with all color tokens from the UX spec
  - [x] Add `@theme` block to register tokens as Tailwind v4 theme values
  - [x] Remove the dark variant rule (`@variant dark`) — dark is now the only theme
- [x] Task 2: Load Inter and JetBrains Mono fonts (AC: #2)
  - [x] Add Google Fonts imports to `index.html` for Inter (400, 500, 600) and JetBrains Mono (400, 500)
  - [x] Set `font-family` on `:root` to `'Inter', system-ui, -apple-system, sans-serif`
  - [x] Register `--font-mono` as `'JetBrains Mono', 'Fira Code', ui-monospace, monospace`
- [x] Task 3: Define spacing and border-radius tokens (AC: #3, #4)
  - [x] Register spacing scale in `@theme`: `--space-1: 4px` through `--space-8: 32px`
  - [x] Set `--radius-sm: 2px` and `--radius-md: 4px` in theme
  - [x] Add base styles setting `border-radius: 2px` on common elements
- [x] Task 4: Remove dark mode toggle and light theme (AC: #6)
  - [x] Remove `dark` state and toggle button from `App.tsx`
  - [x] Remove `getInitialDark()` function and `useEffect` that manages `.dark` class
  - [x] Remove `localStorage` theme persistence logic
  - [x] Set `<html class="dark">` permanently in `index.html` (or apply bg-base directly)
- [x] Task 5: Restyle App.tsx shell and layout (AC: #5)
  - [x] Replace `bg-gray-50 dark:bg-gray-900` with `bg-bg-base`
  - [x] Replace sidebar `bg-white dark:bg-gray-800` with `bg-bg-secondary`
  - [x] Replace all `dark:` prefixed classes with token-based equivalents
  - [x] Replace `border-gray-200 dark:border-gray-700` with `border-border-subtle`
  - [x] Replace text colors: `text-gray-900 dark:text-gray-100` → `text-text-primary`
- [x] Task 6: Restyle all existing components with tokens (AC: #5)
  - [x] GlobalStatusBar.tsx — replace blue/gray classes with token vars
  - [x] ConfigSidebar.tsx — form inputs, labels, buttons to use tokens
  - [x] ProgressStepper.tsx — node states to use accent colors
  - [x] ReportTabs.tsx — tab active/inactive to use tokens
  - [x] ReportPane.tsx — content area backgrounds and text
  - [x] ChartScreen.tsx / ChartContainer.tsx — backgrounds, borders, removed `dark` prop
  - [x] TrackRecordScreen.tsx — all table/card styles, removed `dark` prop
  - [x] WatchlistPanel.tsx / PickCard.tsx — screener styles
  - [x] ScoringCard.tsx / CalibrationChart.tsx — scoring styles
  - [x] TradeSidebar.tsx — trade panel styles
  - [x] TickerAutocomplete.tsx — dropdown and input styles
- [x] Task 7: Verify all components render correctly (AC: #1-6)
  - [x] Run `npm run build` (tsc + vite) with zero errors
  - [x] Verified: zero `dark:` prefixed classes remain (grep confirmed)
  - [x] Verified: zero `bg-gray-`/`text-gray-`/`border-gray-` classes remain
  - [x] Verified: zero raw `bg-blue-`/`text-blue-`/etc. classes remain
  - [x] Verified: Inter and JetBrains Mono fonts loaded via Google Fonts CDN

## Dev Notes

### Architecture & Approach

**Tailwind CSS v4 theming approach:** Tailwind v4 uses CSS-first configuration via `@theme` blocks in CSS files. Design tokens are defined as CSS custom properties and registered as Tailwind theme values in `index.css`. This replaces the old `tailwind.config.js` approach.

**Key pattern — Tailwind v4 `@theme` syntax:**
```css
@import "tailwindcss";

@theme {
  --color-bg-base: #131313;
  --color-bg-primary: #1c1c1c;
  /* ... generates utilities like bg-bg-base, text-bg-primary, etc. */
}
```

When tokens are registered under `--color-*`, Tailwind v4 auto-generates utility classes (e.g., `bg-bg-base`, `text-accent-green`). This is the preferred approach over `bg-[var(--bg-base)]` for frequently used tokens.

**Dark mode removal:** The current app uses class-based dark mode (`@variant dark (&:where(.dark, .dark *))`) with a toggle. Since dark is the only theme, remove the variant rule entirely and all `dark:` prefixed classes. Apply token colors directly.

### Technical Requirements

- **Tailwind CSS v4.2.2** — uses `@theme` blocks, NOT `tailwind.config.js`
- **Vite + @tailwindcss/vite** plugin — already configured in `vite.config.ts`
- **React 19** — no changes to React patterns needed
- **No new dependencies** for fonts — use Google Fonts CDN `<link>` tags in `index.html`

### File Locations

| File | Action | Purpose |
|------|--------|---------|
| `frontend/src/index.css` | MODIFY | Add CSS custom properties + `@theme` block with all tokens |
| `frontend/index.html` | MODIFY | Add Google Fonts links, set permanent dark class on html |
| `frontend/src/App.tsx` | MODIFY | Remove dark toggle, replace all gray/dark: classes with tokens |
| `frontend/src/components/*.tsx` | MODIFY | Replace all Tailwind gray/dark: utilities with token classes |
| `frontend/src/main.tsx` | NO CHANGE | Entry point unchanged |

### Styling Migration Pattern

For every component, the migration follows this pattern:

**Before (current):**
```tsx
className="bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 border-gray-200 dark:border-gray-700"
```

**After (tokens):**
```tsx
className="bg-bg-primary text-text-primary border-border-subtle"
```

Where `bg-bg-primary`, `text-text-primary`, `border-border-subtle` are auto-generated Tailwind v4 utilities from the `@theme` block.

### Color Mapping Reference

| Current Tailwind Class | Token Replacement |
|----------------------|-------------------|
| `bg-gray-50`, `bg-white` (light) / `bg-gray-900` (dark) | `bg-bg-base` |
| `bg-white` / `bg-gray-800` (panels) | `bg-bg-primary` |
| `bg-gray-100` / `bg-gray-700` (hover) | `bg-bg-hover` |
| `border-gray-200` / `border-gray-700` | `border-border-subtle` |
| `border-gray-300` / `border-gray-600` | `border-border-default` |
| `text-gray-900` / `text-gray-100` | `text-text-primary` |
| `text-gray-500` / `text-gray-400` | `text-text-secondary` |
| `text-gray-400` / `text-gray-500` (dimmer) | `text-text-tertiary` |
| `text-blue-600` / `text-blue-400` | `text-accent-blue` |
| `text-green-700` / `text-green-400` | `text-accent-green` |
| `text-red-700` / `text-red-400` | `text-accent-red` |
| `bg-blue-600` (buttons) | `bg-accent-blue` |
| `bg-green-50/500` / `bg-green-900/30` | `bg-accent-green` with opacity |
| `bg-red-50/500` / `bg-red-900/30` | `bg-accent-red` with opacity |

### Anti-Patterns to Avoid

- **DO NOT** use `tailwind.config.js` — Tailwind v4 uses CSS `@theme` blocks
- **DO NOT** keep any `dark:` prefixed classes — dark is the only theme
- **DO NOT** use `bg-[var(--bg-base)]` for commonly used tokens — register in `@theme` so Tailwind generates proper utility classes
- **DO NOT** add `rounded-lg`, `rounded-xl`, `rounded-2xl` — max border-radius is 4px (`rounded-sm` equivalent)
- **DO NOT** add box shadows (`shadow-*`) — flat design, 1px borders only
- **DO NOT** use font sizes > 18px — terminal aesthetic is dense and compact
- **DO NOT** leave any light theme colors (white backgrounds, light gray borders)

### UX Spec Typography Reference

| Level | Size | Weight | Font | Usage |
|-------|------|--------|------|-------|
| Page title | 18px | 600 | Sans | Screen headers only |
| Section header | 14px | 600 | Sans | Panel titles, section labels |
| Body | 13px | 400 | Sans | Descriptions, reasoning text |
| Label | 11px | 500 | Sans | Field labels, timestamps |
| Data large | 16px | 500 | Mono | Ticker, confidence |
| Data default | 13px | 400 | Mono | Prices, percentages |
| Data small | 11px | 400 | Mono | Secondary data, table cells |

[Source: _bmad-output/planning-artifacts/ux-design-specification.md#Typography System]

### Previous Story Context

This is the first story in Epic 4. No previous story learnings. However, the codebase has established patterns from Epics 1-3:
- Existing components use Tailwind utility classes extensively
- All components are in `frontend/src/components/` as PascalCase `.tsx` files
- No CSS modules or styled-components — pure Tailwind utilities
- Existing dark mode uses class-based toggle with `dark:` variant prefixes

### Git Context

Recent commits are backend-focused (risk manager, strategy selection, options agents). No recent frontend changes. The frontend was last significantly touched during initial setup and phase 13-16 implementations.

### Project Structure Notes

- Frontend root: `frontend/`
- Components: `frontend/src/components/` — 15 existing `.tsx` files
- Hooks: `frontend/src/hooks/` — 10 existing `.ts` files
- Types: `frontend/src/types.ts`
- Entry CSS: `frontend/src/index.css`
- HTML entry: `frontend/index.html`
- Build: Vite + `@tailwindcss/vite` plugin

### References

- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Color System]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Typography System]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Spacing & Layout Foundation]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Design System Foundation]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Frontend Architecture]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — clean implementation with no blocking issues.

### Completion Notes List

- Defined all 14 color tokens + 2 border tokens + 4 text tokens in Tailwind v4 `@theme` block in `index.css`
- Loaded Inter (400/500/600) and JetBrains Mono (400/500) via Google Fonts CDN
- Defined spacing scale (4-32px) and border-radius tokens (2px/4px)
- Removed dark mode toggle entirely — dark is permanent. Removed `getInitialDark()`, `dark` state, localStorage theme logic, and `useEffect` for `.dark` class
- Removed `dark` prop from `ChartScreen`, `ChartContainer`, and `TrackRecordScreen` — always-dark chart colors hardcoded
- Restyled all 15 components to use token-based utility classes
- Zero `dark:` prefixed classes remain across entire `src/` directory
- Zero raw Tailwind gray/blue/green/red color classes remain
- Build passes (tsc + vite) with zero errors

### Change Log

- 2026-04-15: Story 4.1 implemented — design token system and global restyle

### File List

- `frontend/src/index.css` — MODIFIED: Added @theme block with all design tokens, base styles, removed dark variant
- `frontend/index.html` — MODIFIED: Added Google Fonts links, set permanent dark class, updated title
- `frontend/src/App.tsx` — MODIFIED: Removed dark toggle, restyled with tokens, refactored nav tabs
- `frontend/src/components/GlobalStatusBar.tsx` — MODIFIED: Token restyle
- `frontend/src/components/ConfigSidebar.tsx` — MODIFIED: Token restyle
- `frontend/src/components/ProgressStepper.tsx` — MODIFIED: Token restyle
- `frontend/src/components/ReportTabs.tsx` — MODIFIED: Token restyle
- `frontend/src/components/ReportPane.tsx` — MODIFIED: Token restyle (including markdown components)
- `frontend/src/components/ChartScreen.tsx` — MODIFIED: Token restyle, removed dark prop
- `frontend/src/components/ChartContainer.tsx` — MODIFIED: Token restyle, removed dark prop, always-dark chart colors
- `frontend/src/components/ChartTickerPicker.tsx` — MODIFIED: Token restyle
- `frontend/src/components/TrackRecordScreen.tsx` — MODIFIED: Token restyle, removed dark prop, always-dark chart colors
- `frontend/src/components/WatchlistPanel.tsx` — MODIFIED: Token restyle
- `frontend/src/components/PickCard.tsx` — MODIFIED: Token restyle
- `frontend/src/components/ScoringCard.tsx` — MODIFIED: Token restyle
- `frontend/src/components/CalibrationChart.tsx` — MODIFIED: Token restyle
- `frontend/src/components/TradeSidebar.tsx` — MODIFIED: Token restyle
- `frontend/src/components/TickerAutocomplete.tsx` — MODIFIED: Token restyle
