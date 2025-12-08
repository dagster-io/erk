---
title: GitHub Issues ABC Implementation Checklist
read_when:
  - "adding or modifying methods in the GitHubIssues ABC interface"
  - "implementing new GitHub Issues operations"
tripwires:
  - action: "adding a new method to GitHubIssues ABC"
    warning: "Must implement in 4 places: abc.py, real.py, fake.py, dry_run.py."
---

# GitHub Issues ABC Implementation Checklist

When adding a new method to the GitHubIssues ABC, you must implement it in **4 places**:

| Implementation | Location                                                       | Purpose        |
| -------------- | -------------------------------------------------------------- | -------------- |
| `abc.py`       | Abstract method definition                                     | Contract       |
| `real.py`      | Actual gh CLI subprocess calls                                 | Production     |
| `fake.py`      | Constructor-injected test data + mutation tracking             | Unit tests     |
| `dry_run.py`   | Delegates to wrapped (read-only) or logs (mutations)           | Preview mode   |

## Source Files

All GitHubIssues ABC implementations are located in `packages/erk-shared/src/erk_shared/github/issues/`:

- `abc.py` - Abstract base class with method signatures
- `real.py` - Production implementation using gh CLI subprocess
- `fake.py` - Test double with constructor-injected data and mutation tracking
- `dry_run.py` - Preview mode wrapper

## Checklist for New GitHubIssues Methods

When adding a new method to the GitHubIssues ABC:

1. [ ] Add abstract method to `abc.py` with docstring
2. [ ] Implement in `real.py` using gh CLI subprocess
3. [ ] Implement in `fake.py` with constructor parameter for test data
4. [ ] Add mutation tracking properties to `fake.py` (if mutation operation)
5. [ ] Implement in `dry_run.py` (delegate if read-only, log if mutation)
6. [ ] Add unit tests for FakeGitHubIssues behavior
7. [ ] Add integration tests for RealGitHubIssues (if feasible)

## Read-Only vs Mutation Methods

### Read-Only Methods

**Examples**: `get_issue`, `list_issues`, `get_issue_comments`, `get_current_username`

- **DryRunGitHubIssues**: Delegates to wrapped implementation (no side effects)
- **FakeGitHubIssues**: Returns from constructor-injected state

### Mutation Methods

**Examples**: `create_issue`, `add_comment`, `update_issue_body`, `close_issue`, `ensure_label_on_issue`

- **DryRunGitHubIssues**: Logs operation with `[DRY RUN]` prefix, does NOT delegate
- **FakeGitHubIssues**: Updates internal state AND tracks mutation for test assertions

## Fake Mutation Tracking Pattern

The `FakeGitHubIssues` implementation tracks all mutations in lists that can be inspected in tests:

### Constructor Parameters

```python
FakeGitHubIssues(
    issues=...,              # Initial state: dict[int, IssueInfo]
    next_issue_number=1,     # Predictable issue numbering
    labels=...,              # Initial state: set[str]
    comments=...,            # Initial state: dict[int, list[str]]
    username="testuser",     # For get_current_username()
    pr_references=...,       # Initial state: dict[int, list[PRReference]]
)
```

### Mutation Tracking Properties

Each mutation method appends to a tracking list:

```python
@property
def created_issues(self) -> list[tuple[str, str, list[str]]]:
    """Read-only access to created issues for test assertions.

    Returns list of (title, body, labels) tuples.
    """
    return self._created_issues

@property
def added_comments(self) -> list[tuple[int, str]]:
    """Read-only access to added comments for test assertions.

    Returns list of (issue_number, body) tuples.
    """
    return self._added_comments

@property
def closed_issues(self) -> list[int]:
    """Read-only access to closed issues for test assertions.

    Returns list of issue numbers that were closed.
    """
    return self._closed_issues
```

### Test Usage Example

```python
def test_create_issue_and_comment():
    fake = FakeGitHubIssues(next_issue_number=42)

    # Perform operations
    result = fake.create_issue(repo_root, "Bug", "Description", ["bug"])
    fake.add_comment(repo_root, result.number, "Fix pending")

    # Assert using mutation tracking
    assert len(fake.created_issues) == 1
    assert fake.created_issues[0] == ("Bug", "Description", ["bug"])

    assert len(fake.added_comments) == 1
    assert fake.added_comments[0] == (42, "Fix pending")
```

## Implementation Pattern

When implementing a new method:

1. **ABC**: Define the abstract method signature with type hints and docstring describing inputs/outputs
2. **RealGitHubIssues**: Use gh CLI subprocess to call GitHub API, parse JSON output as needed
3. **FakeGitHubIssues**:
   - Add constructor parameter (usually a dict) to hold test data
   - If mutation: track it in a list property for test assertions
   - Return appropriate data or update internal state
4. **DryRunGitHubIssues**: For read-only methods, delegate. For mutations, log and return without calling wrapped

See existing methods in the source files for concrete examples of this pattern.

## Integration with Fake-Driven Testing

This pattern aligns with the [Fake-Driven Testing Architecture](../testing/):

- **RealGitHubIssues**: Layer 5 (Business Logic Integration Tests) - production implementation
- **FakeGitHubIssues**: Layer 4 (Business Logic Tests) - in-memory test double for fast tests
- **DryRunGitHubIssues**: Preview mode for CLI operations

See [Fake-Driven Testing](../testing/) for complete testing strategy.

## Related Documentation

- [Git ABC Implementation Checklist](git-abc-implementation.md) - Similar pattern for Git interface
- [GitHub Interface Patterns](github-interface-patterns.md) - REST API usage patterns
- [Erk Architecture Patterns](erk-architecture.md) - Dependency injection, dry-run patterns
- [Protocol vs ABC](protocol-vs-abc.md) - Why GitHubIssues uses ABC instead of Protocol
- [Subprocess Wrappers](subprocess-wrappers.md) - How RealGitHubIssues wraps gh commands
