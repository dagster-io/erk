# Fix: `erk br co --for-plan` allocates a new slot instead of staying in current worktree

## Context

When running `erk br co --for-plan 8712` from a named worktree (e.g., `restructure-exit-plan-menu-03-03-0531`), the command allocates a new pool slot (`erk-slot-01`) instead of checking out the branch in the current worktree. Only `--new-slot` should trigger slot allocation.

The bug is in `src/erk/cli/commands/branch/checkout_cmd.py` lines 660-673. When `current_assignment is None` (user is not in a slot worktree) and the branch doesn't exist anywhere yet, the `else` branch at line 660 unconditionally calls `allocate_slot_for_branch`. It should only do this when `new_slot` is True.

## Changes

**File**: `src/erk/cli/commands/branch/checkout_cmd.py`

Replace the `else` block at line 660 with a two-way branch:

```python
elif new_slot:
    # Allocate slot for the branch (only when --new-slot explicitly requested)
    slot_result = allocate_slot_for_branch(...)
    ...
else:
    # No slot assignment, not --new-slot: checkout in current worktree
    ctx.branch_manager.checkout_branch(repo.root, branch)
    target_wt = WorktreeInfo(path=repo.root, branch=branch)

    if setup is not None:
        _rebase_and_track_for_plan(
            ctx, repo_root=repo.root, worktree_path=target_wt.path,
            branch=branch, parent_branch=parent_branch, trunk=trunk,
        )
        _setup_impl_for_plan(
            ctx, setup=setup, worktree_path=target_wt.path,
            branch_name=branch, script=script,
        )

    worktrees = ctx.git.worktree.list_worktrees(repo.root)
    _perform_checkout(
        ctx, repo_root=repo.root, target_worktree=target_wt,
        branch=branch, script=script, is_newly_created=False,
        worktrees=worktrees, force_script_activation=True,
    )
    return
```

The structure becomes three paths:
1. `current_assignment is not None` → stack in place (existing, lines 604-659)
2. `new_slot` → allocate slot (existing, lines 662-673, now under `elif`)
3. Neither → checkout in current worktree (new path, mirrors stack-in-place pattern)

## Verification

1. Run `make fast-ci` to confirm existing tests pass
2. Add a test for the new path: `erk br co --for-plan <plan>` from a non-slot worktree should checkout in the current worktree without allocating a slot
3. Manual test: from a named worktree, run `erk br co --for-plan <plan>` and confirm it stays in the current worktree
