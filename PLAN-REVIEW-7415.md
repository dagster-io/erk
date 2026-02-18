# Plan: Feature Flag for Plan Backend (Objective #7163)

## Context

Objective #7163 migrates the plan system of record from GitHub Issues to Draft PRs. Before building the new backend, we need a toggle so:
- The new backend can be developed behind a flag
- Either removal path is clean (abandon or ship)

## Approach (Simplified)

Use a Python constant instead of config-backed flag. A single constant controls backend selection. Changing or removing it is a one-file edit.

## Changes

### 1. Add type and constant

**`packages/erk-shared/src/erk_shared/plan_store/backend.py`**
- Add `PlanBackendType = Literal["issues", "draft_pr"]`
- Add `PLAN_BACKEND: PlanBackendType = "issues"` module-level constant

### 2. Wire `create_context()` to use the constant

**`src/erk/core/context.py`**
- Import `PLAN_BACKEND` from plan_store.backend
- At line ~575, branch on the constant:
  - `"issues"` → current `GitHubPlanStore` + `RealPlanListService` (unchanged)
  - `"draft_pr"` → `NotImplementedError` (until backend exists)

### 3. No other changes needed

No config schema, no TOML loading, no test field count updates. The constant is the entire feature flag.

## Removal Scenarios

**Ship it**: Change constant to `"draft_pr"`, delete `GitHubPlanStore` + issues branch, then delete constant
**Abandon it**: Delete draft_pr branch + constant, back to direct `GitHubPlanStore`

## Verification

Run `make fast-ci` to verify tests pass (behavior is unchanged since constant = "issues").