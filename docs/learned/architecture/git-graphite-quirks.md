---
title: Git and Graphite Edge Cases Catalog
read_when:
  - "debugging unexpected git/gt behavior"
  - "handling rebase/restack edge cases"
  - "writing conflict detection logic"
  - "troubleshooting detached HEAD states"
  - "handling concurrent worktree operations"
  - "understanding worktree lock files"
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

## Adding New Quirks

When you discover a new edge case, add it to this document with:

- **Surprising Behavior**: What you expected vs what happened
- **Why It's Surprising**: The assumption that was violated
- **Detection Pattern**: Code to detect/handle this case
- **Location in Codebase**: Where the fix/workaround lives

## Related Documentation

- [Three-Phase Restack Architecture](restack-operations.md)
- [Erk Architecture Patterns](erk-architecture.md)
