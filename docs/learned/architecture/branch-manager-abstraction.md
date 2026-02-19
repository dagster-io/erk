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
last_audited: "2026-02-19 00:00 PT"
audit_result: clean
---

# BranchManager Abstraction

## Why This Abstraction Exists

Without BranchManager, every CLI command would need conditional logic: "Am I in a Graphite repo? Then call `gt track`. Otherwise use `git branch`." This scattered dual-mode awareness creates maintenance burden and makes mode-specific behavior hard to reason about.

BranchManager centralizes the Graphite-vs-Git decision into two frozen dataclass implementations selected once at context construction time. Commands call `ctx.branch_manager.create_branch()` and get correct behavior for the current repository mode without knowing which mode they're in.

## The Mutation Boundary

BranchManager enforces a critical architectural split between mutations and queries:

| Operation Type                                                 | Route                | Rationale                                                                                   |
| -------------------------------------------------------------- | -------------------- | ------------------------------------------------------------------------------------------- |
| **Branch mutations** (create, delete, checkout, submit, track) | `ctx.branch_manager` | Mutations need dual-mode logic: Graphite tracking, metadata cleanup, stack-aware operations |
| **Branch queries** (current branch, list branches, HEAD SHA)   | `ctx.git.branch`     | Queries are always plain git — Graphite adds nothing to read-only operations                |
| **Graphite-only queries** (stack info, parent/child, PR cache) | `ctx.branch_manager` | Return `None`/empty in Git mode, rich data in Graphite mode                                 |

This separation prevents mutation logic from leaking into every query operation while making dual-mode operations explicit in the type system.

## Non-Obvious Behavioral Differences

Both implementations satisfy the same ABC interface, but their behavior diverges in ways that cause agent confusion:

| Operation             | GraphiteBranchManager Behavior                                                           | GitBranchManager Behavior               | Why This Trips Up Agents                                                                 |
| --------------------- | ---------------------------------------------------------------------------------------- | --------------------------------------- | ---------------------------------------------------------------------------------------- |
| `create_branch()`     | Creates + tracks via `gt track`, **then restores original branch**                       | Creates via git, stays on current       | Both leave you on the **original branch** — explicit `checkout_branch()` required        |
| `delete_branch()`     | LBYL check on `is_branch_tracked()`, then delegates to `gt delete` or `git branch -d/-D` | Plain `git branch -d/-D`                | Graphite mode handles diverged branches gracefully; git mode respects `-d` safety checks |
| `submit_branch()`     | Submits **entire stack** via `gt submit`                                                 | Pushes **single branch** via `git push` | Graphite submits multiple PRs; git pushes one ref                                        |
| `track_branch()`      | Delegates to `GraphiteBranchOps`                                                         | **Silent no-op**                        | Git mode won't error — just does nothing                                                 |
| `get_branch_stack()`  | Returns ordered list from cache                                                          | Returns `None`                          | Callers must handle `None` for Git-only repos                                            |
| `get_pr_for_branch()` | Graphite cache first, GitHub API fallback                                                | Always GitHub API                       | `from_fallback` on `PrInfo` tells you which path was taken                               |

<!-- Source: packages/erk-shared/src/erk_shared/gateway/branch_manager/graphite.py, GraphiteBranchManager -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/branch_manager/git.py, GitBranchManager -->

The restore-after-create behavior exists because `gt track` requires the branch to be checked out. GraphiteBranchManager temporarily switches branches to satisfy Graphite's constraint, then restores the original branch to avoid side effects.

## Test Expectations: Checkout Counts

When converting from `git.branch.create_branch()` to `branch_manager.create_branch()`, expect **+2 checkouts** from BranchManager's internal `gt track` sequence. Your code's own checkout/restore adds more. Update test checkout count assertions accordingly.

For example, `plan_save` uses `branch_manager.create_branch()` (2 checkouts for track) plus its own checkout/restore for committing the plan file (2 more), totaling 4 checkouts:

