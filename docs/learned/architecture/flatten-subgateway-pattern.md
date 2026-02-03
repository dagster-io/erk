---
title: Flatten Subgateway Pattern
last_audited: "2026-02-03"
audit_result: edited
read_when:
  - "creating or migrating subgateways"
  - "exposing subgateway operations through parent gateway"
  - "working with gateway hierarchies"
  - "implementing property-based subgateway access"
---

# Flatten Subgateway Pattern

The flatten subgateway pattern exposes specialized operation groups through clean property access on a parent gateway, converting verbose paths like `ctx.git_branch_ops.create_branch()` to elegant calls like `ctx.git.branch.create_branch()`.

## Pattern Overview

**Problem:** Direct subgateway access creates verbose, repetitive code and couples callers to gateway internals.

**Solution:** Expose subgateways through `@property` methods on the parent gateway, providing a clean, hierarchical API.

**Result:** Callers work with a unified gateway interface while accessing specialized operations through intuitive property chains.

## Implementation Structure

The pattern requires implementing the property across all 5 gateway layers:

1. **ABC Layer** - Abstract property with TYPE_CHECKING import guard
2. **Real Layer** - Returns concrete subgateway instance
3. **Fake Layer** - Returns fake subgateway with linked state
4. **DryRun Layer** - Wraps subgateway with DryRun variant
5. **Printing Layer** - Wraps subgateway with Printing variant

## Example: Git Branch Operations

The Git gateway exposes branch operations through the `branch` property. See the canonical implementation in `packages/erk-shared/src/erk_shared/gateway/git/`.

### 1. ABC Layer (abc.py)

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erk_shared.gateway.git.branch_ops.abc import GitBranchOps

class Git(ABC):
    @property
    @abstractmethod
    def branch(self) -> GitBranchOps:
        """Access branch operations subgateway."""
        ...
```

**Key technique:** `TYPE_CHECKING` guard prevents circular imports while maintaining type safety. The import only exists during type checking, not at runtime.

### 2. Real Layer (real.py)

```python
class RealGit(Git):
    def __init__(self, time: Time | None = None) -> None:
        self._time = time if time is not None else RealTime()
        self._worktree = RealWorktree()
        self._branch = RealGitBranchOps(time=self._time)

    @property
    def branch(self) -> GitBranchOps:
        """Access branch operations subgateway."""
        return self._branch
```

**Pattern:** Instantiate the concrete subgateway in `__init__`, store in a private attribute, return via property. Pass shared dependencies (like `time`) to maintain consistency across gateways.

### 3. Fake Layer (fake.py)

```python
class FakeGit(Git):
    def __init__(self, *, ...) -> None:
        # State containers (populated from constructor kwargs)
        self._current_branches = current_branches or {}
        self._local_branches = local_branches or {}
        self._branch_heads = branch_heads or {}
        # ... many more state fields

        # Construct subgateway with shared state references
        self._branch_gateway = FakeGitBranchOps(
            worktrees=self._worktrees,
            current_branches=self._current_branches,
            local_branches=self._local_branches,
            remote_branches=self._remote_branches,
            branch_heads=self._branch_heads,
            trunk_branches=self._trunk_branches,
            # ... additional state references
        )
        # Link mutation tracking so parent sees subgateway mutations
        self._branch_gateway.link_mutation_tracking(
            created_branches=self._created_branches,
            deleted_branches=self._deleted_branches,
            checked_out_branches=self._checked_out_branches,
            detached_checkouts=self._detached_checkouts,
            created_tracking_branches=self._created_tracking_branches,
        )

    @property
    def branch(self) -> GitBranchOps:
        """Access branch operations subgateway."""
        return self._branch_gateway
```

**Critical pattern:** Pass references to parent's state containers to the fake subgateway constructor, then call `link_mutation_tracking()` to connect mutation lists. This enables **linked mutation tracking** -- changes made through the subgateway update the parent's state, allowing queries through the parent to observe the mutations.

### 4. DryRun Layer (dry_run.py)

```python
class DryRunGit(Git):
    def __init__(self, wrapped: Git) -> None:
        self._wrapped = wrapped

    @property
    def branch(self) -> GitBranchOps:
        """Access branch operations subgateway (wrapped with DryRunGitBranchOps)."""
        return DryRunGitBranchOps(self._wrapped.branch)
```

**Pattern:** Wrap the inner gateway's subgateway property with the corresponding DryRun variant. This maintains the wrapper chain through property access.

### 5. Printing Layer (printing.py)

```python
class PrintingGit(PrintingBase, Git):
    # Inherits __init__(wrapped, *, script_mode, dry_run) from PrintingBase

    @property
    def branch(self) -> GitBranchOps:
        """Access branch operations subgateway (wrapped with PrintingGitBranchOps)."""
        return PrintingGitBranchOps(
            self._wrapped.branch, script_mode=self._script_mode, dry_run=self._dry_run
        )
