# Dark Mode Enhancement

**Requested:** 2026-04-01 during Phase 7 visual verification
**Scope:** Add dark/light mode toggle to the frontend

## Implementation Notes
- Tailwind v4 supports dark mode via `@variant dark` or `prefers-color-scheme`
- Add a toggle button in the header/sidebar
- Apply `dark:` variant classes to all components
- Persist preference in localStorage

## Files to modify
- `frontend/src/App.tsx` — dark mode toggle + className on root div
- `frontend/src/components/ConfigSidebar.tsx` — dark variant classes
- `frontend/src/components/ProgressStepper.tsx` — dark variant classes
- `frontend/src/components/ReportTabs.tsx` — dark variant classes
- `frontend/src/components/ReportPane.tsx` — dark variant classes
