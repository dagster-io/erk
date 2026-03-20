---
title: Stack Sync Command
read_when:
  - "working with erk stack sync"
  - "syncing stack branches with remote"
  - "implementing or testing stack-wide divergence resolution"
tripwires:
  - action: "expecting erk stack sync to be user-visible in help output"
    warning: "erk stack sync is a hidden command (hidden=True). It does not appear in `erk stack --help`. It is primarily used internally by CI workflows and automation."
  - action: "running erk stack sync without Graphite"
    warning: "erk stack sync uses GraphiteCommand and requires gt to be installed and configured. If the branch is not tracked by Graphite, the command exits with an error."
---

# Stack Sync Command

`erk stack sync` syncs all branches in the current Graphite stack with their remote tracking branches. It is a **hidden command** not shown in `erk stack --help`.

## Source

- CLI: `src/erk/cli/commands/stack/sync_cmd.py`
- Core logic: `src/erk/core/stack_sync.py`

## What It Does

Performs stack-wide divergence resolution in 5 phases:

1. **Get stack** — Reads the full Graphite stack for the current branch
2. **Bulk fetch** — Runs `git fetch --prune origin` once for all branches
3. **Per-branch sync** — Processes each non-trunk branch bottom-to-top
4. **Re-track fixed branches** — Re-registers fast-forwarded/rebased branches with Graphite
5. **Restack** — Runs `gt restack` on the entire stack

## Per-Branch Sync Actions

For each branch, the sync determines what to do based on divergence state:

| `BranchSyncAction`       | Meaning             | When                                                   |
| ------------------------ | ------------------- | ------------------------------------------------------ |
| `ALREADY_SYNCED`         | No action needed    | Local matches remote, or local is ahead only           |
| `FAST_FORWARDED`         | Updated to remote   | Local is behind only                                   |
| `REBASED`                | Rebased onto remote | Local diverged (ahead and behind)                      |
| `SKIPPED_NO_REMOTE`      | Skipped             | No remote tracking branch exists                       |
| `SKIPPED_OTHER_WORKTREE` | Skipped             | Branch is checked out in another worktree              |
| `CONFLICT`               | Aborted rebase      | Rebase had conflicts; rebase was automatically aborted |
| `ERROR`                  | Failure             | Unexpected error (e.g., could not resolve remote ref)  |

## Output Format

```
Fetching remote state...

  feature/a             already in sync
  feature/b             fast-forwarded (3 behind)
  feature/c             CONFLICT — run: erk pr diverge-fix
  feature/d             skipped (no remote)

Restacking... done

Stack synced: 1 fixed, 1 in sync, 1 conflict, 1 skipped
```

## Conflict Handling

When a rebase conflict is detected:

1. The rebase is **automatically aborted** (no in-progress rebase is left behind)
2. The branch is reported as `CONFLICT`
3. The summary line includes the conflict count
4. The suggested resolution is `erk pr diverge-fix` for that specific branch

## Error Conditions

Fatal errors (non-zero exit) occur when:

- The current branch is in detached HEAD state
- The current branch is not tracked by Graphite

Non-fatal errors (still exits 0) are reported per-branch with `ERROR` action.

## Worktree Awareness

Before attempting to sync a branch, the command checks whether the branch is checked out in another worktree. If it is, the branch is skipped with `SKIPPED_OTHER_WORKTREE`. The current branch is always eligible for sync (not skipped even if checked out).

## Requirements

- Requires `gt` (Graphite CLI) — registered as `cls=GraphiteCommand`
- Requires a current branch tracked by Graphite

## Related Documentation

- [Rebase Conflict Patterns](../architecture/rebase-conflict-patterns.md) — Conflict detection and resolution
- [PR Diverge-Fix](../cli/commands/pr-diverge-fix.md) — Single-branch divergence fix
