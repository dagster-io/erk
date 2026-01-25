---
title: Remote Implementation Idempotency
read_when:
  - "implementing remote plan execution"
  - "debugging branch creation in remote workflows"
  - "working with worktree reuse patterns"
tripwires:
  - action: "reusing existing worktrees for remote implementation"
    warning: "Check if worktree already has a branch before creating new one. Reusing worktrees without checking causes PR orphaning."
---

# Remote Implementation Idempotency

Remote implementation must handle worktree reuse safely.

## The Bug (Fixed)

When remote implementation reused an existing worktree:

1. Old branch still existed
2. Code created a NEW branch anyway (e.g., `P77-fix-...-01-25-0611`)
3. Old PR became orphaned (pointed to `P77-fix-...-01-24-2229` with no commits)
4. CI failures on the orphan PR

## The Fix

Before creating a branch, check if the worktree already has one matching the issue:

- **If branch exists and matches plan**: Use it, skip branch creation entirely
- **If branch exists but differs**: Error clearly (don't silently orphan)
- **Only create new branch**: If no matching branch exists

## Detection Pattern

Check if current branch name matches the expected prefix:

```
P{issue_number}-*
```

If already on a matching branch, output the existing branch name and continue with `.impl/` setup.

## User Experience

**Before (buggy):**

```bash
# Remote workflow re-runs with --issue argument
erk exec setup-impl-from-issue 77
# Creates new branch P77-fix-...-01-25-0611
# Orphans existing P77-fix-...-01-24-2229, PR now broken
```

**After (fixed):**

```bash
# Remote workflow re-runs with --issue argument
erk exec setup-impl-from-issue 77
# Output: Already on branch for issue #77: P77-fix-remote-implementation-01-24-2229
# Continues using existing branch, PR preserved
```

## Reference

- Commit: `f9807f2d` - Fix remote implementation workflow reusing existing branch
- Implementation: `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py`

## Related Topics

- [Submit Branch Reuse](submit-branch-reuse.md) - Similar pattern in submit workflow
- [Plan Lifecycle](lifecycle.md) - Full plan lifecycle including remote execution
