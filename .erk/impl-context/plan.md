# Auto-recover plan context on `erk impl` retry

## Context

When implementation fails on a plan PR, the branch is left in a broken state: `.erk/impl-context/` has been cleaned up (committed + pushed), lifecycle_stage is "impl", and partial implementation commits may exist. Currently the user must manually `git revert` the cleanup commit and reset state before retrying. This should be automatic.

## Approach

Add retry detection and auto-recovery to `erk impl`. When `erk impl` detects it's being run on a branch where implementation was previously attempted, it automatically:

1. Resets the branch to pre-implementation state (merge-base with base branch)
2. Force-pushes the reset
3. Resets lifecycle_stage to "planned" on the PR
4. Proceeds with normal implementation (re-creates impl-context from PR body)

The core reset logic lives in a new `erk exec impl-reset` command (reusable from CI and plan-implement.md). `implement.py` calls this automatically when retry is detected.

## Retry Detection

A retry is detected when ALL of these are true:
- Strategy 1 failed (no `.erk/impl-context/` on disk)
- Strategy 2 found a plan PR via `extract_plan_from_current_branch()`
- The branch has commits beyond the merge-base with the PR's base branch

When detected, `erk impl` prints a message ("Previous implementation detected, resetting branch...") and runs the reset before proceeding to `_implement_from_issue`.

## Implementation

### Phase 1: New exec command `erk exec impl-reset`

**Create** `src/erk/cli/commands/exec/scripts/impl_reset.py`

Core logic:
1. Detect plan PR from current branch (reuse `resolve_plan_id_for_branch` pattern from `implement_shared.py`)
2. Fetch PR to get `base_ref_name` (e.g., "master")
3. Fetch origin to ensure up-to-date refs: `git.remote.fetch_branch(repo_root, "origin", base_ref)`
4. Get merge-base: `git.analysis.get_merge_base(repo_root, f"origin/{base_ref}", "HEAD")`
5. Check if branch has commits beyond merge-base (if HEAD == merge-base, nothing to reset)
6. `git.branch.reset_hard(cwd, merge_base_sha)`
7. `git.remote.push_to_remote(cwd, "origin", branch, set_upstream=False, force=True)`
8. Reset lifecycle via `backend.post_event(repo_root, plan_id, metadata={"lifecycle_stage": "planned"}, comment=reset_comment)`
9. Output JSON: `{"success": true, "plan_number": N, "reset_to": "<sha>", "lifecycle_stage": "planned"}`

Interface:
```
erk exec impl-reset [--plan-number <N>]
```
If `--plan-number` omitted, auto-detect from current branch.

Follow patterns from `impl_signal.py`: Click context injection, JSON output, `require_git`/`require_plan_backend`/`require_repo_root`, graceful error handling (exit 0 on soft errors).

Reuse:
- `require_plan_backend(ctx)` from `erk_shared.context.helpers`
- `git.analysis.get_merge_base()` from `erk_shared.gateway.git.analysis_ops`
- `git.branch.reset_hard()` from `erk_shared.gateway.git.branch_ops`
- `git.remote.push_to_remote(..., force=True)` from `erk_shared.gateway.git.remote_ops`
- `render_erk_issue_event()` for the reset comment
- `github.get_pr()` to get `base_ref_name`

### Phase 2: Register exec command

**Modify** `src/erk/cli/commands/exec/group.py`
- Import `impl_reset` from the new module
- `exec_group.add_command(impl_reset, name="impl-reset")`

### Phase 3: Wire auto-recovery into `erk impl`

**Modify** `src/erk/cli/commands/implement.py`

In the `implement()` function, between Strategy 1 (existing impl-context) and Strategy 2 (extract from branch), add retry detection:

```python
# Strategy 2: Extract plan number from GitHub PR
detected_plan = extract_plan_from_current_branch(ctx)
if detected_plan is not None:
    # Check for retry: branch has commits beyond merge-base
    if _is_retry(ctx, current_branch):
        _auto_reset(ctx, detected_plan)
    target = detected_plan
    user_output(f"Auto-detected plan #{target} from branch")
```

**Add** helper functions to `implement.py` (or `implement_shared.py`):

`_is_retry(ctx, branch)` — Returns True if the branch has commits beyond the merge-base with master. Uses `git.analysis.get_merge_base()` and compares HEAD to merge-base.

`_auto_reset(ctx, plan_number)` — Invokes the impl-reset logic:
1. Import and call the core reset function from `impl_reset.py`
2. Or shell out to `erk exec impl-reset --plan-number <N>`

Prefer direct function call to avoid subprocess overhead. Extract the core logic from `impl_reset.py` into a callable function that both the exec command and `implement.py` can use.

### Phase 4: Tests

**Create** `tests/unit/cli/commands/exec/scripts/test_impl_reset.py`

Test cases:
- Reset with implementation commits: verifies branch reset + lifecycle update
- Reset with no commits beyond merge-base: no-op (already clean)
- Auto-detect plan number from branch
- Explicit `--plan-number` flag
- Error: not on a plan branch
- Error: merge-base computation fails

**Modify** existing implement tests to cover retry detection:
- `erk impl` on a branch with prior impl commits triggers auto-reset
- `erk impl` on a clean plan branch does not trigger reset

## Key Files

| File | Action |
|------|--------|
| `src/erk/cli/commands/exec/scripts/impl_reset.py` | Create |
| `src/erk/cli/commands/exec/group.py` | Register new command |
| `src/erk/cli/commands/implement.py` | Add retry detection + auto-reset |
| `tests/unit/cli/commands/exec/scripts/test_impl_reset.py` | Create |

## Verification

1. Set up a plan PR, run implementation partway, then abort
2. Run `erk impl -d` again — should auto-detect retry, reset branch, and start fresh
3. Run `erk exec impl-reset` directly — should reset and output JSON
4. Run `erk impl` on a clean plan branch — should NOT trigger reset
5. Check PR metadata shows lifecycle_stage "planned" after reset
6. Run `make fast-ci` to verify tests pass
