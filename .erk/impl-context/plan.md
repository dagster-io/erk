# Fix stale plan-to-PR terminology in docs/learned/

## Context

PR #9352 renamed plan-focused modules to PR-focused terminology. During the squash merge, 4 doc files lost their fixes from the second address-review-comments commit. These files still reference stale names that were renamed in the PR.

## Changes

### 1. `docs/learned/cli/exec-script-performance.md`

- Line 9 (tripwire): `PlanListService` → `PrListService`
- Line 54 (body): `PlanListService` → `PrListService`

### 2. `docs/learned/planning/plan-title-prefix-system.md`

- Line 38: `[erk-plan]` → `[erk-pr]` (title tag reference)
- Line 41: `[erk-plan]` → `[erk-pr]` (example title)

### 3. `docs/learned/planning/planned-pr-backend.md`

- Line 98: `[erk-plan]` → `[erk-pr]` (x3 occurrences on the line)

### 4. `docs/learned/pr-operations/plan-embedding-in-pr.md`

- Line 26: `PlanContext` → `PrContext`

## Verification

- `grep -r 'PlanListService\|PlanContext\|\[erk-plan\]' docs/learned/` should show no hits in these 4 files after the fix
- `npx prettier --check` on all 4 files
