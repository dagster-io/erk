---
title: Gateway ABC Implementation Checklist
read_when:
  - "adding or modifying methods in any gateway ABC interface (Git, GitHub, Graphite)"
  - "implementing new gateway operations"
tripwires:
  - action: "adding a new method to Git ABC"
    warning: "Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py."
  - action: "adding a new method to GitHub ABC"
    warning: "Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py."
  - action: "adding a new method to Graphite ABC"
    warning: "Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py."
---

# Gateway ABC Implementation Checklist

All gateway ABCs (Git, GitHub, Graphite) follow the same 5-file pattern. When adding a new method to any gateway, you must implement it in **5 places**:

| Implementation | Purpose                                              |
| -------------- | ---------------------------------------------------- |
| `abc.py`       | Abstract method definition (contract)                |
| `real.py`      | Production implementation (subprocess/API calls)     |
| `fake.py`      | Constructor-injected test data (unit tests)          |
| `dry_run.py`   | Delegates read-only, no-ops mutations (preview mode) |
| `printing.py`  | Delegates to wrapped, prints mutations (verbose)     |

## Gateway Locations

| Gateway  | Location                                                    |
| -------- | ----------------------------------------------------------- |
| Git      | `packages/erk-shared/src/erk_shared/git/`                   |
| GitHub   | `packages/erk-shared/src/erk_shared/github/`                |
| Graphite | `packages/erk-shared/src/erk_shared/integrations/graphite/` |

## Checklist for New Gateway Methods

When adding a new method to any gateway ABC:

1. [ ] Add abstract method to `abc.py` with docstring and type hints
2. [ ] Implement in `real.py` (subprocess for Git, `gh` CLI for GitHub/Graphite)
3. [ ] Implement in `fake.py` with:
   - Constructor parameter for test data (if read method)
   - Mutation tracking list/set (if write method)
   - Read-only property for test assertions (if write method)
4. [ ] Implement in `dry_run.py`:
   - Read-only methods: delegate to wrapped
   - Mutation methods: no-op, return success value
5. [ ] Implement in `printing.py`:
   - Read-only methods: delegate silently
   - Mutation methods: print, then delegate
6. [ ] Add unit tests for Fake behavior
7. [ ] Add integration tests for Real (if feasible)

## Read-Only vs Mutation Methods

### Read-Only Methods

**Examples**: `get_current_branch`, `get_pr`, `list_workflow_runs`

```python
# dry_run.py - Delegate to wrapped
def get_pr(self, repo_root: Path, pr_number: int) -> PRDetails | PRNotFound:
    return self._wrapped.get_pr(repo_root, pr_number)

# printing.py - Delegate silently
def get_pr(self, repo_root: Path, pr_number: int) -> PRDetails | PRNotFound:
    return self._wrapped.get_pr(repo_root, pr_number)
```

### Mutation Methods

**Examples**: `create_branch`, `merge_pr`, `resolve_review_thread`

```python
# dry_run.py - No-op, return success
def resolve_review_thread(self, repo_root: Path, thread_id: str) -> bool:
    return True  # No actual mutation

# printing.py - Print, then delegate
def resolve_review_thread(self, repo_root: Path, thread_id: str) -> bool:
    print(f"Resolving thread {thread_id}")
    return self._wrapped.resolve_review_thread(repo_root, thread_id)
```

## FakeGateway Pattern for Mutations

When adding a mutation method to a Fake:

```python
class FakeGitHub(GitHub):
    def __init__(self, ...) -> None:
        # Mutation tracking
        self._resolved_thread_ids: set[str] = set()
        self._thread_replies: list[tuple[str, str]] = []

    def resolve_review_thread(self, repo_root: Path, thread_id: str) -> bool:
        self._resolved_thread_ids.add(thread_id)
        return True

    def add_review_thread_reply(self, repo_root: Path, thread_id: str, body: str) -> bool:
        self._thread_replies.append((thread_id, body))
        return True

    # Read-only properties for test assertions
    @property
    def resolved_thread_ids(self) -> set[str]:
        return self._resolved_thread_ids

    @property
    def thread_replies(self) -> list[tuple[str, str]]:
        return self._thread_replies
```

## Common Pitfall

**Printing implementations often fall behind** - when adding a new method, verify PrintingGit/PrintingGitHub/PrintingGraphite is updated alongside the other implementations.

## Integration with Fake-Driven Testing

This pattern aligns with the [Fake-Driven Testing Architecture](../testing/):

- **Real**: Layer 5 (Business Logic Integration Tests) - production implementation
- **Fake**: Layer 4 (Business Logic Tests) - in-memory test double for fast tests
- **DryRun**: Preview mode for CLI operations
- **Printing**: Verbose output for debugging

## Related Documentation

- [Erk Architecture Patterns](erk-architecture.md) - Dependency injection, dry-run patterns
- [Protocol vs ABC](protocol-vs-abc.md) - Why gateways use ABC instead of Protocol
- [Subprocess Wrappers](subprocess-wrappers.md) - How Real implementations wrap subprocess calls
- [GitHub GraphQL Patterns](github-graphql.md) - GraphQL mutation patterns for GitHub
