# Fix: `erk pr dispatch` auto-detect from branch context

## Context

When running `erk pr dispatch` with no arguments on a plan branch (`plnd/fix-activation-workspace-d-03-02-0950`), auto-detection fails with "No plan numbers provided and could not auto-detect from context" even though `gt pr` correctly identifies PR #8622.

The root cause is that `_detect_plan_number_from_context()` in `dispatch_cmd.py` only checks `.erk/impl-context/` for a valid `ref.json` via `resolve_impl_dir()` + `read_plan_ref()`. When the branch-scoped impl dir doesn't exist (or the root `ref.json` is incomplete — missing `plan_id`, `url`, `created_at`, `synced_at`), it returns `None` with no fallback.

Other commands like `implement_shared.py` and `land_cmd.py` already use `ctx.plan_backend.resolve_plan_id_for_branch()` which queries the GitHub API to find the PR for the current branch. The dispatch command should use this same fallback.

## Change

**File:** `src/erk/cli/commands/pr/dispatch_cmd.py`

Modify `_detect_plan_number_from_context()` (lines 356-378) to add a GitHub API fallback when the impl-context lookup fails:

```python
def _detect_plan_number_from_context(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    branch_name: str | None,
) -> int | None:
    # Step 1: Check .erk/impl-context/ (existing logic, no API call)
    impl_dir = resolve_impl_dir(repo.root, branch_name=branch_name)
    if impl_dir is not None:
        plan_ref = read_plan_ref(impl_dir)
        if plan_ref is not None and plan_ref.plan_id.isdigit():
            return int(plan_ref.plan_id)

    # Step 2: Fall back to GitHub API lookup (like implement_shared and land_cmd)
    if branch_name is not None:
        plan_id = ctx.plan_backend.resolve_plan_id_for_branch(repo.root, branch_name)
        if plan_id is not None and plan_id.isdigit():
            return int(plan_id)

    return None
```

Update the call site (line 458) to pass `ctx` and `repo`:
```python
detected = _detect_plan_number_from_context(ctx, repo, branch_name=original_branch)
```

## Verification

- Run `erk pr dispatch` from a plan branch with a PR but no branch-scoped impl-context dir — should auto-detect
- Run existing tests: `pytest tests/unit/cli/commands/pr/` (if dispatch tests exist)
- Write a unit test for the fallback path using the fake plan backend
