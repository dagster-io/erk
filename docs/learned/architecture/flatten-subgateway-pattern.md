---
title: Flatten Subgateway Pattern
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

### 1. ABC Layer (abc.py:19-21, 105-109)

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

### 2. Real Layer (real.py:37, 44-47)

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

### 3. Fake Layer (fake.py:271-276, 302-305)

```python
class FakeGit(Git):
    def __init__(self) -> None:
        # Shared state containers
        self._worktrees: dict[Path, Worktree] = {}
        self._current_branches: dict[Path, str] = {}
        self._local_branches: dict[Path, list[str]] = {}
        self._remote_branches: dict[Path, dict[str, list[str]]] = {}
        self._branch_heads: dict[tuple[Path, str], str] = {}

        # Link subgateway to shared state
        self._branch_gateway = FakeGitBranchOps(
            worktrees=self._worktrees,
            current_branches=self._current_branches,
            local_branches=self._local_branches,
            remote_branches=self._remote_branches,
            branch_heads=self._branch_heads,
        )

    @property
    def branch(self) -> GitBranchOps:
        """Access branch operations subgateway."""
        return self._branch_gateway
```

**Critical pattern:** Pass references to parent's state containers to the fake subgateway. This enables **linked mutation tracking** - changes made through the subgateway update the parent's state, allowing queries through the parent to observe the mutations.

See `docs/learned/testing/linked-mutation-tracking.md` for the full pattern.

### 4. DryRun Layer (dry_run.py:52-55)

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

### 5. Printing Layer (printing.py:45-50)

```python
class PrintingGit(Git):
    def __init__(self, wrapped: Git, script_mode: bool, dry_run: bool) -> None:
        self._wrapped = wrapped
        self._script_mode = script_mode
        self._dry_run = dry_run

    @property
    def branch(self) -> GitBranchOps:
        """Access branch operations subgateway (wrapped with PrintingGitBranchOps)."""
        return PrintingGitBranchOps(
            self._wrapped.branch, script_mode=self._script_mode, dry_run=self._dry_run
        )
```

**Pattern:** Similar to DryRun, but pass configuration (script_mode, dry_run) to the printing wrapper.

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

## Related Topics

- [Gateway ABC Implementation](gateway-abc-implementation.md) - Full 5-layer gateway pattern
- [Linked Mutation Tracking](../testing/linked-mutation-tracking.md) - How fakes share state
- [Gateway Hierarchy](gateway-hierarchy.md) - BranchManager factory pattern
- [Tripwires](tripwires.md) - Anti-patterns to avoid
