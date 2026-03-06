---
title: erk reconcile Command
read_when:
  - "cleaning up branches whose PRs have been merged"
  - "reconciling branches merged outside erk land"
  - "working with erk reconcile"
tripwires:
  - action: "manually deleting branches that were merged via GitHub web UI"
    warning: "Use erk reconcile instead. It handles the full lifecycle: learn PR creation, objective updates, slot cleanup, branch deletion, and worktree removal."
---

# erk reconcile Command

Detects and cleans up branches whose PRs have been merged outside of `erk land` (e.g., via GitHub web UI merge).

## Usage

```bash
erk reconcile               # Interactive — shows candidates, asks for confirmation
erk reconcile --force       # Skip confirmation prompt
erk reconcile --dry-run     # Preview candidates without processing
erk reconcile --skip-learn  # Skip learn PR creation step
```

## Implementation

- **Command:** `src/erk/cli/commands/reconcile_cmd.py` (173 lines)
- **Pipeline:** `src/erk/cli/commands/reconcile_pipeline.py` (248 lines)

### Detection Pipeline

1. `fetch_prune` — fetch with prune to detect gone remotes
2. Filter branches where `gone=True` in `BranchSyncInfo`
3. Exclude trunk branch
4. Check PR state via GitHub — must be MERGED
5. Resolve metadata: plan ID, objective number, worktree path

### Processing Pipeline (Fail-Open)

Each step can fail independently without blocking subsequent steps:

1. **Learn PR creation** — creates erk-learn PR for documentation extraction
2. **Objective update** — updates parent objective if linked
3. **Cleanup** — unassign slot, delete branch, remove worktree

### Cleanup Steps

1. Unassign slot from worktree pool
2. Ensure branch is not checked out anywhere
3. Delete branch (force)
4. Remove worktree if linked (not root) and prune remaining worktrees

## Git Layer Extensions

The `gone` field on `BranchSyncInfo` and `fetch_prune` method were added across 5 gateway implementations to support reconciliation detection.

## History

Renamed from `reconcile-with-remote` to `reconcile` (with `diverge-fix` separated into its own command). 16 files were updated in the rename.

## Related Documentation

- [Worktree Cleanup](../../planning/worktree-cleanup.md) — worktree lifecycle management
- [erk pr diverge-fix Command](pr-diverge-fix.md) — branch divergence resolution (split from original reconcile)
