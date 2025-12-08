---
title: Git ABC Implementation Checklist
read_when:
  - "adding or modifying methods in the Git ABC interface"
  - "implementing new Git operations"
tripwires:
  - action: "adding a new method to Git ABC"
    warning: "Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py."
---

# Git ABC Implementation Checklist

When adding a new method to the Git ABC, you must implement it in **5 places**:

| Implementation | Location                                             | Purpose        |
| -------------- | ---------------------------------------------------- | -------------- |
| `abc.py`       | Abstract method definition                           | Contract       |
| `real.py`      | Actual git subprocess calls                          | Production     |
| `fake.py`      | Constructor-injected test data                       | Unit tests     |
| `dry_run.py`   | Delegates to wrapped (read-only) or logs (mutations) | Preview mode   |
| `printing.py`  | Delegates to wrapped, prints mutations               | Verbose output |

## Source Files

All Git ABC implementations are located in `packages/erk/src/erk/integrations/git/`:

- `abc.py` - Abstract base class with method signatures
- `real.py` - Production implementation using subprocess
- `fake.py` - Test double with constructor-injected data
- `dry_run.py` - Preview mode wrapper
- `printing.py` - Verbose output wrapper

## Checklist for New Git Methods

When adding a new method to the Git ABC:

1. [ ] Add abstract method to `abc.py` with docstring
2. [ ] Implement in `real.py` using subprocess
3. [ ] Implement in `fake.py` with constructor parameter for test data
4. [ ] Implement in `dry_run.py` (delegate if read-only, log if mutation)
5. [ ] Implement in `printing.py` (delegate, print if mutation)
6. [ ] Add unit tests for FakeGit behavior
7. [ ] Add integration tests for RealGit (if feasible)

## Common Pitfall

**PrintingGit often falls behind** - check it implements ALL ABC methods. When adding a new method, verify PrintingGit is updated alongside the other implementations.

## Read-Only vs Mutation Methods

### Read-Only Methods

**Examples**: `get_current_branch`, `list_worktrees`, `get_diff`

- **DryRunGit**: Delegates to wrapped implementation (no side effects)
- **PrintingGit**: Delegates silently to wrapped implementation

### Mutation Methods

**Examples**: `create_branch`, `commit`, `push`, `delete_worktree`

- **DryRunGit**: Logs operation with `[DRY RUN]` prefix, does NOT delegate
- **PrintingGit**: Prints operation, then delegates to wrapped implementation

## Implementation Pattern

When implementing a new method:

1. **ABC**: Define the abstract method signature with type hints and docstring describing inputs/outputs
2. **RealGit**: Use subprocess to call the git command, parse output as needed
3. **FakeGit**: Add a new dataclass field (usually a dict) to hold test data, return from that dict
4. **DryRunGit**: For read-only methods, delegate. For mutations, log and return without calling wrapped
5. **PrintingGit**: For read-only methods, delegate silently. For mutations, print then delegate

See existing methods in the source files for concrete examples of this pattern.

## Integration with Fake-Driven Testing

This pattern aligns with the [Fake-Driven Testing Architecture](../testing/):

- **RealGit**: Layer 5 (Business Logic Integration Tests) - production implementation
- **FakeGit**: Layer 4 (Business Logic Tests) - in-memory test double for fast tests
- **DryRunGit**: Preview mode for CLI operations
- **PrintingGit**: Verbose output for debugging

See [Fake-Driven Testing](../testing/) for complete testing strategy.

## Related Documentation

- [Erk Architecture Patterns](erk-architecture.md) - Dependency injection, dry-run patterns
- [Protocol vs ABC](protocol-vs-abc.md) - Why Git uses ABC instead of Protocol
- [Subprocess Wrappers](subprocess-wrappers.md) - How RealGit wraps subprocess calls
