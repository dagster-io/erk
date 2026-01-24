---
title: Git and Graphite Edge Cases Catalog
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
  - action: "using `gt restack` to resolve branch divergence errors"
    warning: "gt restack only handles parent-child stack rebasing, NOT same-branch remote divergence. Use git rebase origin/$BRANCH first."
---

# Git and Graphite Edge Cases Catalog

This document catalogs surprising edge cases and quirks discovered when working with git and Graphite (gt). Each entry includes the discovery context, the surprising behavior, and the workaround.

## Rebase Cleanup Without Completion (Issue #2844)

**Surprising Behavior**: When `gt continue` runs after conflict resolution but conflicts weren't fully resolved, the rebase-merge directory gets cleaned up BUT:

- `is_rebase_in_progress()` returns `False` (no `.git/rebase-merge` or `.git/rebase-apply` dirs)
- `is_worktree_clean()` returns `False` (unmerged files still exist)
- HEAD becomes detached (pointing to commit hash, not branch)

**Why It's Surprising**: One might assume that if `.git/rebase-merge/` doesn't exist, the rebase either completed successfully or was aborted. This is NOT true - it can be in a "half-finished" broken state.

**Detection Pattern**:

```python
# WRONG: Assuming no rebase dirs = clean state
if not ops.git.is_rebase_in_progress(cwd):
    # Might still have unmerged files!
    pass

# CORRECT: Check for unmerged files explicitly
status_result = subprocess.run(
    ["git", "-C", str(cwd), "status", "--porcelain"],
    capture_output=True, text=True, check=False,
)
unmerged_prefixes = ("UU", "AA", "DD", "AU", "UA", "DU", "UD")
unmerged_files = [
    line[3:] for line in status_lines if line[:2] in unmerged_prefixes
]
```

**Location in Codebase**: `packages/erk-shared/src/erk_shared/gateway/gt/operations/restack_finalize.py`

## Transient Dirty State After Rebase

**Surprising Behavior**: After `gt restack --no-interactive` completes, there can be a brief window where `is_worktree_clean()` returns `False` due to:

- Graphite metadata files being written/cleaned up
- Git rebase temp files not yet removed
- File system sync delays

**Workaround**: Retry with brief delay (100ms) before failing.

```python
if not ops.git.is_worktree_clean(cwd):
    ops.time.sleep(0.1)  # Brief delay for transient files
    if not ops.git.is_worktree_clean(cwd):
        # Now it's actually dirty
        yield CompletionEvent(RestackFinalizeError(...))
```

**Location in Codebase**: `packages/erk-shared/src/erk_shared/gateway/gt/operations/restack_finalize.py`

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

**Pattern**: Check if HEAD is detached (not pointing to a branch):

```python
symbolic_result = subprocess.run(
    ["git", "-C", str(cwd), "symbolic-ref", "-q", "HEAD"],
    capture_output=True, text=True, check=False,
)
is_detached = symbolic_result.returncode != 0
```

`git rev-parse --abbrev-ref HEAD` returns "HEAD" when detached, but using `symbolic-ref` is more explicit.

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

**Robust Lock File Resolution**:

Use `git rev-parse --git-path` to let Git resolve paths correctly for any layout:

```python
import subprocess
from pathlib import Path

def git_path(repo_root: Path, rel: str) -> Path:
    """Let Git resolve the correct path for this worktree."""
    out = subprocess.check_output(
        ["git", "-C", str(repo_root), "rev-parse", "--git-path", rel],
        text=True,
    ).strip()
    return Path(out)

def wait_for_index_lock(repo_root: Path, time: Time, *, max_wait_seconds: float = 5.0) -> bool:
    """Wait for index.lock to be released."""
    lock_file = git_path(repo_root, "index.lock")
    elapsed = 0.0
    while lock_file.exists() and elapsed < max_wait_seconds:
        time.sleep(0.5)
        elapsed += 0.5
    return not lock_file.exists()
```

This handles all cases:

- Normal repos (`.git` directory)
- Linked worktrees (`.git` file → per-worktree admin dir)
- Uncommon layouts (`$GIT_DIR`, `$GIT_COMMON_DIR`)

**Anti-Pattern**: Don't manually parse `.git` files and compute paths with `parent.parent`. The worktree admin directory structure can vary, and Git uses `commondir` files for indirection.

**When to Use**: Apply lock-waiting to operations that modify the index (`checkout`, `add`, `commit`, `reset`, etc.) when running concurrent git commands in the same worktree or when updating shared refs across worktrees.

**Implementation Reference**: `packages/erk-shared/src/erk_shared/git/lock.py`

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

