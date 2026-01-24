---
title: Mutation Tracking Test Patterns
read_when:
  - "asserting on fake gateway mutations"
  - "handling mutation tracking tuple format changes"
  - "testing BranchManager with explicit branch_ops"
tripwires:
  - action: "modifying FakeGit.created_branches or FakeGitBranchOps.created_branches tuple format"
    warning: "This change cascades to 8+ test files. All assertions unpacking the tuple must be updated."
---

# Mutation Tracking Test Patterns

Fake gateways track mutations via tuples/lists for test assertions. This document covers patterns for asserting on these structures and handling format changes.

## Tuple Unpacking in Assertions

Mutation tracking uses tuples to capture all arguments passed to mutation methods. This enables tests to verify what operations were performed and with what parameters.

For example, `FakeGitBranchOps.create_branch()` stores each invocation as a 4-tuple:

```
(cwd, branch_name, start_point, force)
```

Tests unpack these tuples to assert on mutation behavior:

```python
fake_ops = FakeGitBranchOps()
# ... invoke code that creates branches ...

# Assert on tracked mutations
cwd, branch, start, force = fake_ops.created_branches[0]
assert branch == "feature-branch"
assert force is False
```

## Handling Tuple Format Changes

When a mutation method signature changes (e.g., adding a new parameter), the tuple format must expand to include the new parameter. This change cascades to all test files with assertions unpacking the old tuple format.

### Identifying Affected Tests

Use grep to find all unpacking patterns:

```bash
grep -r "created_branches\[" tests/
```

Update patterns will look like:

- 3-element unpacking: `cwd, branch, start = ...`
- 4-element unpacking: `cwd, branch, start, force = ...`

### Before Change (3-tuple)

```python
def test_create_branch():
    fake = FakeGitBranchOps()
    # ... code that calls create_branch() ...

    cwd, branch, start = fake.created_branches[0]
    assert branch == "feature"
```

### After Change (4-tuple)

```python
def test_create_branch():
    fake = FakeGitBranchOps()
    # ... code that calls create_branch(..., force=True) ...

    cwd, branch, start, force = fake.created_branches[0]
    assert branch == "feature"
    assert force is True
```

## Explicit branch_ops Injection Pattern

Tests for `GraphiteBranchManager` must inject both `git_branch_ops` and `graphite_branch_ops` rather than allowing the manager to create them internally. This enables tests to access the fakes and verify mutations.

```python
from erk_shared.git.branch_ops.fake import FakeGitBranchOps
from erk_shared.gateway.graphite.branch_ops.fake import FakeGraphiteBranchOps

def test_branch_creation() -> None:
    fake_git_branch_ops = FakeGitBranchOps()
    fake_graphite_branch_ops = FakeGraphiteBranchOps()

    branch_manager = GraphiteBranchManager(
        git=fake_git,
        git_branch_ops=fake_git_branch_ops,  # Explicit injection
        graphite=fake_graphite,
        graphite_branch_ops=fake_graphite_branch_ops,  # Explicit injection
        github=fake_github,
    )

    branch_manager.create_branch(repo_root, "feature", "main")

    # Assert on injected fake's mutations
    assert len(fake_git_branch_ops.created_branches) == 1
    cwd, branch, start, force = fake_git_branch_ops.created_branches[0]
    assert branch == "feature"
```

## Why Explicit Injection?

Without explicit injection, `GraphiteBranchManager` creates its own internal branch_ops instances. Tests can't access these to verify mutations, making it impossible to assert on low-level branch operation behavior.

By passing fakes explicitly via constructor, tests gain visibility into what branch operations were performed and with what parameters.

## Linked branch_ops Factory Pattern

Use `create_linked_branch_ops()` when you need both the gateway and its sub-gateway to share state:

```python
fake_git, fake_git_branch_ops = FakeGit.create_linked_branch_ops()
```

This ensures mutation tracking is consistent between the two layers, enabling tests to verify operations at either level.

## Related Documentation

- [Gateway ABC Implementation Checklist](../architecture/gateway-abc-implementation.md) - The 5-file pattern that creates these tuples
- [Erk Test Reference](testing.md) - General testing patterns and fake-driven architecture
- [Force Flag Design](../architecture/force-flags.md) - Understanding force parameter semantics
