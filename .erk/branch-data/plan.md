# Sync local branch with remote for draft-PR plans

## Context

When implementing a draft-PR plan locally, the local branch can fall out of sync with remote. `plan_save.py` creates a branch, commits `.erk/branch-data/` files, pushes to remote, then **checks back to the original branch**. When the user later implements on this branch, the remote may have additional commits (from workflow runs). `gt submit` detects this divergence and fails.

The user wants: "fix the process so that remote and local are in sync. branch-data should exist locally."

## Changes

### 1. Modify `setup-impl-from-issue` to detect and reuse draft-PR plan branches

**File:** `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py`

After fetching the plan (line 105), detect if it has a `branch_name` in `header_fields` (the canonical marker for draft-PR plans, same pattern as `issue_workflow.py:104`). If so:

1. Use that branch name instead of generating a new `P{issue}-...` name
2. Fetch the branch from remote
3. Check out or create the local tracking branch
4. Pull-rebase to sync local with remote

```python
# New imports
from erk_shared.gateway.github.metadata.schemas import BRANCH_NAME
from erk_shared.gateway.git.remote_ops.types import PullRebaseError

# After line 105 (plan = result), before line 108 (current_branch):
plan_branch = plan.header_fields.get(BRANCH_NAME)
```

Then restructure the branch logic (lines 108-148):

- If `plan_branch` is a non-empty string: use it, fetch from remote, checkout, pull-rebase
- If `current_branch == plan_branch`: skip branch creation, just sync
- If branch exists locally: checkout + pull-rebase
- If branch doesn't exist locally: create from `origin/{plan_branch}`, checkout
- Else (no plan_branch): fall through to existing `P{issue}-...` logic unchanged

**Key existing functions to reuse:**

- `git.remote.fetch_branch(repo_root, "origin", branch_name)` — fetches remote branch
- `git.remote.pull_rebase(cwd, "origin", branch_name)` — syncs local with remote, returns `PullRebaseResult | PullRebaseError`
- `git.branch.list_local_branches(repo_root)` — checks if branch exists locally
- `branch_manager.checkout_branch(cwd, branch_name)` — checks out the branch

### 2. Update plan-implement skill to always run setup when issue tracking is present

**File:** `.claude/commands/erk/plan-implement.md`

Currently, when `impl-init --json` returns `valid: true`, the skill skips `setup-impl-from-issue` entirely. This means the sync never happens for resumed implementations.

Change Steps 1a and 1b: when `impl-init` returns valid AND `has_issue_tracking: true`, still call `setup-impl-from-issue` (which is now idempotent for draft-PR plans) to ensure sync. The `--no-impl` flag can be used since `.impl/` already exists.

### 3. Add tests

**File:** `tests/unit/cli/commands/exec/scripts/test_setup_impl_from_issue.py`

Add tests to the existing test file:

1. **`test_draft_pr_plan_uses_plan_branch_name`**: Plan with `header_fields[BRANCH_NAME]` → uses that branch, calls `fetch_branch`, `pull_rebase`
2. **`test_draft_pr_plan_already_on_plan_branch`**: Already on the plan branch → no branch creation, still syncs
3. **`test_draft_pr_plan_sync_failure_reports_error`**: `pull_rebase` returns error → exit code 1 with error JSON
4. **`test_issue_plan_without_branch_name_uses_p_prefix`**: Regression test — plan without `BRANCH_NAME` in header_fields still generates `P{issue}-...`

Tests use `FakeGitHub` with a draft PR whose body includes a `plan-header` metadata block containing `branch_name`. Pass `plan_store=DraftPRPlanBackend(fake_github, fake_issues, time=FakeTime())` to `context_for_test`. Assert on `fake_git.fetched_branches` and `fake_git.pull_rebase_calls`.

## Files to modify

| File                                                                 | Change                                                                |
| -------------------------------------------------------------------- | --------------------------------------------------------------------- |
| `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py`         | Add draft-PR branch detection + remote sync                           |
| `.claude/commands/erk/plan-implement.md`                             | Always call setup-impl-from-issue for sync when issue tracking exists |
| `tests/unit/cli/commands/exec/scripts/test_setup_impl_from_issue.py` | Add 4 new tests                                                       |

## Verification

1. Run existing tests: `pytest tests/unit/cli/commands/exec/scripts/test_setup_impl_from_issue.py`
2. Run new tests to verify draft-PR sync behavior
3. Run `make fast-ci` to verify no regressions
