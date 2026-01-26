# Learn Plan: Fix `erk br delete` Not Force-Deleting Merged PR Branches

**Issue**: #6053
**PR**: #6055
**Session**: e8dd4e67-22ba-4d7e-92ae-5331c5d0ab33

## Context

The `erk br delete` command had a bug where the `--force` flag was being parsed correctly at the CLI level but **not passed through** to the underlying `BranchManager.delete_branch()` method. This meant that even when users specified `--force`, the deletion would fail when trying to delete branches that had unmerged commits or other safety checks.

The fix was simple but involved understanding how the `BranchManager` abstraction works and ensuring the force flag flows through all layers.

## What Was Built

### The Problem
- `erk br delete --force <branch>` would fail even with `--force`
- The `--force` flag controls the `-D` (force delete) vs `-d` (safe delete) behavior in git
- The flag was parsed at CLI level but dropped before calling `BranchManager`
- This affected users trying to delete merged PR branches that had unpushed local commits

### The Solution

**Three-file fix:**

1. **CLI command layer** (`src/erk/cli/commands/wt/delete_cmd.py:401`): Changed from:
   ```python
   ctx.branch_manager.delete_branch(repo_root, branch)
   ```
   To:
   ```python
   ctx.branch_manager.delete_branch(repo_root, branch, force=force)
   ```

2. **Fake test double** (`packages/erk-shared/src/erk_shared/branch_manager/fake.py:33, 85`):
   - Changed `_deleted_branches` from `list[str]` to `list[tuple[str, bool]]` to track the force flag
   - Updated docstring: "Track deleted branches for assertions: list of (branch, force) tuples"
   - Updated append logic to store `(branch, force)` tuples instead of just branch name

3. **Test assertions** (`tests/unit/fakes/test_fake_branch_manager.py`):
   - Updated all test assertions to match new tuple format
   - Added new test `test_delete_branch_tracks_force_flag()` to explicitly verify force flag tracking

### Design Pattern: Frozen Dataclasses with Mutable Internal Lists

The `FakeBranchManager` uses a pattern worth documenting:

```python
@dataclass(frozen=True)
class FakeBranchManager(BranchManager):
    _deleted_branches: list[tuple[str, bool]] = field(default_factory=list)

    def delete_branch(self, repo_root: Path, branch: str, *, force: bool = False) -> None:
        # Mutates internal list despite frozen dataclass
        self._deleted_branches.append((branch, force))
```

**Why this works:**
- The dataclass is frozen (immutable)
- But the list object itself (the reference) is mutable
- Each method appends to the shared list
- Tests can then assert on what was tracked

**Why this is intentional:**
- Enables test observability without breaking the frozen contract
- Each BranchManager call is recorded for assertions
- Mirrors real-world behavior where gateway methods have observable side effects

## Lessons Learned

### 1. Flag Flow-Through in Layered Architectures

