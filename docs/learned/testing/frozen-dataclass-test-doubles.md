---
title: Frozen Dataclass Test Doubles
read_when:
  - "implementing a fake for an ABC interface"
  - "adding mutation tracking to a test double"
  - "understanding the frozen dataclass with mutable internals pattern"
  - "writing tests that assert on method call parameters"
---

# Frozen Dataclass Test Doubles

This pattern combines frozen dataclasses (immutability guarantees) with mutable internal lists (test observability) to create effective test doubles.

## The Pattern

```python
@dataclass(frozen=True)
class FakeBranchManager(BranchManager):
    # Test data - provided at construction
    pr_info: dict[str, PrInfo] = field(default_factory=dict)

    # Mutation tracking - mutable despite frozen
    _deleted_branches: list[tuple[str, bool]] = field(default_factory=list)

    def delete_branch(self, repo_root: Path, branch: str, *, force: bool = False) -> None:
        # Append to internal list - mutates despite frozen dataclass
        self._deleted_branches.append((branch, force))

    @property
    def deleted_branches(self) -> list[tuple[str, bool]]:
        # Return a copy to prevent external mutation
        return list(self._deleted_branches)
```

## Why This Works

The dataclass is frozen (immutable), but:

- The **reference** to the list is frozen (can't reassign `_deleted_branches`)
- The **list contents** are mutable (can append/remove items)
- This is intentional Python semantics, not a bug

## Benefits

**1. Immutability Contract**

The frozen dataclass prevents accidental field reassignment:

```python
fake = FakeBranchManager()
fake._deleted_branches = []  # Raises FrozenInstanceError
```

**2. Test Observability**

Methods can record their calls for assertions:

```python
fake = FakeBranchManager()
fake.delete_branch(repo_root, "feature", force=True)

# Assert the method was called with expected parameters
assert ("feature", True) in fake.deleted_branches
```

**3. Parameter Tracking**

Track full call context, not just what was called:

```python
# Old - loses force flag information
_deleted_branches: list[str]

# New - preserves all call context
_deleted_branches: list[tuple[str, bool]]
```

## Property Pattern for Safe Access

Always expose mutation lists via properties that return copies:

```python
@property
def deleted_branches(self) -> list[tuple[str, bool]]:
    """Get list of deleted branches for test assertions."""
    return list(self._deleted_branches)  # Return a copy
```

This prevents test code from accidentally modifying the tracking list.

## Common Tuple Structures

Different operations need different information tracked:

| Operation       | Tuple Structure              | Example                         |
| --------------- | ---------------------------- | ------------------------------- |
| Branch creation | `(branch_name, base_branch)` | `("feature", "main")`           |
| Branch deletion | `(branch_name, force)`       | `("feature", True)`             |
| Branch tracking | `(branch_name, parent)`      | `("feature", "main")`           |
| Tracking branch | `(branch, remote_ref)`       | `("feature", "origin/feature")` |

## Test Assertions

```python
def test_delete_branch_tracks_force_flag() -> None:
    fake = FakeBranchManager()

    fake.delete_branch(Path("/repo"), "branch-1", force=False)
    fake.delete_branch(Path("/repo"), "branch-2", force=True)

    assert fake.deleted_branches == [
        ("branch-1", False),
        ("branch-2", True),
    ]
```

## When to Use This Pattern

- Implementing fakes for ABC interfaces
- Any test double that needs to track method calls
- When you need to assert both "what was called" and "how it was called"

## Reference Implementations

- `FakeBranchManager`: `packages/erk-shared/src/erk_shared/branch_manager/fake.py`
- `FakeGitHub`: `packages/erk-shared/src/erk_shared/github/fake.py`
- `FakeGitBranchOps`: `packages/erk-shared/src/erk_shared/git/branch_ops/fake.py`

## Related Documentation

- [Gateway ABC Implementation Checklist](../architecture/gateway-abc-implementation.md) - Full fake implementation checklist
- [BranchManager Abstraction](../architecture/branch-manager-abstraction.md) - The abstraction this pattern supports
