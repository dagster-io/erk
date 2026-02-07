---
title: Git and Graphite Edge Cases Catalog
last_audited: "2026-02-07 13:52 PT"
audit_result: edited
read_when:
  - "debugging unexpected git/gt behavior"
  - "handling rebase/restack edge cases"
  - "writing conflict detection logic"
  - "troubleshooting detached HEAD states"
  - "handling concurrent worktree operations"
  - "understanding worktree lock files"
tripwires:
  - action: "calling gt commands without --no-interactive flag"
    warning: "Always use `--no-interactive` with gt commands (gt sync, gt submit, gt restack, etc.). Without this flag, gt may prompt for user input and hang indefinitely. Note: `--force` does NOT prevent prompts - you must use `--no-interactive` separately."
  - action: "calling graphite.track_branch() with a remote ref like origin/main"
    warning: "Graphite's `gt track` only accepts local branch names, not remote refs. Use BranchManager.create_branch() which normalizes refs automatically, or strip `origin/` prefix before calling track_branch()."
---

# Git and Graphite Edge Cases Catalog

This document catalogs surprising edge cases and quirks discovered when working with git and Graphite (gt). Each entry includes the discovery context, the surprising behavior, and the workaround.

## Rebase Cleanup Without Completion (Issue #2844)

**Surprising Behavior**: When `gt continue` runs after conflict resolution but conflicts weren't fully resolved, the rebase-merge directory gets cleaned up BUT:

- `is_rebase_in_progress()` returns `False` (no `.git/rebase-merge` or `.git/rebase-apply` dirs)
- `is_worktree_clean()` returns `False` (unmerged files still exist)
- HEAD becomes detached (pointing to commit hash, not branch)

**Why It's Surprising**: One might assume that if `.git/rebase-merge/` doesn't exist, the rebase either completed successfully or was aborted. This is NOT true - it can be in a "half-finished" broken state.

**Detection Pattern**: Don't assume no rebase dirs means clean state. After checking `git.rebase.is_rebase_in_progress(cwd)`, also check for unmerged files via `git.status.get_conflicted_files(cwd)`.

See `GitRebaseOps.is_rebase_in_progress()` in `packages/erk-shared/src/erk_shared/gateway/git/rebase_ops/` and `GitStatusOps.get_conflicted_files()` in `packages/erk-shared/src/erk_shared/gateway/git/status_ops/` for the current implementations.

## Transient Dirty State After Rebase

**Surprising Behavior**: After `gt restack --no-interactive` completes, there can be a brief window where `is_worktree_clean()` returns `False` due to:

- Graphite metadata files being written/cleaned up
- Git rebase temp files not yet removed
- File system sync delays

**Workaround**: Retry with brief delay (100ms) using `context.time.sleep(0.1)` before failing. Check `git.worktree.is_worktree_clean(cwd)` again after the delay to distinguish transient from real dirty state.

## Unmerged File Status Codes

**Reference**: Git status porcelain format for unmerged files

| Code | Meaning                                |
| ---- | -------------------------------------- |
| `UU` | Both modified (classic merge conflict) |
| `AA` | Both added                             |
| `DD` | Both deleted                           |
| `AU` | Added by us, unmerged                  |
| `UA` | Added by them, unmerged                |
| `DU` | Deleted by us, unmerged                |
| `UD` | Deleted by them, unmerged              |

All indicate files needing manual resolution before the rebase can continue.

## Detached HEAD Detection

**Pattern**: To check if HEAD is detached, use `git symbolic-ref -q HEAD` (returns non-zero exit code when detached). This is more explicit than `git rev-parse --abbrev-ref HEAD` which returns the literal string "HEAD" when detached. See `GitBranchOps` in `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/` for erk's branch query operations.

## Git Index Lock and Worktree Concurrency

**Background**: Git's index and `index.lock` are **per-worktree**, not repository-wide. Each worktree has its own index stored in its admin directory (e.g., `.git/worktrees/<id>/index`).

**What IS shared across worktrees:**

- Objects (the object database)
- Refs (branch pointers, tags)
- Ref lockfiles (e.g., when updating the same branch from multiple worktrees)

**What is NOT shared:**