**Solution**: The `BranchManager.create_branch()` method in `GraphiteBranchManager` normalizes branch names before calling `graphite.track_branch()`:

```python
def create_branch(
    self,
    repo_root: Path,
    branch_name: str,
    base_branch: str,
) -> None:
    self.git.create_branch(repo_root, branch_name, base_branch)
    # Graphite's `gt track` only accepts local branch names, not remote refs
    parent_for_graphite = base_branch.removeprefix("origin/")
    self.graphite.track_branch(repo_root, branch_name, parent_for_graphite)
```

**Design Pattern**: Tool quirks should be absorbed at abstraction boundaries. Callers (like the submit command) don't need to know about Graphite's limitations—they can pass remote refs freely and trust `BranchManager` to handle normalization.

**Anti-Pattern**: Calling `graphite.track_branch()` directly with user-provided branch names that might contain `origin/` prefix.

**Location in Codebase**: `packages/erk-shared/src/erk_shared/branch_manager/graphite.py`

## Parent Branch Divergence Detection

**Surprising Behavior**: When creating a new branch from a remote ref (e.g., `origin/feature-parent`) and the corresponding local branch `feature-parent` exists but has different commits, Graphite's `gt track` can succeed but create an invalid stack relationship (local parent is not an ancestor of the child).

**Why It's Surprising**: Git handles remote vs local refs transparently - creating branches from either just works. Graphite's stack tracking requires the local parent branch to be an ancestor of the new branch, which fails silently if local has diverged from remote.

**Solution**: The `GraphiteBranchManager.create_branch()` method validates parent branch state via `_ensure_local_matches_remote()`:

1. If local branch doesn't exist, create it from remote
2. If local exists and matches remote, proceed normally
3. If local has diverged from remote, fail with clear fix instructions

**Error Message**:

```
Local branch 'feature-parent' has diverged from origin/feature-parent.
Graphite requires the local branch to match the remote for stack tracking.

To fix, update your local branch to match remote and restack:
  git fetch origin && git branch -f feature-parent origin/feature-parent
  gt restack --downstack

Or if you have local changes to keep, push them first:
  With Graphite: gt checkout feature-parent && gt submit
  With git:      git checkout feature-parent && git push origin feature-parent
```

**When This Happens**:

- User has local commits on parent branch not yet pushed
- Parent branch was rebased/amended remotely
- `gt sync` was not run after another user pushed to parent

**Location in Codebase**: `packages/erk-shared/src/erk_shared/branch_manager/graphite.py` - `_ensure_local_matches_remote()` method

## Branch Restoration After Graphite Tracking

**Surprising Behavior**: Graphite's `gt track` command requires the branch to be checked out. After tracking, the original branch is not automatically restored.

**Why It's Surprising**: Most git operations don't require checkout, and callers expect `create_branch()` to not change the current branch.

**Solution**: `GraphiteBranchManager.create_branch()` saves and restores the current branch:

1. Save current branch before operations
2. Create and checkout new branch
3. Track with Graphite
4. Checkout original branch

This ensures callers can create multiple branches without unexpected working directory changes.

**Location in Codebase**: `packages/erk-shared/src/erk_shared/branch_manager/graphite.py`

## RestackError Handling Patterns

`gt restack` can fail in two distinct ways, requiring different user responses:

### Error Types

| Error Type         | Meaning                                              | User Action                                             |
| ------------------ | ---------------------------------------------------- | ------------------------------------------------------- |
| `restack-conflict` | Merge conflicts during rebase                        | Resolve conflicts manually, run `gt restack --continue` |
| `restack-failed`   | Other restack failure (permissions, corrupted state) | Check git status, may need `git rebase --abort`         |

### Code Pattern

```python
from erk_shared.gateway.gt.types import RestackError, RestackSuccess

result = ctx.graphite.restack_idempotent(repo.root, no_interactive=True)

if isinstance(result, RestackError):
    if result.error_type == "restack-conflict":
        # Guide user through conflict resolution
        user_error(f"Conflicts detected: {result.message}")
        user_output("Resolve conflicts and run: gt restack --continue")
    else:
        # Generic failure
        raise click.ClickException(result.message)
```

### Reference

Type definitions: `packages/erk-shared/src/erk_shared/gateway/gt/types.py:26-43`

## Adding New Quirks

When you discover a new edge case, add it to this document with:

- **Surprising Behavior**: What you expected vs what happened
- **Why It's Surprising**: The assumption that was violated
- **Detection Pattern**: Code to detect/handle this case
- **Location in Codebase**: Where the fix/workaround lives

## Related Documentation

- [Three-Phase Restack Architecture](restack-operations.md)
- [Erk Architecture Patterns](erk-architecture.md)
