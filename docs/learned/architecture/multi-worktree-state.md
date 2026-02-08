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

## The Core Constraint

Git enforces a fundamental invariant: **a branch can only be checked out in one worktree at a time**. This is not a configuration option or a safety feature that can be disabled—it's part of git's core state management. Attempting to checkout a branch that's already active elsewhere fails with an error.

This constraint exists because a branch ref points to exactly one HEAD. Two worktrees can't both be "on branch X" because there's no way to represent which worktree's commits should advance the branch.

## Why LBYL Is Required

Most of erk's codebase avoids checking conditions before operations (LBYL), relying on explicit return types to surface failure modes. Multi-worktree checkout operations are an exception. The single-checkout constraint means:

1. **Checkout failures are ambiguous** — git returns non-zero exit code for many reasons (invalid branch, already checked out, uncommitted changes)
2. **Post-failure state is unclear** — after a failed checkout, you don't know if the branch exists, where it's checked out, or if it's safe to retry
3. **Defensive operations require precise decisions** — when landing a PR, you need to know "is trunk available for checkout?" before deciding between checkout vs detached HEAD

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/worktree/abc.py, Worktree.find_worktree_for_branch -->

The solution: Query first with `Worktree.find_worktree_for_branch()`, which returns `Path | None` indicating where the branch is checked out. This makes the constraint explicit in the type system.

## Decision Tables by Operation

### PR Landing Cleanup

After landing a PR, erk deletes the feature branch and attempts to leave the worktree in a valid state:

| Trunk Available? | Result State           | Rationale                                                |
| ---------------- | ---------------------- | -------------------------------------------------------- |
| Yes              | Checked out on trunk   | Normal case - worktree remains usable                    |
| No               | Detached HEAD at trunk | Trunk held elsewhere - detached HEAD is valid git state  |
| (error)          | Unchanged              | Defensive check failed - abort rather than corrupt state |

<!-- Source: src/erk/cli/commands/land_cmd.py, _cleanup_non_slot_worktree -->

See `_cleanup_non_slot_worktree()` in `src/erk/cli/commands/land_cmd.py` for the implementation. The key insight: detached HEAD is not an error condition—it's the correct outcome when trunk is unavailable.

### Checkout Command Navigation

When checking out a branch that's already in a worktree:

| Branch Location          | Action                     | Why Not Checkout?                           |
| ------------------------ | -------------------------- | ------------------------------------------- |
| Current worktree         | No-op (already there)      | Branch is already checked out here          |
| Different worktree       | Navigate to that worktree  | Can't checkout (single-checkout constraint) |
| Not checked out anywhere | Create worktree + checkout | Safe to checkout                            |

<!-- Source: src/erk/cli/commands/checkout_helpers.py, ensure_branch_has_worktree -->

See `ensure_branch_has_worktree()` in `src/erk/cli/commands/checkout_helpers.py`. The navigation strategy preserves the constraint—if a branch exists in worktree A, opening it in worktree B means navigating to A, not checking out in B.

## Anti-Patterns

### WRONG: Try checkout and catch errors

```python
# DON'T DO THIS - failure reason is ambiguous
try:
    ctx.branch_manager.checkout_branch(repo_root, "master")
except RuntimeError:
    # Why did it fail? Invalid branch? Already checked out? Uncommitted changes?
    pass
```

This violates LBYL and provides no path to recovery. The error message from git doesn't distinguish "already checked out" from "branch doesn't exist."

### WRONG: Assume checkout will succeed

```python
# DON'T DO THIS - silently fails when trunk is held elsewhere
ctx.branch_manager.delete_branch(repo_root, feature_branch)
ctx.branch_manager.checkout_branch(repo_root, "master")  # May fail!
```

If trunk is checked out in the root worktree and you're in a slot worktree, this leaves you in detached HEAD with no explanation.

### CORRECT: Query then decide

```python
# Query first
trunk_worktree = ctx.git.worktree.find_worktree_for_branch(repo_root, "master")

if trunk_worktree is None:
    # Trunk is available - safe to checkout
    ctx.branch_manager.checkout_branch(repo_root, "master")
else:
    # Trunk is held elsewhere - checkout detached HEAD instead
    ctx.branch_manager.checkout_detached(repo_root, "master")
    user_output(f"Trunk held by {trunk_worktree} - left in detached HEAD")
```

The query result drives the decision. If trunk is unavailable, detached HEAD is the fallback strategy, not an error.

## Defensive Branch Deletion

Git refuses to delete a branch that's checked out in any worktree. This interacts poorly with stale pool state—if pool.json records worktree path A but the branch is actually in worktree B, deletion fails.

<!-- Source: src/erk/cli/commands/land_cmd.py, _ensure_branch_not_checked_out -->

The defensive pattern in `_ensure_branch_not_checked_out()`:

1. Query where the branch is checked out (ignore pool state)
2. If checked out anywhere, checkout detached HEAD there first
3. Verify branch is released (query again)
4. Delete branch (now safe)

This recovers from stale state by trusting git's live worktree list over pool.json.

## Recovering from Detached HEAD

Detached HEAD is a valid worktree state, not an error. Users can:

- **Checkout any available branch** — returns to normal branch state
- **Create a new branch** — `git checkout -b new-feature` keeps current commits
- **Leave as-is** — detached HEAD supports normal git operations (commit, fetch, etc.)

The important insight: erk doesn't "fix" detached HEAD automatically because it's not broken. It's the correct fallback when the desired branch is unavailable.

## Related Documentation

- [Branch Cleanup Guide](../erk/branch-cleanup.md) — Slot cleanup and branch deletion workflows
- [Git and Graphite Edge Cases](git-graphite-quirks.md) — Other git state constraints
