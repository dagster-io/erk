---
title: Frozen Dataclass Patterns
read_when:
  - "using frozen dataclasses as common currency"
  - "bundling parameters to avoid explosion"
  - "understanding when to use dataclasses.replace()"
  - "adding computed properties to frozen dataclasses"
---

# Frozen Dataclass Patterns

Frozen dataclasses serve as immutable carriers of state in command pipelines, providing type safety and self-documenting code.

## Core Principle

Frozen dataclasses act as "common currency" that unifies different entry points into a single downstream flow:

```python
@dataclass(frozen=True)
class LandTarget:
    """Resolved landing target from any entry point."""
    branch: str
    pr_details: PRDetails
    worktree_path: Path | None
    is_current_branch: bool
    use_graphite: bool
    target_child_branch: str | None
```

All three entry points (current branch, PR number, branch name) resolve to this single type.

## Benefits

1. **Immutability** - Thread-safe, no accidental mutation
2. **Type safety** - All fields must be populated at construction
3. **Self-documenting** - Field names explain what downstream code needs
4. **Testability** - Easy to construct in tests
5. **Enables replace()** - Create modified copies safely

## Parameter Bundling

When functions need many related parameters, bundle them into a frozen dataclass:

```python
# BEFORE - parameter explosion
def _cleanup_worktree(
    ctx: ErkContext,
    repo: RepoContext,
    branch: str,
    worktree_path: Path | None,
    is_current_branch: bool,
    plan_issue_number: int | None,
    target_child_branch: str | None,
    use_graphite: bool,
    force: bool,
    up_flag: bool,
) -> None:
    ...

# AFTER - bundled into context
@dataclass(frozen=True)
class CleanupContext:
    ctx: ErkContext
    repo: RepoContext
    branch: str
    worktree_path: Path | None
    is_current_branch: bool
    plan_issue_number: int | None
    target_child_branch: str | None
    use_graphite: bool
    force: bool
    up_flag: bool

def _cleanup_worktree(cleanup: CleanupContext) -> None:
    ...
```

## Computed Properties

Add computed fields via `@property` decorators:

```python
@dataclass(frozen=True)
class BranchWorktreeInfo:
    worktree_path: Path | None
    slot_assignment: SlotAssignment | None

    @property
    def is_slot(self) -> bool:
        """Return True if the branch is in a slot worktree."""
        return self.slot_assignment is not None

    @property
    def has_worktree(self) -> bool:
        """Return True if the branch has an associated worktree."""
        return self.worktree_path is not None
```

## Creating Modified Copies

Use `dataclasses.replace()` for immutable updates:

```python
from dataclasses import replace

# Create modified copy with new root
main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root
post_deletion_repo = replace(repo, root=main_repo_root)
```

This preserves all other fields while changing only the specified ones.

## Examples in Codebase

| Dataclass | Purpose | Location |
|-----------|---------|----------|
| `LandTarget` | Resolved PR landing info | land_cmd.py |
| `CleanupContext` | Bundle cleanup parameters | land_cmd.py |
| `ValidatedIssue` | Issue validation result | submit.py |
| `SubmitResult` | Submit operation result | submit.py |
| `WorktreeInfo` | Worktree metadata | erk_shared/git/abc.py |
| `BranchSyncInfo` | Branch sync status | erk_shared/git/abc.py |
| `SlotAllocationResult` | Slot allocation outcome | slot/common.py |
| `NavigationResult` | Navigation outcome | navigation_helpers.py |

## Design Guidelines

### Always Use frozen=True

```python
# CORRECT
@dataclass(frozen=True)
class MyResult:
    value: str

# WRONG - allows mutation
@dataclass
class MyResult:
    value: str
```

### Use None for Optional Fields

```python
@dataclass(frozen=True)
class Target:
    branch: str              # Required - always present
    worktree: Path | None    # Optional - may be None
    pr_number: int | None    # Optional - may be None
```

### Avoid Mutable Default Factories

```python
# WRONG - mutable default
@dataclass(frozen=True)
class Config:
    items: list[str] = field(default_factory=list)

# CORRECT - use tuple for immutable sequences
@dataclass(frozen=True)
class Config:
    items: tuple[str, ...] = ()
```

### Keep Fields Focused

Each dataclass should represent one concept:

```python
# GOOD - focused on landing target
@dataclass(frozen=True)
class LandTarget:
    branch: str
    pr_details: PRDetails
    worktree_path: Path | None

# BAD - mixed concerns
@dataclass(frozen=True)
class LandContext:
    branch: str
    pr_details: PRDetails
    worktree_path: Path | None
    output_format: str        # Unrelated to landing target
    verbose: bool             # Unrelated to landing target
```

## Protocol Compatibility

When using frozen dataclasses with Protocols, use `@property` in the Protocol:

```python
from typing import Protocol

class HasBranch(Protocol):
    @property
    def branch(self) -> str: ...

@dataclass(frozen=True)
class LandTarget:
    branch: str  # Compatible with HasBranch protocol
```

See [Protocol vs ABC Guide](protocol-vs-abc.md) for details.

## Related Topics

- [Multi-Entry-Point Commands](../cli/multi-entry-point-commands.md) - Using frozen dataclasses as common currency
- [Resolver Pattern](../cli/resolver-pattern.md) - Returning frozen dataclasses from resolvers
- [Protocol vs ABC Guide](protocol-vs-abc.md) - Protocol compatibility with frozen dataclasses
