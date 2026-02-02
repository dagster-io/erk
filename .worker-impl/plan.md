# Fix: trigger-async-learn crashes when plan has no branch_name

## Problem

`erk land` → `trigger-async-learn` → `get-pr-for-plan` exits with code 1 when the plan-header has no `branch_name` field. `_run_subprocess` treats any non-zero exit as fatal, killing the entire learn pipeline.

**Root cause**: `branch_name` is intentionally omitted when a plan is created (`plan_issues.py:165`). It's only set later by `impl-signal started`, which runs with `2>/dev/null || true` in `plan-implement.md:184`. If `impl-signal` fails silently, `branch_name` stays missing forever.

## Two-part fix

### Part 1: Resilience — trigger-async-learn handles missing PR gracefully

PR lookup is optional context for learning. If `get-pr-for-plan` fails, skip review comments and continue.

**File: `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`**

1. Add `_run_subprocess_lenient` function (after `_run_subprocess`):
   - Same subprocess pattern as `_run_subprocess`
   - On non-zero exit: log a dim warning to stderr, return `None`
   - On success: parse and return JSON
   - On empty output or invalid JSON: return `None`

2. Replace `_run_subprocess` call at line ~294 with `_run_subprocess_lenient`

3. Update check at line ~300: `if pr_result is not None and pr_result.get("success") and pr_result.get("pr_number"):`

**File: `tests/unit/cli/commands/exec/scripts/test_trigger_async_learn.py`**

4. Add test: `test_trigger_async_learn_pr_lookup_failure_continues` — mock `get-pr-for-plan` with `returncode=1` and stderr error JSON, verify pipeline still succeeds (skips review comments, continues to upload and trigger workflow)

### Part 2: Root cause — plan-implement sets branch_name even if impl-signal fails

The `erk:plan-implement` command calls `impl-signal started` which sets `branch_name` on the issue. But `impl-signal` can fail silently. Add a fallback in `get-pr-for-plan` to detect the branch from the current git context when `branch_name` is missing from the plan-header.

**File: `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py`**

5. When `branch_name is None` (line 82), before returning the error, attempt to infer the branch:
   - Get current git branch via `subprocess.run(["git", "branch", "--show-current"])`
   - Check if the branch name starts with `P{issue_number}-` (standard erk branch naming)
   - If it matches, use that branch name instead of erroring
   - If no match, fall back to existing error behavior

This way, when `trigger-async-learn` is called from `erk land` (which runs in the worktree on the correct branch), the PR can still be found even if `branch_name` was never written to the plan-header.

**File: `tests/unit/cli/commands/exec/scripts/test_get_pr_for_plan.py`**

6. Add test: branch inference when plan-header has no `branch_name` but current git branch matches `P{issue}-*` pattern

## Verification

- `pytest tests/unit/cli/commands/exec/scripts/test_trigger_async_learn.py`
- `pytest tests/unit/cli/commands/exec/scripts/test_get_pr_for_plan.py`
- All existing tests pass unchanged
- New tests confirm both resilience and branch inference
