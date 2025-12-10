---
title: Git and Graphite Edge Cases Catalog
read_when:
  - "debugging unexpected git/gt behavior"
  - "handling rebase/restack edge cases"
  - "writing conflict detection logic"
  - "troubleshooting detached HEAD states"
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

**Location in Codebase**: `packages/erk-shared/src/erk_shared/integrations/gt/operations/restack_finalize.py`

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

**Location in Codebase**: `packages/erk-shared/src/erk_shared/integrations/gt/operations/restack_finalize.py`

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

## Adding New Quirks

When you discover a new edge case, add it to this document with:

- **Surprising Behavior**: What you expected vs what happened
- **Why It's Surprising**: The assumption that was violated
- **Detection Pattern**: Code to detect/handle this case
- **Location in Codebase**: Where the fix/workaround lives

## Related Documentation

- [Three-Phase Restack Architecture](restack-operations.md)
- [Erk Architecture Patterns](erk-architecture.md)
