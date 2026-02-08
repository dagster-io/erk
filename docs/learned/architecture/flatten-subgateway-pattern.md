---
title: Flatten Subgateway Pattern
last_audited: "2026-02-07 20:05 PT"
audit_result: edited
read_when:
  - "creating or migrating subgateways"
  - "exposing subgateway operations through parent gateway"
  - "working with gateway hierarchies"
  - "implementing property-based subgateway access"
tripwires:
  - action: "adding a subgateway property to a gateway ABC"
    warning: "Must implement property in 5 places: ABC with TYPE_CHECKING import guard, Real with concrete instance, Fake with linked state, DryRun wrapping inner subgateway, Printing wrapping with script_mode/dry_run."
  - action: "creating fake subgateway without shared state"
    warning: "Fake subgateways must share state containers with parent via constructor parameters and call link_mutation_tracking(). Without this, mutations through subgateway won't be visible to parent queries."
---

# Flatten Subgateway Pattern

## The Pattern

Gateway hierarchies expose specialized operations through property access on parent gateways. Instead of `ctx.git_branch_ops.create_branch()`, callers write `ctx.git.branch.create_branch()`.

**Why this exists:** As gateways decompose from monoliths into focused subgateways, the access pattern becomes verbose if callers construct subgateways directly. Properties provide a clean API while maintaining the 5-layer gateway architecture (ABC, Real, Fake, DryRun, Printing).

## The 5-Layer Implementation Contract

Every subgateway property requires coordinated implementation across all gateway layers. Missing or incorrect implementation in any layer breaks the gateway pattern.

### Layer 1: ABC — TYPE_CHECKING Import Guard

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/abc.py, lines 19-29 -->

The ABC layer uses `TYPE_CHECKING` to import subgateway types without creating runtime circular dependencies. The import only exists during type checking, not at runtime.

See the import block in `Git` ABC (`packages/erk-shared/src/erk_shared/gateway/git/abc.py`) for the pattern. Each subgateway type is imported inside `if TYPE_CHECKING:`, then referenced in `@abstractmethod` property signatures.

**Why TYPE_CHECKING:** Without this guard, abc.py would import from subgateway/abc.py, which imports back to parent abc.py for types like `WorktreeInfo`, creating a circular import. Python's import system would fail at runtime.

### Layer 2: Real — Instantiate and Store

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/real.py, RealGit.__init__ -->

Real layer instantiates concrete subgateway implementations in `__init__`, stores them in private attributes, and returns via property.

See `RealGit.__init__` in `packages/erk-shared/src/erk_shared/gateway/git/real.py`. Each subgateway is constructed once during initialization (e.g., `self._branch = RealGitBranchOps(time=self._time)`), then returned by the property.

**Why instantiate in **init**:** Subgateways often need shared dependencies (like `Time` or other subgateways). Constructing them once ensures consistency — multiple property accesses return the same instance with the same dependencies.

### Layer 3: Fake — Linked State and Mutation Tracking

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/fake.py, FakeGit.__init__ -->

Fake layer is the most complex because it must maintain state consistency between parent and child. State linking uses three distinct mechanisms, not a single pattern.

See `FakeGit.__init__` in `packages/erk-shared/src/erk_shared/gateway/git/fake.py`. The three linking mechanisms:

1. **Constructor injection** — Parent passes read state by reference when constructing the fake subgateway (e.g., `FakeGitBranchOps(worktrees=self._worktrees, ...)`). This is the most common pattern for initial query state.
2. **`link_state()`** — Late-binds read state that isn't available at constructor time, or that needs to be shared after construction (e.g., `self._repo_gateway.link_state(repository_roots=..., git_common_dirs=..., worktrees=...)`). Used by `FakeGitRepoOps`, `FakeGitAnalysisOps`, `FakeGitConfigOps`, `FakeGitStatusOps`, and `FakeGitCommitOps`.
3. **`link_mutation_tracking()`** — Connects mutation lists so parent properties see subgateway mutations (e.g., `self._branch_gateway.link_mutation_tracking(deleted_branches=self._deleted_branches, ...)`). Used by `FakeGitBranchOps`, `FakeGitRemoteOps`, `FakeGitCommitOps`, `FakeGitRebaseOps`, `FakeGitTagOps`, and `FakeGitConfigOps`.

Some subgateways use multiple mechanisms. For example, `FakeGitCommitOps` receives initial state via constructor, then uses both `link_mutation_tracking()` and `link_state()` for different state categories.

**Why linked state matters:** Tests construct a `FakeGit` and call operations through subgateways like `fake_git.branch.delete_branch()`. Without linked state, test assertions on `fake_git.deleted_branches` would see an empty list — the subgateway's mutations wouldn't propagate back to the parent.

### Layer 4: DryRun — Wrap Inner Subgateway

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/dry_run.py, DryRunGit properties -->

DryRun layer accesses the wrapped gateway's subgateway property and wraps it with the corresponding DryRun variant.

