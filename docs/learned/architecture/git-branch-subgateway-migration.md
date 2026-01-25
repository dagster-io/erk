---
title: Git Branch Subgateway Migration Guide
read_when:
  - "migrating code from git_branch_ops field access"
  - "updating tests after branch subgateway changes"
  - "encountering AttributeError for git_branch_ops"
---

# Git Branch Subgateway Migration Guide

This guide explains how to migrate code from the removed `git_branch_ops` field to the new property-based access pattern (`ctx.git.branch`).

## Breaking Change Summary

The `git_branch_ops` field has been removed from `ErkContext`. Branch mutation operations are now accessed through the `ctx.git.branch` property, which returns a `GitBranchOps` sub-gateway.

## Before/After Examples

### Direct Field Access

**Before (removed):**

```python
# This no longer works
ctx.git_branch_ops.create_branch(repo_root, "feature", "main")
ctx.git_branch_ops.checkout_branch(repo_root, "feature")
```

**After (use BranchManager):**

```python
# Branch mutations should go through BranchManager
ctx.branch_manager.create_branch(repo_root, "feature", "main")
ctx.branch_manager.checkout_branch(repo_root, "feature")
```

### Factory Function Parameters

**Before (removed):**

```python
# Factory accepted git_branch_ops parameter
ctx = ErkContext(
    git=git,
    git_branch_ops=FakeGitBranchOps(),  # This parameter is removed
    ...
)
```

**After (auto-linked):**

```python
# FakeGit creates linked FakeGitBranchOps automatically
ctx = ErkContext.for_test(
    git=FakeGit(),  # Includes linked branch_ops
    ...
)
```

### Test Setup

**Before (manual linking):**

```python
# Manually created separate fakes
fake_git = FakeGit()
fake_branch_ops = FakeGitBranchOps()
ctx = create_test_context(
    git=fake_git,
    git_branch_ops=fake_branch_ops,
)
```

**After (automatic linking):**

```python
# FakeGit includes linked branch_ops
fake_git = FakeGit()
ctx = create_test_context(git=fake_git)

# Access via property
fake_git.branch.create_branch(...)
assert "feature" in fake_git.branch.created_branches
```

## Why This Change?

1. **Fewer fields**: `ErkContext` has one less field to manage
2. **Consistent access**: All sub-gateways accessed via properties (`ctx.git.branch`, `ctx.git.worktree`)
3. **Encapsulation**: Branch ops are an implementation detail of the Git gateway
4. **Testability**: FakeGit automatically creates linked fakes for mutation tracking

## Migration Checklist

When updating code affected by this change:

1. [ ] Replace `ctx.git_branch_ops.method()` with `ctx.branch_manager.method()`
2. [ ] Remove `git_branch_ops` parameters from factory function calls
3. [ ] Update test setup to use `FakeGit()` without separate `FakeGitBranchOps`
4. [ ] Update test assertions to use `fake_git.branch.property` instead of separate fake

## Common Errors After Migration

### AttributeError: 'ErkContext' has no attribute 'git_branch_ops'

**Cause:** Code still references the removed field.

**Fix:** Use `ctx.branch_manager` for branch mutations.

### TypeError: unexpected keyword argument 'git_branch_ops'

**Cause:** Factory function called with removed parameter.

**Fix:** Remove the `git_branch_ops` parameter. FakeGit creates linked fakes automatically.

## Related Topics

- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) - Sub-gateway pattern details
- [Flatten Subgateway Pattern](flatten-subgateway-pattern.md) - Pattern documentation
- [Erk Architecture Patterns](erk-architecture.md) - BranchManager usage
