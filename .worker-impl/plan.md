# Plan: Graphite Branch Delete Fallback to Git

## Problem

When `erk br delete` fails because Graphite refuses to delete a branch (diverged/untracked), the user must manually run `git branch -D`. This is a poor UX.

**Error scenario:**
```
gt delete -f P4517-... → ERROR: Cannot perform this operation on diverged branch
gt untrack P4517-...   → Branch is not tracked by Graphite
gt delete P4517-...    → ERROR: Cannot perform this operation on untracked branch
git branch -D P4517... → Works!
```

Two failure modes:
1. **Untracked**: Branch not tracked by Graphite
2. **Diverged**: Branch is tracked but local SHA differs from Graphite's cached SHA

## Solution

Add LBYL checks in `GraphiteBranchManager.delete_branch()` to detect when Git fallback is needed.

## Implementation

### File: `packages/erk-shared/src/erk_shared/branch_manager/graphite.py`

Modify `delete_branch()` method (lines 73-80):

```python
def delete_branch(self, repo_root: Path, branch: str) -> None:
    """Delete a branch with Graphite metadata cleanup.

    Falls back to plain git if Graphite can't delete (untracked/diverged).
    """
    # LBYL: Check if Graphite can handle this branch
    if not self._can_graphite_delete(repo_root, branch):
        self.git.delete_branch(repo_root, branch, force=True)
        return

    self.graphite.delete_branch(repo_root, branch)

def _can_graphite_delete(self, repo_root: Path, branch: str) -> bool:
    """Check if Graphite can delete this branch (tracked and not diverged)."""
    # Check 1: Is branch tracked?
    if not self.graphite.is_branch_tracked(repo_root, branch):
        return False

    # Check 2: Is branch diverged?
    branches = self.graphite.get_all_branches(self.git, repo_root)
    if branch in branches:
        graphite_sha = branches[branch].commit_sha
        actual_sha = self.git.get_branch_head(repo_root, branch)
        if graphite_sha is not None and actual_sha is not None and graphite_sha != actual_sha:
            return False

    return True
```

No new Git ABC methods needed - `get_branch_head()` already exists.

## Why LBYL Here

1. `is_branch_tracked()` already exists and is cheap (`gt branch info --quiet`)
2. `get_all_branches()` is already cached in the Graphite gateway
3. Both checks are deterministic - no race condition concerns for delete
4. Follows project conventions: LBYL over try/except for control flow

## Verification

1. Run unit tests: `make test-unit`
2. Manual test: Create a diverged branch scenario and verify `erk br delete` succeeds