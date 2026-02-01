---
title: BranchManager Abstraction
read_when:
  - "working with branch operations (create, delete, checkout, submit)"
  - "implementing commands that manipulate branches"
  - "understanding the Graphite vs Git mode difference"
  - "debugging branch-related operations"
tripwires:
  - action: "calling ctx.git mutation methods (create_branch, delete_branch, checkout_branch, checkout_detached, create_tracking_branch)"
    warning: "Use ctx.branch_manager instead. Branch mutation methods are in GitBranchOps sub-gateway, accessible only through BranchManager. Query methods (get_current_branch, list_local_branches, etc.) remain on ctx.git."
  - action: "calling ctx.graphite mutation methods (track_branch, delete_branch, submit_branch)"
    warning: "Use ctx.branch_manager instead. Branch mutation methods are in GraphiteBranchOps sub-gateway, accessible only through BranchManager. Query methods (is_branch_tracked, get_parent_branch, etc.) remain on ctx.graphite."
  - action: "GraphiteBranchManager.create_branch() without explicit checkout"
    warning: "GraphiteBranchManager.create_branch() restores the original branch after tracking. Always call branch_manager.checkout_branch() afterward if you need to be on the new branch."
---

# BranchManager Abstraction

The `BranchManager` ABC provides a unified interface for branch operations that works transparently with both Graphite-managed and plain Git repositories.

## Why BranchManager Exists

Erk supports two modes:

- **Graphite mode**: Uses `gt` commands for stack-aware branch operations
- **Git mode**: Uses plain `git` commands when Graphite is unavailable

Without an abstraction, every command would need conditional logic:

```python
# DON'T DO THIS - scattered conditionals
if ctx.graphite.is_enabled():
    ctx.graphite.track_branch(...)
else:
    ctx.git.create_branch(...)
```

`BranchManager` centralizes this logic, providing a consistent API regardless of the underlying implementation.

## When to Use BranchManager

**Use `ctx.branch_manager` for all branch mutations:**

- Creating branches
- Deleting branches
- Checking out branches
- Submitting branches to remote
- Tracking branches with parents

**Exception: Ephemeral/Placeholder Branches**

For ephemeral branches that should **never be tracked by Graphite**, use `ctx.git.branch` directly:

```python
# Placeholder branches bypass BranchManager
create_result = ctx.git.branch.create_branch(
    repo.root, placeholder_branch, trunk, force=False
)
```

**Examples of ephemeral branches:**

- `placeholder/slot-*` (pool worktree placeholders)
- Temporary branches for internal operations
- Branches that will never be pushed or have PRs

**See**: [Placeholder Branches](../erk/placeholder-branches.md) and [Branch Manager Decision Tree](branch-manager-decision-tree.md) for complete guidance.

**Use `ctx.git` for read-only queries:**

- `get_current_branch()`
- `list_local_branches()`
- `get_repository_root()`
- Commit operations

## Method Reference

| Method                 | Purpose                              | Graphite                  | Git                  | Error Handling                 |
| ---------------------- | ------------------------------------ | ------------------------- | -------------------- | ------------------------------ |
| `create_branch()`      | Create new branch from base          | `gt create`               | `git branch`         | Discriminated union (PR #6348) |
| `delete_branch()`      | Delete local branch                  | `git branch -D` + cleanup | `git branch -d/-D`   | Exception-based                |
| `checkout_branch()`    | Switch to branch                     | `git checkout`            | `git checkout`       | Exception-based                |
| `submit_branch()`      | Push branch to remote                | `gt submit`               | `git push -u origin` | Exception-based                |
| `track_branch()`       | Register existing branch with parent | `gt track`                | No-op                | Exception-based                |
| `get_pr_for_branch()`  | Get PR info for branch               | Cache lookup              | GitHub API           | Exception-based                |
| `get_branch_stack()`   | Get linear stack containing branch   | Returns stack             | Returns None         | Returns None on failure        |
| `get_parent_branch()`  | Get parent branch name               | Cache lookup              | Returns None         | Returns None on failure        |
| `get_child_branches()` | Get child branches                   | Cache lookup              | Returns empty list   | Returns empty on failure       |

## Force Flag Flow-Through

When passing flags through to BranchManager methods, ensure they flow through all layers:

```python
# Correct - force flag passed through
ctx.branch_manager.delete_branch(repo_root, branch, force=force)

# Wrong - force flag dropped
ctx.branch_manager.delete_branch(repo_root, branch)  # Always uses safe delete
```

The `force` parameter controls `-D` (force delete) vs `-d` (safe delete) behavior in git. Dropping it causes silent behavioral differences from what the user expects.

## Implementation Files

| Implementation          | Location                                                                |
| ----------------------- | ----------------------------------------------------------------------- |
| ABC                     | `packages/erk-shared/src/erk_shared/gateway/branch_manager/abc.py`      |
| Graphite implementation | `packages/erk-shared/src/erk_shared/gateway/branch_manager/graphite.py` |
| Git implementation      | `packages/erk-shared/src/erk_shared/gateway/branch_manager/git.py`      |
| Fake for testing        | `packages/erk-shared/src/erk_shared/gateway/branch_manager/fake.py`     |

## Checking Graphite Mode

To check whether Graphite is being used (e.g., for display purposes):

```python
if ctx.branch_manager.is_graphite_managed():
    # Show Graphite-specific UI
    ...
```

## Discriminated Union Delegation

As of PR #6348, `create_branch()` uses discriminated union error handling. BranchManager delegates to the underlying GitBranchOps gateway, which returns a `CreateBranchResult`:

```python
result = git_ops.create_branch(name=branch_name, start_point=base_branch)
if result.type == "branch_already_exists":
    # Handle existing branch
    ...
elif result.type == "error":
    # Handle unexpected error
    ...
# Success case
return result.branch_name
```

This pattern allows callers to distinguish between "branch already exists" (recoverable) and generic errors (unrecoverable) without exception parsing.

## Related Documentation

- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) - Pattern for implementing gateway ABCs
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) - When to use discriminated unions vs exceptions
- [Gateway Error Boundaries](gateway-error-boundaries.md) - Where try/except belongs in gateway implementations
- [Frozen Dataclass Test Doubles](../testing/frozen-dataclass-test-doubles.md) - Testing pattern for FakeBranchManager
