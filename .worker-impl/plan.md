# Plan: Visual Status Indicators for erkdesk Plan List

**Part of Objective #6423, Step 2.4**

## Goal

Replace emoji-encoded display strings in the PlanList table with proper GUI elements: colored status dots paired with text. Use raw state fields (`pr_state`, `run_conclusion`, `resolved_comment_count`, etc.) already sent by the backend instead of parsing emoji from display strings.

## Approach

- **Keep separate columns** — PR, Checks, Comments remain distinct columns (no consolidation)
- **CSS-only colored dots** — `<span>` with `border-radius: 50%`, no SVG or external deps
- **Frontend-only change** — Python backend already sends all needed raw fields via `dataclasses.asdict()`; no backend changes required
- **No new column for run state** — out of scope for this step

## Color Palette (VS Code dark theme)

| Color  | Hex       | Used For                                      |
| ------ | --------- | --------------------------------------------- |
| Green  | `#4ec9b0` | PR open, checks pass, all comments resolved   |
| Amber  | `#dcdcaa` | PR draft, checks running, unresolved comments |
| Purple | `#c586c0` | PR merged                                     |
| Red    | `#f44747` | PR closed, checks failed                      |
| Gray   | `#666666` | No data / none                                |

## Files to Modify/Create

### 1. Extend TypeScript interface — `erkdesk/src/types/erkdesk.d.ts`

Add fields already sent by backend but undeclared:

```
run_status: string | null
run_conclusion: string | null
resolved_comment_count: number
total_comment_count: number
```

### 2. Create `StatusIndicator` component (new files)

- `erkdesk/src/renderer/components/StatusIndicator.tsx` — renders `<span>` colored dot with `title` tooltip
- `erkdesk/src/renderer/components/StatusIndicator.css` — 8px circle, 5 color variants

### 3. Create status derivation helpers (new file)

- `erkdesk/src/renderer/components/statusHelpers.ts`

Three pure functions mapping raw state to `{color, text, tooltip}`:

- `derivePrStatus(plan)` — maps `pr_state` + `pr_number` to dot color + "#NNN" text
- `deriveChecksStatus(plan)` — maps `run_status`/`run_conclusion` to dot color + checkmark/x text
- `deriveCommentsStatus(plan)` — maps `resolved_comment_count`/`total_comment_count` to dot color + "N/M" text

### 4. Update PlanList component — `erkdesk/src/renderer/components/PlanList.tsx`

Replace three table cells:

| Column   | Before                           | After                                          |
| -------- | -------------------------------- | ---------------------------------------------- |
| PR       | `{plan.pr_display}` (emoji text) | `<StatusIndicator>` dot + `#NNN` text          |
| Checks   | `{plan.checks_display}` (emoji)  | `<StatusIndicator>` dot + checkmark/x          |
| Comments | `{plan.comments_display}` (text) | `<StatusIndicator>` dot + `N/M` text (colored) |

Each cell renders: `[colored-dot] [text]` in an inline-flex container.

### 5. Update PlanList CSS — `erkdesk/src/renderer/components/PlanList.css`

- Add `.plan-list__status-cell` for inline-flex dot+text alignment
- Widen PR column from 70px to 80px (dot adds ~12px)
- Possibly widen Checks column from 40px to 50px

### 6. Update test fixtures — 3 files with `makePlan` helpers

Add new fields with defaults to `makePlan` in:

- `erkdesk/src/renderer/App.test.tsx`
- `erkdesk/src/renderer/components/PlanList.test.tsx`
- `erkdesk/src/renderer/components/ActionToolbar.test.tsx`

### 7. Create tests for status helpers (new file)

- `erkdesk/src/renderer/components/statusHelpers.test.ts`

Test all state-to-color mappings:

- Each `pr_state` value + null
- Each `run_conclusion` value + `run_status` = "in_progress"
- Comment counts: 0/0, partial, fully resolved

## Implementation Order

1. Add fields to `PlanRow` interface in `erkdesk.d.ts`
2. Create `StatusIndicator.tsx` + `StatusIndicator.css`
3. Create `statusHelpers.ts`
4. Create `statusHelpers.test.ts` — run tests
5. Update `PlanList.tsx` to use new components
6. Update `PlanList.css` for layout
7. Update `makePlan` in all 3 test files
8. Run full test suite, verify visually with `npm start`

## Verification

1. Run `npm test` in `erkdesk/` — all tests pass
2. Run `npm start` in `erkdesk/` — launch the app
3. Visually confirm:
   - PR column shows colored dot (green for open, purple for merged, etc.) + PR number
   - Checks column shows colored dot (green for pass, red for fail)
   - Comments column shows colored text with dot when unresolved comments exist
   - Selected row (blue background) still has visible dots
   - No emoji characters visible in any column