```python
assert len(fake_git.checked_out_branches) == 4
assert fake_git.checked_out_branches[0][1].startswith("plan-")  # gt track checkout
assert fake_git.checked_out_branches[1] == (tmp_path, "feature-branch")  # gt track restore
assert fake_git.checked_out_branches[2][1].startswith("plan-")  # plan commit checkout
assert fake_git.checked_out_branches[3] == (tmp_path, "feature-branch")  # plan commit restore
```

<!-- Source: tests/unit/cli/commands/exec/scripts/test_plan_save.py, test_draft_pr_restores_original_branch -->

See `test_draft_pr_restores_original_branch()` in `tests/unit/cli/commands/exec/scripts/test_plan_save.py:220-236` for the full example.

## The Ephemeral Branch Exception

Not all branches should go through BranchManager. Placeholder branches (`__erk-slot-XX-br-stub__`) and other ephemeral branches bypass BranchManager because Graphite tracking would pollute stack metadata for branches that:

- Are never pushed to remote
- Never have PRs
- Are frequently created/destroyed
- Exist only to satisfy git's multi-worktree constraint

**Decision framework**: [Branch Manager Decision Tree](branch-manager-decision-tree.md)

**Lifecycle details**: [Placeholder Branches](../erk/placeholder-branches.md)

## Graphite create_branch() Complexity

<!-- Source: packages/erk-shared/src/erk_shared/gateway/branch_manager/graphite.py, GraphiteBranchManager.create_branch -->

`GraphiteBranchManager.create_branch()` is the most complex method in the abstraction because it must:

1. Handle remote-ref parents — strip `origin/` prefix, ensure local branch exists and matches remote SHA
2. Auto-fix diverged parents — if parent is diverged from Graphite's tracking, retrack it before tracking child (prevents tracking failures)
3. Temporarily checkout the new branch to run `gt track` (Graphite requirement)
4. Restore the original branch to avoid unexpected working directory changes

This complexity is why `create_branch()` + `checkout_branch()` is the correct two-step pattern, not an agent mistake.

## Error Handling: Mixed Patterns

BranchManager uses **discriminated unions** for `create_branch()` and `submit_branch()` because the non-ideal outcomes (branch exists, push failed) are normal control flow cases that callers distinguish and handle:

```python
# Callers branch on the error type and continue
result = branch_manager.create_branch(repo_root, name, base)
if isinstance(result, BranchAlreadyExists):
    # Continue: use existing branch or prompt for new name
    handle_existing_branch(result.branch_name)
# Type narrowing: result is now BranchCreated
```

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/branch_ops/types.py, BranchCreated and BranchAlreadyExists -->

Other methods (`delete_branch()`, `checkout_branch()`) use **exceptions** because their failures are truly exceptional — branch doesn't exist, worktree conflict — and no caller has meaningful recovery logic. All they do is extract the message and terminate.

**Deeper pattern**: [Discriminated Union Error Handling](discriminated-union-error-handling.md)

## Sub-Gateway Architecture

BranchManager doesn't implement branch operations itself — it delegates to sub-gateways:

- **`GitBranchOps`** — mutation + query operations on git branches (used by both implementations)
- **`GraphiteBranchOps`** — Graphite-specific mutations (`track_branch`, `delete_branch`, `submit_branch`, `retrack_branch`)

`GraphiteBranchManager` composes both sub-gateways plus `Git` and `GitHub`. `GitBranchManager` only needs `Git` and `GitHub`. This composition (not inheritance) keeps the abstraction clean and makes the Graphite-only operations explicit in the type system.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/branch_manager/abc.py, BranchManager ABC -->

## Related Documentation

- [Branch Manager Decision Tree](branch-manager-decision-tree.md) — When to use `ctx.branch_manager` vs `ctx.git.branch`
- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) — 5-place implementation pattern for gateway ABCs
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) — When to use discriminated unions vs exceptions
- [Frozen Dataclass Test Doubles](../testing/frozen-dataclass-test-doubles.md) — Testing pattern for FakeBranchManager