```

**Pattern:** Similar to DryRun, but inherits from `PrintingBase` which provides the common `__init__` with `wrapped`, `script_mode`, and `dry_run`. Each property passes these configuration values to the printing subgateway wrapper.

## Read-Only Subgateways

When a subgateway contains only query operations (no mutations), the DryRun and Printing wrapper layers can be simplified to pure pass-through delegation.

**Example:** GitStatusOps contains only query methods (`has_staged_changes`, `get_file_status`, etc.), so:

- `DryRunGitStatusOps` simply delegates to the wrapped implementation
- `PrintingGitStatusOps` simply delegates without logging

There's no special dry-run behavior needed because queries have no side effects to suppress.

See [Gateway Decomposition Phases](gateway-decomposition-phases.md) for the full list of subgateway variants.

## Before and After

**Before (verbose, coupled):**

```python
# Direct subgateway access
ctx.git_branch_ops.create_branch(repo_root, "feature-branch")
ctx.git_branch_ops.checkout_branch(repo_root, "feature-branch")
ctx.git_branch_ops.delete_branch(repo_root, "old-branch")
```

**After (clean, hierarchical):**

```python
# Through parent gateway property
ctx.git.branch.create_branch(repo_root, "feature-branch")
ctx.git.branch.checkout_branch(repo_root, "feature-branch")
ctx.git.branch.delete_branch(repo_root, "old-branch")
```

## Benefits

1. **Cleaner API** - Shorter, more intuitive call chains
2. **Encapsulation** - Hides subgateway instantiation details
3. **Consistency** - All layers implement the same interface
4. **Testability** - Fake layer maintains state linkage through properties
5. **Type Safety** - TYPE_CHECKING guard avoids circular imports

## Implementation Checklist

When adding a subgateway property:

- [ ] Add TYPE_CHECKING import in ABC layer
- [ ] Define abstract property in ABC class
- [ ] Instantiate concrete subgateway in Real.**init**
- [ ] Return instance via property in Real layer
- [ ] Create linked fake subgateway in Fake.**init** with shared state
- [ ] Return fake instance via property in Fake layer
- [ ] Wrap subgateway in DryRun layer property
- [ ] Wrap subgateway in Printing layer property
- [ ] Update all call sites to use new property path
- [ ] Add tripwire to prevent old-style access

## Common Pitfalls

**Double property access:** `ctx.git.branch.branch.create_branch()` - calling property twice.

- **Cause:** Forgetting that `branch` IS the subgateway, not a namespace
- **Prevention:** Add "Double .branch.branch" tripwire

**Broken fake linkage:** Mutations through subgateway not visible in parent queries.

- **Cause:** Fake subgateway not sharing state with parent
- **Fix:** Pass parent's state containers by reference to fake subgateway

**Missing wrapper layers:** DryRun or Printing doesn't wrap the subgateway.

- **Cause:** Forgetting to update all 5 layers
- **Fix:** Use the 5-layer checklist above

## Removed Convenience Methods Rationale

### Pure Facade Goal

Gateway ABCs should contain **ONLY property accessors** to subgateways, not convenience methods that delegate to those properties. This enforces a pure facade pattern where the ABC is a thin organizational layer.

### The Problem: Convenience Method Accumulation

As new subgateways are added, convenience methods accumulate in the parent ABC - methods that just forward calls to subgateway properties:

```python
class Git(ABC):
    @property
    @abstractmethod
    def branch(self) -> GitBranchOps:
        ...

    # Convenience method - just forwards to subgateway
    @abstractmethod
    def get_current_branch(self, repo_root: Path) -> str:
        ...

    # What it actually does in implementations:
    def get_current_branch(self, repo_root: Path) -> str:
        return self.branch.get_current_branch(repo_root)
```

### PR #6285: Systematic Cleanup

PR #6285 removed **16 methods** from the Git ABC implementations:

- **14 convenience methods** - Forwards to `branch`, `worktree`, `rebase`, etc.
- **2 rebase methods** - `rebase_onto`, `rebase_abort` moved to `rebase` subgateway

**Migration mapping examples:**

| Before (convenience)       | After (subgateway property)       |
| -------------------------- | --------------------------------- |
| `git.get_current_branch()` | `git.branch.get_current_branch()` |
| `git.create_branch()`      | `git.branch.create_branch()`      |
| `git.delete_branch()`      | `git.branch.delete_branch()`      |
| `git.checkout_branch()`    | `git.branch.checkout_branch()`    |
| `git.list_worktrees()`     | `git.worktree.list_worktrees()`   |
| `git.add_worktree()`       | `git.worktree.add_worktree()`     |
| `git.rebase_onto()`        | `git.rebase.rebase_onto()`        |

**Result:** Git ABC reduced to exactly **10 abstract property accessors** - a pure facade with zero convenience methods.

### Why This Matters

1. **Clear Ownership** - Each operation belongs to exactly one subgateway, eliminating ambiguity
2. **Discoverability** - IDE autocomplete guides users through the property hierarchy
3. **Smaller Surface Area** - Fewer methods in the ABC = less to maintain across 5 implementations
4. **Prevents Duplication** - Without convenience methods, there's one obvious way to call each operation

### Periodic Audit Recommendation

Convenience methods creep back as code evolves. Periodically audit gateway ABCs:

1. Search for methods that delegate to `self.subgateway.method()`
2. Check for zero production callers (methods that aren't actually used)
3. Batch removal in a single PR (maintain 5-file synchronization)

See [Gateway ABC Implementation](gateway-abc-implementation.md#abc-method-removal-pattern) for the removal pattern and verification steps.

## Related Topics

- [Gateway ABC Implementation](gateway-abc-implementation.md) - Full 5-layer gateway pattern
- [Gateway Hierarchy](gateway-hierarchy.md) - BranchManager factory pattern
- [Tripwires](tripwires.md) - Anti-patterns to avoid
