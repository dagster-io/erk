---
title: Flatten Subgateway Pattern
read_when:
  - "adding a new subgateway to an existing gateway"
  - "refactoring field-based gateway composition to property-based"
  - "understanding ctx.git.branch or ctx.git.worktree patterns"
---

# Flatten Subgateway Pattern

The flatten subgateway pattern converts field-based gateway composition (`ctx.foo_ops`) to property-based access (`ctx.gateway.foo`), reducing ErkContext fields while maintaining testability.

## Pattern Definition

**Before (field-based):**

```
ErkContext
├── git: Git
├── git_branch_ops: GitBranchOps    # Separate field
├── git_worktree_ops: GitWorktreeOps # Separate field
└── ...
```

**After (property-based):**

```
ErkContext
├── git: Git
│   ├── .branch → GitBranchOps      # Property access
│   └── .worktree → GitWorktreeOps  # Property access
└── ...
```

## Benefits

1. **Reduced fields**: ErkContext has fewer fields to manage and pass through factories
2. **Consistent access**: All sub-gateways follow the same pattern (`gateway.subgateway`)
3. **Encapsulation**: Sub-gateway is an implementation detail of the parent gateway
4. **Automatic linking**: FakeGit creates linked fake sub-gateways at initialization

## Implementation Requirements

Adding a subgateway property requires updates across all 5 gateway layers:

| Layer         | Implementation                                |
| ------------- | --------------------------------------------- |
| `abc.py`      | Abstract property with TYPE_CHECKING guard    |
| `real.py`     | Returns existing instance created at init     |
| `fake.py`     | Creates linked instance at init, returns same |
| `dry_run.py`  | Lazy wraps underlying property with DryRun    |
| `printing.py` | Lazy wraps underlying property with Printing  |

## Reference Implementations

### Phase 1: Worktree Operations

```python
# Access pattern
ctx.git.worktree.add_worktree(repo_root, path, branch)
ctx.git.worktree.remove_worktree(repo_root, path)
```

Location: `packages/erk-shared/src/erk_shared/git/worktree_ops/`

### Phase 2A: Branch Operations

```python
# Access pattern (through BranchManager, not directly)
ctx.branch_manager.create_branch(repo_root, "feature", "main")
ctx.branch_manager.checkout_branch(repo_root, "feature")
```

Location: `packages/erk-shared/src/erk_shared/git/branch_ops/`

## Implementation Checklist

When adding a new subgateway property:

1. [ ] Create sub-gateway directory with 5 files (abc, real, fake, dry_run, printing)
2. [ ] Add abstract property to parent ABC with TYPE_CHECKING guard
3. [ ] Update RealGateway to create sub-gateway instance at init
4. [ ] Update FakeGateway to create linked fake at init
5. [ ] Update DryRunGateway with lazy wrapping pattern
6. [ ] Update PrintingGateway with lazy wrapping pattern
7. [ ] Remove old field from ErkContext if it existed
8. [ ] Update all factory functions to remove old parameter
9. [ ] Update tests to use property access

## Testing Pattern

The flatten pattern simplifies testing because FakeGit creates linked fakes automatically:

```python
def test_branch_mutations_tracked() -> None:
    fake_git = FakeGit()

    # Use the same access pattern as production code
    fake_git.branch.create_branch(repo_root, "feature", "main")

    # Assert on mutations via the same property
    assert "feature" in fake_git.branch.created_branches
```

No need to create separate fakes or link them manually.

## Related Documentation

- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) - 5-layer implementation details
- [Git Branch Subgateway Migration Guide](git-branch-subgateway-migration.md) - Migration examples
- [Erk Architecture Patterns](erk-architecture.md) - Overall architecture context

## Objective Link

This pattern is part of the gateway facade optimization work tracked in objective #5292.
