# Fix: `erk pr dispatch` fails when branch is checked out in worktree

## Context

`erk pr dispatch` crashes when run from a worktree that has the target branch checked out. Line 223 of `dispatch_cmd.py` runs `git branch -f <branch> origin/<branch>` to sync the local ref to remote, but git refuses to force-update a branch that's checked out in any worktree.

## Root Cause

`create_branch(..., force=True)` uses `git branch -f` which has a safety check preventing updates to checked-out branches. The function's docstring says "no checkout required" but it doesn't account for the branch already being checked out elsewhere.

## Fix

Replace `create_branch` with `update_local_ref` on line 223 of `dispatch_cmd.py`. `update_local_ref` uses `git update-ref` (plumbing command) which works regardless of checkout status. The downstream `commit_files_to_branch` already uses `git update-ref` internally, so this is consistent.

**File:** `src/erk/cli/commands/pr/dispatch_cmd.py` (line 220-223)

Before:
```python
ctx.git.remote.fetch_branch(repo.root, "origin", branch_name)
ctx.git.branch.create_branch(repo.root, branch_name, f"origin/{branch_name}", force=True)
```

After:
```python
ctx.git.remote.fetch_branch(repo.root, "origin", branch_name)
remote_sha = ctx.git.branch.get_branch_head(repo.root, f"origin/{branch_name}")
if remote_sha is None:
    raise UserFacingCliError(f"Remote branch 'origin/{branch_name}' not found after fetch")
ctx.git.branch.update_local_ref(repo.root, branch_name, remote_sha)
```

## Verification

1. Run existing dispatch tests: `pytest tests/commands/pr/test_dispatch.py`
2. Manual test: `erk pr dispatch` from a worktree with the target branch checked out
