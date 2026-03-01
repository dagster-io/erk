# Fix: Dispatch fails when plan branch is already in a worktree slot

## Context

When dispatching a plan via `erk pr dispatch` (from TUI or CLI), the command fails with:
```
Failed to dispatch plan #8544: stderr: fatal: 'plnd/doc-mid-rebase-behavior-03-01-1326'
is already used by worktree at '/Users/schrockn/.erk/repos/erk/worktrees/erk-slot-54'
```

This happens because `_dispatch_planned_pr_plan()` checks out the plan branch in the **root worktree** to commit `.erk/impl-context/` and push. But if the branch is already checked out in a slot (from a previous `erk implement` run), git refuses the checkout. This is git's safety mechanism preventing the same branch in two worktrees.

The fix: detect the existing worktree and use it directly instead of checking out in root.

## Changes

### 1. Add worktree detection in `_dispatch_planned_pr_plan()`

**File:** `src/erk/cli/commands/pr/dispatch_cmd.py` (lines 226-277)

Replace the checkout-in-root logic with a LBYL check using `find_worktree_for_branch()`:

```python
# Fetch the branch from remote (always needed)
ctx.git.remote.fetch_branch(repo.root, "origin", branch_name)

# LBYL: Check if branch is already in a worktree (e.g., from prior erk implement)
existing_worktree = ctx.git.worktree.find_worktree_for_branch(repo.root, branch_name)
if existing_worktree is not None:
    user_output(
        f"Branch already in worktree at {click.style(str(existing_worktree), fg='cyan')}, "
        "using it for dispatch"
    )
    work_dir = existing_worktree
    checked_out_in_root = False
else:
    # Branch not in any worktree — checkout in root
    user_output(f"Checking out existing plan branch: {click.style(branch_name, fg='cyan')}")
    local_branches = ctx.git.branch.list_local_branches(repo.root)
    if branch_name not in local_branches:
        remote_ref = f"origin/{branch_name}"
        ctx.branch_manager.create_tracking_branch(repo.root, branch_name, remote_ref)
    ctx.branch_manager.checkout_branch(repo.root, branch_name)
    work_dir = repo.root
    checked_out_in_root = True
```

Then replace all subsequent `repo.root` references (lines 238-269) with `work_dir`:
- `pull_rebase(work_dir, ...)`
- `impl_context_exists(work_dir)` / `remove_impl_context(work_dir)`
- `create_impl_context(..., repo_root=work_dir, ...)`
- `stage_files(work_dir, ...)` / `commit(work_dir, ...)` / `push_to_remote(work_dir, ...)`

And conditionally restore the original branch:
```python
if checked_out_in_root:
    ctx.branch_manager.checkout_branch(repo.root, original_branch)
```

Keep `retrack_branch(repo.root, ...)` as-is — Graphite metadata is repo-global.

### 2. Add test for branch-in-worktree scenario

**File:** `tests/commands/pr/test_dispatch.py`

Add `test_dispatch_planned_pr_plan_uses_existing_worktree_when_branch_occupied()`:
- Configure `FakeGit` with a `WorktreeInfo` entry mapping the plan branch to a slot path
- Invoke `erk pr dispatch 42 --base main`
- Assert: output mentions "already in worktree"
- Assert: workflow was triggered successfully
- Assert: `.erk/impl-context/` was created in the worktree path (not root)
- Assert: no `Traceback` in output

Setup: Add the worktree to `FakeGit`'s worktrees dict:
```python
slot_path = env.cwd.parent / "erk-slot-54"
slot_path.mkdir(parents=True)
git = FakeGit(
    worktrees={env.cwd: [
        WorktreeInfo(path=env.cwd, branch="main", is_root=True),
        WorktreeInfo(path=slot_path, branch=plan_branch, is_root=False),
    ]},
    ...
)
```

### 3. Update existing test assertion

**File:** `tests/commands/pr/test_dispatch.py`

The existing test at line 133 asserts `"Checking out existing plan branch" in result.output`. Since the no-conflict path still prints this message, no change needed — the new worktree-detected path prints a different message.

## Key files

- `src/erk/cli/commands/pr/dispatch_cmd.py` — main fix (lines 226-277 of `_dispatch_planned_pr_plan`)
- `tests/commands/pr/test_dispatch.py` — new test
- `packages/erk-shared/src/erk_shared/gateway/git/worktree/fake.py` — `FakeWorktree` (no changes, just used in test setup)
- `packages/erk-shared/src/erk_shared/gateway/git/worktree/real.py:149` — `find_worktree_for_branch()` (existing, reused)

## Verification

1. Run existing dispatch tests: `uv run pytest tests/commands/pr/test_dispatch.py`
2. Run new test to verify worktree conflict is handled
3. Run ty/ruff for type/lint checks
