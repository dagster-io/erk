---
title: Force Flag Design in Branch Operations
read_when:
  - "adding force parameter to branch mutation methods"
  - "understanding when force-update is safe"
  - "implementing auto-fix patterns for branch divergence"
---

# Force Flag Design in Branch Operations

Force flags in erk's branch operations exist for **internal optimization**, not external API exposure. This document explains the design, safety properties, and implementation pattern.

## Design Principle: Internal vs External APIs

| Layer                  | Force Flag? | Reason                                              |
| ---------------------- | ----------- | --------------------------------------------------- |
| BranchManager (public) | No          | Callers shouldn't decide when to force              |
| GitBranchOps (internal)| Yes         | BranchManager implementations decide when to force  |

The abstraction boundary protects callers from making dangerous force decisions while enabling internal optimizations.

## When Force-Update is Safe

Force-updating a branch is safe when:

1. **The worktree is on a different branch** - You're not on the branch being force-updated
2. **The branch state is recoverable** - Remote has the authoritative state
3. **The operation context guarantees both** - e.g., after creating a child branch from remote

### Example: Auto-fixing Diverged Parent Branches

When creating a new Graphite-tracked branch from a remote parent, if the local parent branch has diverged from its remote counterpart, the system needs to sync them:

```
Scenario:
  1. User has local branch "feature-parent"
  2. Creates new Graphite-tracked branch "feature-parent/child" from "origin/feature-parent"
  3. Problem: local "feature-parent" has commits not on "origin/feature-parent"
  4. Graphite requires local parent to be an ancestor of remote

Solution: Force-update is safe because:
  - We already created and checked out "feature-parent/child"
  - We're NOT on "feature-parent" (we're on the child)
  - "origin/feature-parent" has the authoritative state
  - Local commits are recoverable via reflog
```

## Implementation Across 5 Files

When adding a force parameter (or any parameter) to a gateway method, implement in all 5 places:

### 1. ABC Definition (abc.py)

Add to abstract method signature with keyword-only marker:

```
packages/erk-shared/src/erk_shared/git/branch_ops/abc.py
```

### 2. Real Implementation (real.py)

Pass force flag to subprocess command:

```
packages/erk-shared/src/erk_shared/git/branch_ops/real.py
```

### 3. Fake Implementation (fake.py)

Record force flag in mutation tracking tuple. This enables tests to assert on whether force was used:

```
packages/erk-shared/src/erk_shared/git/branch_ops/fake.py
```

### 4. Dry-Run Wrapper (dry_run.py)

No-op in dry-run mode (don't execute force):

```
packages/erk-shared/src/erk_shared/git/branch_ops/dry_run.py
```

### 5. Printing Wrapper (printing.py)

Delegate to wrapped implementation:

```
packages/erk-shared/src/erk_shared/git/branch_ops/printing.py
```

For concrete code examples, see [Gateway ABC Implementation Checklist](gateway-abc-implementation.md#concrete-example-adding-a-parameter-to-an-existing-method).

## Caller Responsibilities

All callers (BranchManager implementations) must decide when to use force:

- **Default: force=False** for normal branch creation (safe, explicit intent)
- **Use force=True only when:**
  - You've already verified worktree is on a different branch
  - Remote is authoritative state
  - Divergence is expected and handled

## Related Documentation

- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) - 5-file pattern details
- [Git and Graphite Edge Cases](git-graphite-quirks.md) - Branch divergence scenarios
- [Mutation Tracking Test Patterns](../testing/mutation-tracking-patterns.md) - Testing force flag behavior
