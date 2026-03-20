---
title: sync_branch_to_sha Pattern
read_when:
  - "syncing a local branch to a known remote SHA"
  - "working with dispatch_helpers.py branch sync"
  - "handling checked-out branch updates in dispatch"
tripwires:
  - action: "calling update_local_ref on a branch without checking if it is checked out"
    warning: "Use sync_branch_to_sha instead. It detects checkout state and handles dirty worktrees. Direct update_local_ref on a checked-out branch desynchronizes the index. See sync-branch-to-sha-pattern.md."
  - action: "using sync_branch_to_sha when merge-base analysis is needed"
    warning: "sync_branch_to_sha moves a branch to a known SHA. For trunk sync with divergence detection, use ensure_trunk_synced(). See sync-branch-to-sha-pattern.md."
---

# sync_branch_to_sha Pattern

`sync_branch_to_sha` in `src/erk/cli/commands/pr/dispatch_helpers.py:12-40` moves a local branch ref to a target SHA, safely handling the case where the branch is currently checked out in a worktree.

## Function Signature

```python
def sync_branch_to_sha(ctx: ErkContext, repo_root: Path, branch: str, target_sha: str) -> None:
```

## Behavior

1. **Check checkout state**: `ctx.git.worktree.is_branch_checked_out(repo_root, branch)` → `Path | None`
2. **Not checked out**: call `ctx.git.branch.update_local_ref(repo_root, branch, target_sha)` directly and return
3. **Early return**: if `local_sha == target_sha`, return immediately (already in sync)
4. **Checked out, dirty worktree**: print error and `raise SystemExit(1)` — refuses to reset with uncommitted changes
5. **Checked out, clean**: call `ctx.git.branch.reset_hard(checked_out_path, target_sha)` to atomically sync ref + index + working tree

## Error Pattern

Dirty worktree errors use `SystemExit(1)` (not exceptions), consistent with other dispatch error paths:

```python
if ctx.git.status.has_uncommitted_changes(checked_out_path):
    user_output(click.style("Error: ", fg="red") + f"Branch '{branch}' is checked out at ...")
    raise SystemExit(1)
```

## Distinction from `ensure_trunk_synced`

| Function              | Use Case                                    | Requires                     |
| --------------------- | ------------------------------------------- | ---------------------------- |
| `sync_branch_to_sha`  | Move branch to a known target SHA           | Known remote SHA             |
| `ensure_trunk_synced` | Fetch + sync trunk with divergence checking | Internet (fetch from remote) |

`ensure_trunk_synced` performs merge-base analysis to distinguish fast-forward, ahead, and diverged states. `sync_branch_to_sha` assumes the caller already has the target SHA.

## Call Sites

4 verified call sites across dispatch and checkout commands:

| File                                                        | Line | Context                                          |
| ----------------------------------------------------------- | ---- | ------------------------------------------------ |
| `src/erk/cli/commands/pr/dispatch_cmd.py`                   | 237  | Sync PR branch to remote SHA before dispatch     |
| `src/erk/cli/commands/exec/scripts/incremental_dispatch.py` | 113  | Sync branch before committing impl-context files |
| `src/erk/cli/commands/branch/checkout_cmd.py`               | 430  | Sync parent branch to remote SHA on checkout     |
| `src/erk/cli/commands/pr/checkout_cmd.py`                   | 269  | Sync base branch to remote SHA on PR checkout    |

## Related Documentation

- [Git Plumbing Patterns](git-plumbing-patterns.md) — broader context on ref update patterns
- [Incremental Dispatch](../planning/incremental-dispatch.md) — uses sync_branch_to_sha at line 113
