# Fix `erk prepare` for draft PR plan backend

## Context

When using the draft PR plan backend (`ERK_PLAN_BACKEND=draft_pr`), `plan-save` creates a branch locally, pushes it to remote, and creates a draft PR. When the user then runs `erk prepare <PR-number>`, it fails with:

```
Error: Branch 'plan-add-print-statement-to-fir-02-19-0802' already exists.
Use `erk br assign` to assign an existing branch to a slot.
```

The branch is **expected** to exist — `plan-save` created it. The error is incorrect.

## Changes

### 1. Add `branch_preexists` field to `IssueBranchSetup`

**File:** `packages/erk-shared/src/erk_shared/issue_workflow.py`

- Add `branch_preexists: bool` field to `IssueBranchSetup` (after `objective_issue`, before `warnings`)
- In `prepare_plan_for_worktree()`, set via `branch_preexists=(plan_backend == "draft_pr")` in the return statement

### 2. Handle pre-existing branches in `branch_create`

**File:** `src/erk/cli/commands/branch/create_cmd.py`

Replace the unconditional "branch already exists" check (lines 150-176) with backend-aware logic:

- When `setup is not None and setup.branch_preexists`:
  - If branch exists locally: skip creation, output `"Using existing branch: {name}"`
  - If branch doesn't exist locally: fetch from remote via `ctx.git.remote.fetch_branch()`, then `ctx.branch_manager.create_tracking_branch()` from `origin/<branch>`, output `"Created tracking branch: {name}"`
  - Track with Graphite via `ctx.branch_manager.track_branch(repo.root, branch_name, trunk)` (no-op for plain Git)
- Else (standard path): keep existing logic unchanged

### 3. Tests

**File:** `tests/unit/shared/test_issue_workflow.py`
- Add `assert result.branch_preexists is True` to `test_draft_pr_backend_uses_existing_branch`
- Add `assert result.branch_preexists is False` to `test_prepare_plan_valid_returns_setup`

**File:** `tests/unit/cli/commands/test_prepare.py`
- Add `test_prepare_with_draft_pr_backend_existing_branch` — plan-save created the branch locally, prepare should succeed with "Using existing branch"
- Add `test_prepare_with_draft_pr_backend_remote_only_branch` — branch only on remote, prepare should fetch and create tracking branch
- Both tests use `monkeypatch.setenv("ERK_PLAN_BACKEND", "draft_pr")`, `create_draft_pr_store_with_plans`, and plan bodies with `format_plan_header_body_for_test(branch_name=...)` so `header_fields` roundtrips correctly through the store

## Verification

1. Run `pytest tests/unit/shared/test_issue_workflow.py` — verify `branch_preexists` assertions
2. Run `pytest tests/unit/cli/commands/test_prepare.py` — verify new draft PR tests pass and existing tests unchanged
3. Run `make fast-ci` — full fast CI pass