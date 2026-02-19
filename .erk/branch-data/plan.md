# Fix: setup-impl-from-issue Switches to Wrong Branch in CI

## Context

When the remote implementation CI runs, it:

1. Checks out an implementation branch (e.g. `P7622-add-something-02-19-1430`)
2. Runs `erk exec create-worker-impl-from-issue $PLAN_ID` → creates `.worker-impl/plan-ref.json` with `plan_id="7622"`
3. Copies `.worker-impl/` to `.impl/` (so `.impl/plan-ref.json` exists with correct `plan_id`)
4. Launches the agent with `/erk:plan-implement 7622`

The agent calls `erk exec setup-impl-from-issue 7622`. For draft-PR plans, this command reads the `BRANCH_NAME` header field from the plan PR (e.g. `plan-add-something-02-19-1428`) and unconditionally switches to that branch — abandoning the implementation branch CI set up. All implementation work then lands on the plan branch instead of the implementation branch.

The fix: if `.impl/plan-ref.json` already exists with a matching `plan_id`, skip branch switching and stay on the current branch. The presence of `.impl/` with the right ref means CI already set up this worktree correctly.

## Files to Modify

### 1. `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py`

In the draft-PR branch section (lines 111–142), add a guard at the top before any branch operations:

```python
if isinstance(plan_branch, str) and plan_branch:
    # Check if .impl/ is already set up for this issue (e.g. CI pre-populated it)
    impl_dir = cwd / ".impl"
    existing_ref = read_plan_ref(impl_dir) if impl_dir.exists() else None
    if existing_ref is not None and existing_ref.plan_id == str(issue_number):
        click.echo(
            f"Found existing .impl/ for plan #{issue_number}, skipping branch setup",
            err=True,
        )
        branch_name = current_branch
    else:
        # Original logic: fetch, checkout, and sync the plan branch
        branch_name = plan_branch
        git.remote.fetch_branch(repo_root, "origin", branch_name)
        ...
```

Add import for `read_plan_ref` from `erk_shared.impl_folder` (already imported for `create_impl_folder`; add `read_plan_ref` to that import).

The `branch_name = current_branch` path falls through to Step 3 (create `.impl/` folder + save plan ref) which is idempotent — recreating with the same content is fine.

### 2. `tests/unit/cli/commands/exec/scripts/test_setup_impl_from_issue.py`

Add one new test after `test_draft_pr_plan_already_on_plan_branch`:

**`test_draft_pr_plan_skips_checkout_when_impl_exists`**

- Create a draft-PR backend (same `_make_draft_pr_backend` helper used in existing tests)
- Set `current_branch` to a different branch than `plan_branch` (simulating CI's implementation branch)
- Create a real `.impl/plan-ref.json` in `tmp_path / ".impl"` using `save_plan_ref()` with matching `plan_id`
- Assert: exit code 0, no `fetched_branches`, no `checked_out_branches` for the plan branch, output `branch` == current branch (not plan branch)

## Key Utilities to Reuse

- `read_plan_ref(impl_dir)` — `erk_shared.impl_folder:167` — reads `.impl/plan-ref.json` with legacy fallback, returns `PlanRef | None`
- `save_plan_ref(impl_dir, ...)` — `erk_shared.impl_folder:125` — use in test setup to create valid `.impl/plan-ref.json`
- `_make_draft_pr_backend(tmp_path, plan_branch)` — existing test helper in `test_setup_impl_from_issue.py` for creating draft-PR plan backends
- `FakeGit`, `context_for_test` — already used in the existing draft-PR tests in the same file

## Verification

1. Run existing tests: `pytest tests/unit/cli/commands/exec/scripts/test_setup_impl_from_issue.py`
   — all existing tests must still pass (behavior unchanged for non-CI cases)
2. New test passes: `test_draft_pr_plan_skips_checkout_when_impl_exists`
3. Type check: `ty check src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py`
