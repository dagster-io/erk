# Fix: `gt track` fails during `erk pr checkout` in worktree context

## Context

`erk pr checkout 8348` crashed during the Graphite tracking step. The `gt track` command received `worktree_path` (e.g., `/Users/schrockn/.erk/repos/erk/worktrees/erk-slot-47`) as its working directory, but Graphite failed with `ERROR: Could not find branch ... source: no such file or directory:`. Running the identical command manually from the same path seconds later succeeded.

The root cause: in `checkout_cmd.py`, the `track_branch` and `retrack_branch` calls pass `worktree_path` as the first argument, but **every other call site in the codebase** passes `repo.root` (the main repo root). The `worktree_path` value is a git worktree, where `git rev-parse --git-dir` returns `.git/worktrees/<name>/` instead of `.git/`. Graphite likely uses `--git-dir` to locate branch refs, leading to an incorrect lookup path in worktree contexts. The transient nature suggests a Graphite caching/timing interaction, but using `repo.root` avoids the issue entirely and is consistent with all other callers.

## Changes

### 1. Fix `src/erk/cli/commands/pr/checkout_cmd.py` (lines 293, 296)

Change both Graphite calls from `worktree_path` to `repo.root`:

```python
# Line 293 - currently:
ctx.branch_manager.track_branch(worktree_path, branch_name, pr.base_ref_name)
# Change to:
ctx.branch_manager.track_branch(repo.root, branch_name, pr.base_ref_name)

# Line 296 - currently:
ctx.branch_manager.retrack_branch(worktree_path, branch_name)
# Change to:
ctx.branch_manager.retrack_branch(repo.root, branch_name)
```

### 2. Fix `src/erk/cli/commands/branch/checkout_cmd.py` (line 127)

Same pattern — uses `target_path` (a worktree path) instead of `repo_root`:

```python
# Line 127 - currently:
ctx.branch_manager.track_branch(target_path, branch, trunk_branch)
# Change to:
ctx.branch_manager.track_branch(repo_root, branch, trunk_branch)
```

`repo_root` is already a parameter of `_ensure_graphite_tracking` (line 81).

### 3. Update test to verify repo root is passed

In `tests/commands/pr/test_checkout_graphite_linking.py`, enhance `test_pr_checkout_tracks_untracked_branch_with_graphite` to assert `track_branch` was called with the repo root path (not a worktree subpath). Use `FakeGraphiteBranchOps.track_branch_calls` to inspect the `cwd` argument.

## Verification

- Run `pytest tests/commands/pr/test_checkout_graphite_linking.py`
- Run `pytest tests/commands/navigation/test_checkout.py`
- Run `ty` for type checking
