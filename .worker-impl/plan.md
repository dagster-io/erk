# Plan: Add `get_plan_for_branch` to PlanBackend and migrate callers

## Context

Objective #7163 migrates the plan system of record from GitHub Issues to Draft PRs. A key blocker is the `extract_leading_issue_number(branch)` function — called in 15+ files — which parses plan issue numbers from branch names (`P{number}-...`). This approach assumes the plan identifier is known before the branch is created, which breaks with draft PRs (the PR number doesn't exist until after the branch is pushed).

The fix: make `get_plan_for_branch(branch) -> int | None` a method on `PlanBackend`. The issues backend implements it via branch name parsing (current behavior). A future draft PR backend implements it via cached GitHub API lookup. All callers migrate to the new abstraction.

## Changes

### 1. Add abstract method to `PlanBackend`

**`packages/erk-shared/src/erk_shared/plan_store/backend.py`**

```python
@abstractmethod
def get_plan_for_branch(self, branch_name: str) -> int | None:
    """Get the plan number associated with a branch.

    For issue-backed plans: parses P{number}- from the branch name.
    For draft-PR-backed plans: looks up the PR for the branch via API (cached).
    """
    ...
```

### 2. Implement in `GitHubPlanStore`

**`packages/erk-shared/src/erk_shared/plan_store/github.py`**

```python
def get_plan_for_branch(self, branch_name: str) -> int | None:
    return _extract_leading_issue_number(branch_name)
```

Move `extract_leading_issue_number` from `naming.py` into `github.py` as a private module-level function `_extract_leading_issue_number`. (Or import it privately — the key is that no external caller uses it directly anymore.)

### 3. Migrate call sites (12 files with `ctx`)

Each site: replace `extract_leading_issue_number(branch)` with `ctx.plan_backend.get_plan_for_branch(branch)`.

| # | File | Call site |
|---|------|-----------|
| 1 | `src/erk/cli/commands/objective_helpers.py:86` | `plan_number = extract_leading_issue_number(branch)` |
| 2 | `src/erk/cli/commands/objective_helpers.py:148` | `plan_number = extract_leading_issue_number(branch)` |
| 3 | `src/erk/cli/commands/pr/shared.py:205` | `branch_issue = extract_leading_issue_number(branch_name)` |
| 4 | `src/erk/cli/commands/land_pipeline.py:343` | `plan_issue_number = extract_leading_issue_number(state.branch)` |
| 5 | `src/erk/cli/commands/land_pipeline.py:645` | `plan_issue_number = extract_leading_issue_number(branch)` |
| 6 | `src/erk/cli/commands/pr/metadata_helpers.py:82` | `plan_issue_number = extract_leading_issue_number(branch_name)` |
| 7 | `src/erk/cli/commands/land_cmd.py:1071` | `plan_issue_number = extract_leading_issue_number(target.branch)` |
| 8 | `src/erk/cli/commands/plan/checkout_cmd.py:47` | `branch_issue = extract_leading_issue_number(branch)` |
| 9 | `src/erk/cli/commands/plan/view.py:251` | `issue_number = extract_leading_issue_number(branch)` |
| 10 | `src/erk/cli/commands/exec/scripts/get_learn_sessions.py:241` | `issue_number = extract_leading_issue_number(branch_name)` |
| 11 | `src/erk/cli/commands/exec/scripts/track_learn_evaluation.py:175` | `issue_number = extract_leading_issue_number(branch)` |
| 12 | `src/erk/cli/commands/implement_shared.py:468` | `issue_num = extract_leading_issue_number(current_branch)` |
| 13 | `src/erk/cli/commands/learn/learn_cmd.py:121` | `issue_number = extract_leading_issue_number(branch_name)` |
| 14 | `src/erk/core/plan_context_provider.py:69` | `issue_number = extract_leading_issue_number(branch_name)` |

### 4. Migrate `plan_data_provider` (has `self._ctx`)

**`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py:434`**

Replace `extract_leading_issue_number(worktree.branch)` with `self._ctx.plan_backend.get_plan_for_branch(worktree.branch)`.

### 5. Migrate `impl_folder.py` (thread dependency)

**`packages/erk-shared/src/erk_shared/impl_folder.py:261`**

The `discover_plan_id()` function is a standalone utility. Add `plan_backend: PlanBackend` as a parameter. Update all callers of `discover_plan_id()` to pass `ctx.plan_backend`.

### 6. Remove `get_branch_issue` from git branch ops

**Remove from:**
- `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/abc.py:237` — abstract method
- `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/real.py:355` — real impl
- `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/fake.py:328` — fake impl
- `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/printing.py:100` — printing wrapper
- `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/dry_run.py:107` — dry-run wrapper

**Migrate sole caller:**
- `src/erk/cli/commands/wt/list_cmd.py:108` → use `ctx.plan_backend.get_plan_for_branch()`

**Update tests:**
- `tests/unit/fakes/test_fake_git.py:410-452` — remove `get_branch_issue` tests

### 7. Clean up `naming.py` export

**`packages/erk-shared/src/erk_shared/naming.py`**

Keep `extract_leading_issue_number` as a private-by-convention function (prefix with `_`) or move it into `github.py`. The `extract_objective_number` and `extract_plan_review_issue_number` functions that depend on similar patterns stay in `naming.py` for now (they're used by different subsystems).

## Verification

1. Run `make fast-ci` — all tests should pass since `GitHubPlanStore.get_plan_for_branch()` delegates to the same parsing logic
2. Grep for `extract_leading_issue_number` — should have zero public callers (only the private impl in `github.py`)
3. Grep for `get_branch_issue` — should have zero results after removal