- Index and index.lock (each worktree has its own)
- HEAD (each worktree tracks its own checked-out branch)
- Other per-worktree files

**Gitfile Indirection**: Linked worktrees use gitfile indirection (not sparse checkout):

- Each worktree has `.git` as a **file** (not a directory)
- The file contains: `gitdir: /main/repo/.git/worktrees/<name>`
- The worktree's admin directory contains `index`, `HEAD`, and a `commondir` file pointing to the shared repo

**Robust Lock File Resolution**: Use `git rev-parse --git-path index.lock` to let Git resolve the lock path correctly for any repository layout (normal repos, linked worktrees, custom `$GIT_DIR`). See `get_lock_path()` and `wait_for_index_lock()` in `packages/erk-shared/src/erk_shared/gateway/git/lock.py` for the production implementation.

**Anti-Pattern**: Don't manually parse `.git` files and compute paths with `parent.parent`. The worktree admin directory structure can vary, and Git uses `commondir` files for indirection.

**When to Use**: Apply lock-waiting to operations that modify the index (`checkout`, `add`, `commit`, `reset`, etc.) when running concurrent git commands in the same worktree or when updating shared refs across worktrees.

## Graphite Interactive Mode Hangs

**Surprising Behavior**: Running `gt sync`, `gt submit`, `gt restack`, or other gt commands without the `--no-interactive` flag can cause the command to hang indefinitely when run from Claude Code sessions or other non-interactive contexts.

**Why It's Surprising**: The command appears to be doing nothing - no output, no error, just silence. The underlying cause is that gt is waiting for user input at a prompt that isn't visible.

**Solution**: Always use `--no-interactive` flag with gt commands:

```bash
# WRONG - may hang waiting for user input
gt sync
gt submit
gt submit --force  # --force does NOT prevent prompts!

# CORRECT - never prompts, fails fast if interaction needed
gt sync --no-interactive
gt submit --no-interactive
gt submit --force --no-interactive
gt restack --no-interactive
```

**Important**: The `--force` flag does NOT prevent interactive prompts. You must use `--no-interactive` separately. The `--force` flag only skips confirmation for destructive operations, but gt may still prompt for other decisions (like whether to include upstack branches).

**Common Scenarios Where gt Prompts**:

- `gt sync` prompts to delete merged branches
- `gt submit` prompts to confirm PR creation/update
- `gt restack` prompts during conflict resolution
- Various commands prompt when state is ambiguous

**Implementation Reference**: This pattern is used throughout the Graphite gateway in `packages/erk-shared/src/erk_shared/gateway/graphite/real.py`.

## Graphite track_branch Remote Ref Limitation

**Surprising Behavior**: Graphite's `gt track --parent <branch>` command **only accepts local branch names** (e.g., `main`), not remote refs (e.g., `origin/main`). Git commands like `git branch` and `git checkout` accept both transparently, but Graphite will reject remote refs or create incorrect parent relationships.

**Why It's Surprising**: Git and Graphite are often used together, and Git's flexibility with branch references creates an expectation that Graphite would also accept remote refs. The error messages from Graphite don't clearly indicate that the issue is the `origin/` prefix.

**Solution**: `GraphiteBranchManager.create_branch()` normalizes branch names with `base_branch.removeprefix("origin/")` before calling `graphite_branch_ops.track_branch()`. It also handles divergence detection and re-tracking. See the full implementation in `packages/erk-shared/src/erk_shared/gateway/branch_manager/graphite.py`.

**Design Pattern**: Tool quirks should be absorbed at abstraction boundaries. Callers (like the submit command) don't need to know about Graphite's limitations -- they can pass remote refs freely and trust `BranchManager` to handle normalization.

**Anti-Pattern**: Calling `graphite_branch_ops.track_branch()` directly with user-provided branch names that might contain `origin/` prefix.

## Adding New Quirks

When you discover a new edge case, add it to this document with:

- **Surprising Behavior**: What you expected vs what happened
- **Why It's Surprising**: The assumption that was violated
- **Detection Pattern**: Code to detect/handle this case
- **Location in Codebase**: Where the fix/workaround lives

## Related Documentation

- [Erk Architecture Patterns](erk-architecture.md)
