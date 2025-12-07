---
title: Not-Found Sentinel Pattern
read_when:
  - "designing return types for lookup operations"
  - "handling missing resource cases without exceptions"
  - "checking if get_pr_for_branch() returned a PR"
  - "working with GitHub PR lookup results"
tripwires:
  - action: "checking if get_pr_for_branch() returned a PR"
    warning: "Use `isinstance(pr, PRNotFound)` not `pr is not None`. PRNotFound is a sentinel object, not None."
---

# Not-Found Sentinel Pattern

Use sentinel classes instead of `None` or exceptions for LBYL-style "not found" handling in lookup operations.

## The Pattern

When a lookup operation might not find a result, return a sentinel class instead of `None`:

```python
@dataclass(frozen=True)
class ResourceNotFound:
    """Sentinel indicating resource was not found."""
    identifier: str  # What was looked up (for context)

@dataclass(frozen=True)
class Resource:
    """The actual resource data."""
    id: str
    name: str

def get_resource(identifier: str) -> Resource | ResourceNotFound:
    """Look up a resource by identifier."""
    data = _fetch_from_api(identifier)
    if data is None:
        return ResourceNotFound(identifier=identifier)
    return Resource(id=data["id"], name=data["name"])
```

### Consuming the Result

```python
# CORRECT: Check for sentinel with isinstance
result = get_resource("abc123")
if isinstance(result, ResourceNotFound):
    click.echo(f"Resource not found: {result.identifier}")
else:
    # result is Resource - type narrowing works
    click.echo(f"Found: {result.name}")

# WRONG: Checking for None doesn't work
result = get_resource("abc123")
if result is not None:  # ResourceNotFound is not None!
    click.echo(result.name)  # AttributeError!
```

## Why Sentinel Instead of None?

| Approach        | Type Safety                 | Context        | LBYL | Downsides                                  |
| --------------- | --------------------------- | -------------- | ---- | ------------------------------------------ |
| Return `None`   | ❌ `T \| None` loses info   | ❌ No context  | ✅   | Loses what was looked up                   |
| Raise exception | ❌ Not in signature         | ✅ Can include | ❌   | Violates LBYL, control flow via exceptions |
| Sentinel class  | ✅ `T \| NotFound` explicit | ✅ Preserves   | ✅   | Slightly more code                         |

The sentinel provides:

1. **Type safety**: Union type `Resource | ResourceNotFound` is explicit about possible returns
2. **Context preservation**: Sentinel can store what was looked up (ID, name, etc.)
3. **LBYL compliance**: Explicit isinstance check, not try/except

## When to Use This Pattern

**Use sentinels when:**

- Lookup failure is a normal, expected case (not exceptional)
- Callers need to know what was looked up when handling the "not found" case
- You want type-safe return values that work with type narrowing

**Use exceptions when:**

- Failure indicates a programming error or system failure
- The error should propagate up the call stack
- Recovery is unlikely at the immediate call site

**Use `None` when:**

- No context about the lookup is needed
- The API is simple and `T | None` is clear enough
- You're matching an existing interface that uses `None`

## Example: PRNotFound

The `PRNotFound` sentinel in erk demonstrates this pattern:

```python
from erk_shared.github.types import PRNotFound, PRDetails

# PRNotFound preserves lookup context
@dataclass(frozen=True)
class PRNotFound:
    branch: str | None = None    # Branch that was looked up
    pr_number: int | None = None  # PR number that was looked up

# Usage
pr = github.get_pr_for_branch(repo_root, branch_name)
if isinstance(pr, PRNotFound):
    click.echo(f"No PR found for branch: {pr.branch}")
else:
    # pr is PRDetails - type narrowing works
    click.echo(f"PR #{pr.number}: {pr.title}")
```

### Methods Using PRNotFound

- `GitHub.get_pr_for_branch(repo_root, branch) -> PRDetails | PRNotFound`
- `GitHub.get_pr(owner, repo, pr_number) -> PRDetails | PRNotFound`

## Implementation Checklist

When implementing a not-found sentinel:

1. **Create a frozen dataclass** for the sentinel
2. **Include context fields** (what was looked up)
3. **Use union return type** (`Result | NotFound`)
4. **Document the pattern** in method docstrings
5. **Update fakes** to return the sentinel (not `None`)

## Cross-Package Consistency

**Important**: When code is tested by multiple packages with different fakes, ensure all fakes return the sentinel type consistently. Using `isinstance(result, NotFoundType)` handles cases where some fakes might still return `None` (since `None` fails the isinstance check).

## Related Topics

- [GitHub Interface Patterns](github-interface-patterns.md) - PRDetails type and fetch patterns
- [Protocol vs ABC](protocol-vs-abc.md) - Interface design decisions
