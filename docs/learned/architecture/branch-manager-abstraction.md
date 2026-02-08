---
title: BranchManager Abstraction
read_when:
  - "working with branch operations (create, delete, checkout, submit)"
  - "implementing commands that manipulate branches"
  - "understanding the Graphite vs Git mode difference"
  - "debugging branch-related operations"
tripwires:
  - action: "calling ctx.git.branch mutation methods directly (create_branch, delete_branch, checkout_branch, checkout_detached, create_tracking_branch)"
    warning: "Use ctx.branch_manager instead for all user-facing branches. Only use ctx.git.branch directly for ephemeral/placeholder branches that should never be Graphite-tracked. See branch-manager-decision-tree.md."
  - action: "calling ctx.graphite_branch_ops mutation methods directly (track_branch, delete_branch, submit_branch)"
    warning: "Use ctx.branch_manager instead. GraphiteBranchOps is a sub-gateway that BranchManager delegates to internally. Direct calls bypass the dual-mode abstraction."
  - action: "calling create_branch() and assuming you're on the new branch"
    warning: "GraphiteBranchManager.create_branch() restores the original branch after Graphite tracking. Always call branch_manager.checkout_branch() afterward if you need to be on the new branch."
  - action: "calling delete_branch() without passing the force parameter through"
    warning: "The force flag controls -D (force) vs -d (safe) git delete. Dropping it silently changes behavior. Always flow force=force through all layers."
last_audited: "2026-02-07"
audit_result: clean
---

# BranchManager Abstraction

## Why This Abstraction Exists

Erk supports both Graphite-managed and plain Git repositories. Without BranchManager, every CLI command that touches branches would need conditional logic to decide whether to call `gt` or `git`. BranchManager centralizes that decision into two frozen dataclass implementations — `GraphiteBranchManager` and `GitBranchManager` — selected once at context construction time.

```python
# DON'T DO THIS — scattered conditionals in every command
if ctx.graphite.is_enabled():
    ctx.graphite.track_branch(...)
else:
    ctx.git.branch.create_branch(...)
```

The abstraction enforces a **mutation boundary**: all branch mutations (create, delete, checkout, submit, track) go through `ctx.branch_manager`, while read-only queries (current branch, branch list, commit info) stay on `ctx.git.branch`.

## Mutation vs Query Split

This is the key architectural decision. Understanding which operations belong where prevents misuse:

| Operation Type | Access Via | Why |
|---|---|---|
| **Branch mutations** (create, delete, checkout, submit, track) | `ctx.branch_manager` | Mutations need dual-mode logic (Graphite tracking, metadata cleanup, stack awareness) |
| **Branch queries** (current branch, list branches, get HEAD SHA) | `ctx.git.branch` | Queries are always plain git — Graphite adds nothing |
| **Graphite-specific queries** (stack info, parent/child, PR cache) | `ctx.branch_manager` | Queries that return `None`/empty in Git mode, rich data in Graphite mode |

## Behavioral Differences Between Modes

The two implementations diverge in non-obvious ways. This table captures the differences that trip up agents:

| Operation | GraphiteBranchManager | GitBranchManager | Gotcha |
|---|---|---|---|
| `create_branch()` | Creates via git, then temporarily checks out to run `gt track`, then **restores original branch** | Creates via git, stays on current branch | Both leave you on the original branch, but for different reasons |
| `delete_branch()` | LBYL: checks `is_branch_tracked()` first. Tracked branches use `gt delete` (re-parents children, cleans metadata). Untracked branches fall back to plain git | Always plain `git branch -d/-D` | Graphite version handles diverged SHAs gracefully via `gt delete` |
| `submit_branch()` | `gt submit --force --quiet` (submits entire stack) | `git push -u --force origin <branch>` (pushes single branch) | Graphite submits the **whole stack**, not just one branch |
| `track_branch()` | Delegates to `GraphiteBranchOps.track_branch()` | No-op | Silent no-op in Git mode — won't error, just does nothing |
| `get_branch_stack()` | Returns ordered branch list from Graphite cache | Returns `None` | Callers must handle `None` for Git-only repos |
| `get_pr_for_branch()` | Checks Graphite cache first (fast, local), falls back to GitHub API. Sets `from_fallback` flag | Always GitHub API | The `from_fallback` field on `PrInfo` tells you which path was taken |

## The Ephemeral Branch Exception

Not all branches should go through BranchManager. Placeholder branches (`__erk-slot-XX-br-stub__`) and other ephemeral branches bypass it because Graphite tracking would pollute stack metadata for branches that are never pushed, never have PRs, and are frequently created/destroyed.

**See**: [Branch Manager Decision Tree](branch-manager-decision-tree.md) for the full decision framework and [Placeholder Branches](../erk/placeholder-branches.md) for the lifecycle.

## Graphite create_branch() Complexity

<!-- Source: packages/erk-shared/src/erk_shared/gateway/branch_manager/graphite.py, GraphiteBranchManager.create_branch -->

`GraphiteBranchManager.create_branch()` is the most complex method because `gt track` requires the branch to be checked out. The method:

1. Saves the current branch
2. Creates the branch via git
3. Checks out the new branch temporarily
4. Handles remote-ref parents (strips `origin/` prefix, ensures local branch matches remote)
5. Auto-fixes diverged parents via `retrack_branch()` before tracking children
6. Runs `gt track` to register with Graphite
7. Restores the original branch

This restore-after-track behavior is why agents must explicitly call `checkout_branch()` after `create_branch()` — you are **not** left on the new branch.

See `GraphiteBranchManager.create_branch()` in `packages/erk-shared/src/erk_shared/gateway/branch_manager/graphite.py`.

## Error Handling: Mixed Patterns

BranchManager uses **discriminated unions** for `create_branch()` and `submit_branch()` — operations where the non-ideal outcome (branch exists, push failed) is a normal control flow case that callers need to distinguish.

Other methods (`delete_branch()`, `checkout_branch()`) use **exceptions** because their failures are truly exceptional (branch doesn't exist, worktree conflict).

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/branch_ops/types.py, BranchCreated and BranchAlreadyExists -->

See `BranchCreated` and `BranchAlreadyExists` in `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/types.py` for the discriminated union types, and [Discriminated Union Error Handling](discriminated-union-error-handling.md) for the broader pattern.

## Sub-Gateway Architecture

BranchManager sits atop two sub-gateways that provide the actual branch mutation operations:

- **`GitBranchOps`** — mutation + query operations on git branches (used by both implementations)
- **`GraphiteBranchOps`** — Graphite-specific mutations (`track_branch`, `delete_branch`, `submit_branch`, `retrack_branch`)

`GraphiteBranchManager` composes both sub-gateways plus `Git` and `GitHub`. `GitBranchManager` only needs `Git` and `GitHub`. This composition means BranchManager doesn't subclass the sub-gateways — it delegates to them, keeping the abstraction clean.

See `BranchManager` ABC in `packages/erk-shared/src/erk_shared/gateway/branch_manager/abc.py` for the full interface.

## Related Documentation

- [Branch Manager Decision Tree](branch-manager-decision-tree.md) — When to use `ctx.branch_manager` vs `ctx.git.branch`
- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) — Pattern for implementing gateway ABCs
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) — When to use discriminated unions vs exceptions
- [Gateway Error Boundaries](gateway-error-boundaries.md) — Where try/except belongs in gateway implementations
- [Frozen Dataclass Test Doubles](../testing/frozen-dataclass-test-doubles.md) — Testing pattern for FakeBranchManager