When a CLI flag controls method behavior:
- Parse at CLI boundary
- Pass through ALL intermediate layers (don't drop it mid-stack)
- Document the parameter in ABC method signature
- Update test doubles to track the parameter
- Add test coverage for both flag values

**Risk:** Flags dropped at any layer cause silent behavioral failures - the user sees expected behavior in --help but actual behavior differs.

### 2. Testing Fake Implementations

The `FakeBranchManager` pattern is essential for testing commands that use the `BranchManager` abstraction:

- **ABC signature** (`BranchManager.delete_branch`): Defines the contract with `force` parameter
- **Real implementations** (Git, Graphite): Execute actual git commands
- **Fake implementation**: Tracks calls for assertion without side effects
- **Test double pattern**: Lists of tuples enable assertions on both action and parameters

Tests cannot be written for `_delete_branch_at_error_boundary` without a test-friendly `BranchManager` implementation. The fake provides observable state.

### 3. Immutable Interface with Mutable Observability

Frozen dataclasses can still have mutable observability:

```python
@property
def deleted_branches(self) -> list[tuple[str, bool]]:
    """Get list of deleted branches for test assertions."""
    return list(self._deleted_branches)  # Return a copy
```

The property returns a copy, preventing external mutation, but internal lists are mutable for recording. This preserves both immutability guarantees and test observability.

### 4. Parameter Types in Fake Implementations

When tracking method calls, track the actual parameter types:

- **Old**: `_deleted_branches: list[str]` - loses information
- **New**: `_deleted_branches: list[tuple[str, bool]]` - preserves all call context

This enables assertions that verify not just "what was called" but "how was it called". Critical for testing conditional behavior.

## Documentation Gaps Identified

### 1. **BranchManager Abstraction Documentation** - NEW DOC
**Priority**: HIGH
**Category**: Architecture pattern

The `BranchManager` ABC is the abstraction boundary for branch operations in erk. Users need to understand:
- Why it exists (decouples git vs graphite implementations)
- How to use it in commands (always use `ctx.branch_manager` not `ctx.git` or `ctx.graphite`)
- What methods exist and their contracts
- How it handles both Graphite and Git modes transparently

**Related file**: `packages/erk-shared/src/erk_shared/branch_manager/abc.py`

Suggested location: `docs/learned/architecture/branch-manager-abstraction.md`

### 2. **Frozen Dataclass Test Doubles Pattern** - NEW DOC
**Priority**: HIGH
**Category**: Testing pattern

The frozen dataclass with mutable internal lists is a useful pattern for test doubles. Should document:
- Why frozen dataclasses are preferred (immutability contract)
- How to add mutable internal lists for observability
- How to expose them safely via properties that return copies
- Examples from `FakeBranchManager`, `FakeBranchManager`, and other fakes

**Suggested location**: `docs/learned/testing/frozen-dataclass-test-doubles.md`

### 3. **Tripwire Update: Branch Manager ABC Implementation Checklist** - UPDATE EXISTING
**Category**: Tripwire

When adding methods to `BranchManager` ABC, a tripwire should remind implementers to update:
1. `abc.py` - Add abstract method
2. `git.py` - Real implementation for Git mode
3. `graphite.py` - Real implementation for Graphite mode
4. `fake.py` - Test double (track calls for assertions)
5. `dry_run.py` - Dry-run wrapper (log calls without side effects)

Possibly also `printing.py` if it exists.

**Current state**: The `delete_branch` change required updating 4 files (abc, git, graphite, fake). This is already documented in tripwires.md but good reinforcement.

## Inventory of Changes

**New functionality**: None - this is a bug fix (force flag flow-through)

**Modified files**:
- `packages/erk-shared/src/erk_shared/branch_manager/fake.py`: Track force flag in deleted branches list
- `src/erk/cli/commands/wt/delete_cmd.py`: Pass force flag to branch_manager.delete_branch()
- `tests/unit/fakes/test_fake_branch_manager.py`: Update assertions to match new tuple format, add force flag test

**No new test files, no new CLI commands, no new config options**

## Integration Notes

This fix touches the core branch deletion abstraction. No integration issues because:
- The `BranchManager` ABC wasn't changed (backwards compatible)
- `delete_branch` already had `force` parameter in Git implementation
- The fix just ensures the CLI passes it through
- Tests updated to verify the parameter is tracked

## Related Tripwires

1. **Before adding a new method to BranchManager ABC** → Must implement in 5 places (abc, git, graphite, fake, dry_run)
2. **Before calling ctx.branch_manager mutation methods** → Use ctx.branch_manager not ctx.git or ctx.graphite directly
3. **Before hand-constructing Plan objects** → Use gateway abstractions, don't hand-construct

These were all followed in this fix.

## Summary

A focused fix demonstrating good architectural practices:
- Respects abstraction boundaries (BranchManager)
- Test doubles track relevant parameters (force flag)
- Frozen immutability with mutable observability for testing
- Proper flag flow-through through all layers

The main learning is ensuring flags and parameters flow through complete call stacks - this appears simple but is easy to miss when refactoring across multiple files.