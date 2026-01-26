---
title: Multi-Worktree State Handling
read_when:
  - "checkout operations in multi-worktree repositories"
  - "landing PRs with worktree cleanup"
  - "understanding git single-checkout constraint"
  - "debugging checkout failures across worktrees"
tripwires:
  - action: "calling checkout_branch() in a multi-worktree repository"
    warning: "Verify the target branch is not already checked out in another worktree using `git.worktree.find_worktree_for_branch()`. Git enforces a single-checkout constraint - attempting to checkout a branch held elsewhere causes silent state corruption or unexpected failures."
---

# Multi-Worktree State Handling

This document covers patterns for safe branch operations in repositories with multiple worktrees.

## The Single-Checkout Constraint

Git enforces a fundamental rule: **a branch can only be checked out in one worktree at a time**. Attempting to checkout a branch that's already checked out elsewhere will fail.

This constraint catches operations like:

```bash
# In worktree A (on master)
git checkout feature-branch  # Fails if feature-branch is checked out in worktree B
```

## Query Before Action Pattern

Before performing a checkout, verify the target branch is available:

```python
# Check if branch is held by another worktree
worktree = ctx.git.worktree.find_worktree_for_branch(repo_root, target_branch)

if worktree is not None:
    # Branch is checked out elsewhere
    user_warning(f"Cannot checkout {target_branch}: held by worktree at {worktree.path}")
    return
```

The `find_worktree_for_branch()` method returns the `WorktreeInfo` if the branch is checked out in any worktree, or `None` if available.

## Conditional Execution Pattern

Use query results to decide the operation:

```python
def checkout_or_skip(ctx: ErkContext, repo_root: Path, branch: str) -> bool:
    """Checkout branch if available, skip if held elsewhere."""
    worktree = ctx.git.worktree.find_worktree_for_branch(repo_root, branch)

    if worktree is not None:
        # Not an error - just can't checkout here
        return False

    ctx.branch_manager.checkout_branch(repo_root, branch)
    return True
```

## Example: Land Command Cleanup

The `erk pr land` command demonstrates this pattern. After landing a PR:

1. Delete the feature branch
2. Try to checkout trunk (master)
3. Handle the case where trunk is held by another worktree

```python
# After landing and deleting feature branch
trunk_worktree = ctx.git.worktree.find_worktree_for_branch(repo_root, "master")

if trunk_worktree is not None:
    # Trunk is held elsewhere - leave HEAD detached
    user_output(f"Trunk (master) is checked out in: {trunk_worktree.path}")
    user_output("Worktree is now in detached HEAD state")
else:
    # Safe to checkout trunk
    ctx.branch_manager.checkout_branch(repo_root, "master")
```

## Anti-Patterns

### Assuming checkout will succeed

```python
# WRONG: No check before checkout
ctx.branch_manager.checkout_branch(repo_root, "master")  # May fail!
```

### Catching errors instead of querying

```python
# WRONG: Exception-based control flow
try:
    ctx.branch_manager.checkout_branch(repo_root, "master")
except GitError:
    # Now what? We don't know WHY it failed
    pass
```

### Ignoring detached HEAD state

```python
# WRONG: Not handling the skip case
if not checkout_or_skip(ctx, repo_root, "master"):
    # Silently continue with detached HEAD - user is confused
    pass
```

## Expected States After Operations

| Scenario                    | Trunk Available | Worktree State       |
| --------------------------- | --------------- | -------------------- |
| Land from non-root worktree | Yes             | Checked out on trunk |
| Land from non-root worktree | No              | Detached HEAD        |
| Land from root worktree     | Always Yes      | Checked out on trunk |

When trunk is unavailable, the worktree enters detached HEAD state. This is expected behavior, not an error.

## Recovering from Detached HEAD

When a worktree is in detached HEAD after a land operation:

```bash
# Check current state
git status  # Shows "HEAD detached at ..."

# Option 1: Checkout any available branch
git checkout other-branch

# Option 2: Create a new branch from HEAD
git checkout -b new-feature

# Option 3: Leave as-is (valid for temporary work)
```

## Related Documentation

- [Branch Cleanup Guide](../erk/branch-cleanup.md) - Cleaning up branches and worktrees
- [Git and Graphite Edge Cases](git-graphite-quirks.md) - Other git/gt quirks
- [Erk Architecture Patterns](erk-architecture.md) - Core architecture patterns
