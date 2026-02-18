# Plan: Feature Flag for Plan Backend (Objective #7163)

## Context

Objective #7163 migrates the plan system of record from GitHub Issues to Draft PRs. Before building the new backend, we need a toggle so:
- The new backend can be developed behind a flag
- Either removal path is clean (abandon or ship)

## Surface Analysis

Issue numbers are deeply embedded beyond just the `PlanBackend` abstraction. A backend swap alone is insufficient. The full surface area that needs gating:

| Surface | Files | Issue-Specific Coupling |
|---------|-------|------------------------|
| **PlanBackend / PlanStore** | `plan_store/github.py` | Metadata in issue bodies, issue closure |
| **PlanListService** | `services/plan_list_service.py` | GraphQL queries issues, keys by issue number |
| **TUI (erk dash)** | `tui/data/types.py`, `tui/widgets/plan_table.py`, `tui/commands/registry.py`, `tui/sorting/logic.py` | `PlanRowData.issue_number`, all commands build `erk plan X {issue_number}`, sort by issue number |
| **Branch naming** | `naming.py` | `P{issue_number}-` prefix, `extract_leading_issue_number()` |
| **Plan CLI commands** | `cli/commands/plan/create_cmd.py`, `list_cmd.py` | Creates issues, displays issue URLs, worktree-by-issue mapping |
| **Landing pipeline** | `land_cmd.py`, `land_pipeline.py` | Issue closure, learn tracking by `learned_from_issue` |
| **Exec scripts** | `exec/scripts/close_issue_with_comment.py`, `plan_update_issue.py`, many others | Accept `issue_number` args, call `github.close_issue()` |
| **CI workflows** | `.github/workflows/learn.yml` | Concurrency groups keyed by `issue_number` |
| **Objective linkage** | Objective roadmap steps | Plans linked by issue number |

## Approach

Use a Python constant as the feature flag, but the gating strategy is **layered**, not a single backend swap:

### Layer 1: Plan identifier abstraction (this PR)

Add the constant and introduce a `plan_id: str` concept that can be either an issue number or a PR number. The constant gates `create_context()` wiring for `PlanBackend` + `PlanListService`. This is the foundation — it makes the system _aware_ of multiple backends without changing any behavior.

**`packages/erk-shared/src/erk_shared/plan_store/backend.py`**
- Add `PlanBackendType = Literal["issues", "draft_pr"]`
- Add `PLAN_BACKEND: PlanBackendType = "issues"` module-level constant

**`src/erk/core/context.py`**
- Import `PLAN_BACKEND` from plan_store.backend
- At line ~575, branch on the constant:
  - `"issues"` → current `GitHubPlanStore` + `RealPlanListService` (unchanged)
  - `"draft_pr"` → `NotImplementedError` (until backend exists)

### Layer 2: Surface-by-surface gating (future PRs in objective)

Each surface listed above gets its own PR that reads `PLAN_BACKEND` and branches:
- **TUI**: `PlanRowData` gets a `plan_id: str` field alongside `issue_number` (or replacing it), command registry switches URL/number format
- **Branch naming**: `P{plan_id}-` prefix works for either issues or PRs (both are numeric)
- **Landing pipeline**: Close-on-merge replaces close-issue, learn tracking uses `plan_id`
- **Exec scripts**: Accept `plan_id` instead of `issue_number`
- **Workflows**: Concurrency groups key by `plan_id`

### Why layered, not big-bang

Each layer can be developed, tested, and reviewed independently. The constant is readable from anywhere — surfaces check it locally rather than threading it through function signatures. If we abandon, we remove the constant and all the `elif` branches collapse.

## Removal Scenarios

**Ship it**: Change constant to `"draft_pr"`, delete all `"issues"` branches across layers, then delete constant
**Abandon it**: Delete all `"draft_pr"` branches across layers + constant, code collapses back to direct paths

Both paths are symmetric — every gated surface has the same `if/elif` structure keyed on the same constant.

## Verification

Run `make fast-ci` to verify tests pass (behavior is unchanged since constant = "issues").