See properties in `DryRunGit` (`packages/erk-shared/src/erk_shared/gateway/git/dry_run.py`). Pattern: `return DryRunGitBranchOps(self._wrapped.branch)`.

**Why wrap dynamically:** DryRun doesn't store subgateways during construction because the inner gateway might be Real or Fake. Wrapping on property access maintains the wrapper chain regardless of the inner type.

**Read-only subgateways:** When a subgateway contains only queries (no mutations), DryRun and Printing wrappers become pure pass-through delegates. See `GitRepoOps` and `GitStatusOps` as examples — their DryRun variants simply delegate because queries have no side effects to suppress.

### Layer 5: Printing — Wrap with Configuration

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/printing.py, PrintingGit properties -->

Printing layer wraps like DryRun but also propagates `script_mode` and `dry_run` configuration flags to the subgateway wrapper.

See properties in `PrintingGit` (`packages/erk-shared/src/erk_shared/gateway/git/printing.py`). Pattern: `return PrintingGitBranchOps(self._wrapped.branch, script_mode=self._script_mode, dry_run=self._dry_run)`.

**Why propagate configuration:** Printing behavior varies by mode. Script mode emits parseable output; human mode adds formatting. Dry-run mode changes prefixes ("Would" vs actual operation). Subgateway wrappers need these flags to match parent printing behavior.

## Before and After Migration

Migration changes call paths but doesn't change behavior:

**Before (direct subgateway access):**

```python
ctx.git_branch_ops.create_branch(repo_root, "feature-branch")
```

**After (through parent property):**

```python
ctx.git.branch.create_branch(repo_root, "feature-branch")
```

The flattening occurred during Git gateway decomposition (PR #6169 and subsequent phases). All direct subgateway construction was replaced with property access.

## Common Failure Modes

### Fake Without Linked State

**Symptom:** Test calls `fake_git.branch.delete_branch("old")` but `fake_git.deleted_branches` remains empty.

**Cause:** Fake subgateway wasn't given references to parent state containers, or `link_mutation_tracking()` wasn't called.

**Fix:** Pass parent's state containers by reference to subgateway constructor, then call `link_mutation_tracking()` with mutation lists.

### Missing TYPE_CHECKING Guard

**Symptom:** `ImportError: cannot import name 'GitBranchOps' from partially initialized module` at runtime.

**Cause:** ABC imports subgateway type unconditionally, creating circular import (abc → subgateway/abc → abc for shared types).

**Fix:** Wrap subgateway imports in `if TYPE_CHECKING:` block in parent ABC.

### Double Property Access

**Symptom:** Callsite writes `ctx.git.branch.branch.create_branch()` (property called twice).

**Cause:** Mental model confusion — thinking `branch` is a namespace rather than the subgateway itself.

**Fix:** Remove duplicate property. The property **is** the subgateway, not a path to it.

### Incomplete Layer Implementation

**Symptom:** Type checker errors, `AttributeError` at runtime, or missing wrapper behavior.

**Cause:** Property added to ABC and Real but forgotten in Fake, DryRun, or Printing.

**Fix:** Implement property in all 5 layers. Use checklist below.

## Implementation Checklist

When adding a subgateway property:

- [ ] Add TYPE_CHECKING import in parent ABC
- [ ] Define `@property @abstractmethod` in parent ABC class
- [ ] Instantiate concrete subgateway in Real's `__init__`, store in private attribute
- [ ] Add property returning stored instance in Real
- [ ] Create fake subgateway in Fake's `__init__` with shared state references
- [ ] Call `link_mutation_tracking()` on fake subgateway with parent's mutation lists
- [ ] Add property returning fake instance in Fake
- [ ] Add property in DryRun wrapping `self._wrapped.subgateway_property`
- [ ] Add property in Printing wrapping with `script_mode` and `dry_run` flags
- [ ] Migrate all callsites to use new property path
- [ ] Add tripwire documenting the new property path

## Historical Context: Convenience Method Removal

Gateway ABCs originally contained convenience methods that forwarded to subgateways — methods like `git.get_current_branch()` that just called `self.branch.get_current_branch()`.

PR #6285 removed 16 such methods from Git ABC, enforcing a **pure facade pattern** where the ABC contains **only property accessors**, never convenience methods.

**Why remove convenience methods:**

1. **Clear ownership** — Each operation belongs to exactly one subgateway
2. **Smaller surface area** — Fewer methods = less to maintain across 5 implementations
3. **Prevents duplication** — Without convenience methods, there's one obvious call path
4. **Better discoverability** — IDE autocomplete guides through property hierarchy

**Periodic audit recommendation:** Convenience methods creep back as code evolves. Periodically search gateway ABCs for methods that just delegate to `self.subgateway.method()`, then batch-remove them and migrate callsites.

## Related

- [Gateway ABC Implementation](gateway-abc-implementation.md) — Full 5-layer gateway implementation checklist
- [Gateway Decomposition Phases](gateway-decomposition-phases.md) — Timeline of Git subgateway extractions
