---
name: fake-driven-testing-advanced-extensions
description: Advanced gateway extensions like DryRun wrappers
---

# Advanced Gateway Extensions

**Read this when**: You want to extend the gateway system beyond the core ABC/Real/Fake pattern.

## Overview

The core gateway pattern (ABC → Real → Fake) handles most testing needs. This document covers optional extensions you can add when your project requires them.

## Extension: Dry-Run Wrapper

A **DryRun wrapper** intercepts write operations and prints what would happen, while delegating read operations to the wrapped implementation. This is useful for CLI tools with a `--dry-run` flag.

### Pattern

```python
class DryRunDatabaseGateway(DatabaseGateway):
    """Wrapper that prints instead of executing writes."""

    def __init__(self, gateway: DatabaseGateway) -> None:
        self._gateway = gateway  # Wrap any implementation

    def query(self, sql: str) -> list[dict]:
        """Read operation: delegate to wrapped."""
        return self._gateway.query(sql)

    def execute(self, sql: str) -> None:
        """Write operation: print instead of executing."""
        print(f"[DRY RUN] Would execute: {sql}")
        # Does NOT call self._gateway.execute()
```

### Key Characteristics

- **Decorator pattern**: Wraps any gateway implementation (Real or Fake)
- **Read operations**: Pass through to wrapped implementation
- **Write operations**: Print `[DRY RUN]` message, don't execute
- **Same interface**: Implements the same ABC as Real and Fake

### Wiring

```python
def create_context(*, dry_run: bool) -> AppContext:
    database = RealDatabaseGateway(connection_string)
    if dry_run:
        database = DryRunDatabaseGateway(database)
    return AppContext(database=database)
```

### Testing Dry-Run

```python
def test_migration_dry_run(capsys) -> None:
    """Verify --dry-run doesn't modify data."""
    fake_db = FakeDatabaseGateway(
        users=[{"id": 1, "name": "Alice"}]
    )
    # Wrap fake with dry-run (same as production wraps real)
    dry_run_db = DryRunDatabaseGateway(fake_db)

    service = MigrationService(database=dry_run_db)
    service.migrate()

    # Write operations were intercepted
    assert len(fake_db.executed_commands) == 0
    captured = capsys.readouterr()
    assert "[DRY RUN]" in captured.out
```

### When to Add DryRun

Add a DryRun wrapper when:

- Your application has a `--dry-run` CLI flag
- Users need to preview what operations would do before executing
- Write operations are destructive or expensive

Most gateways do **not** need DryRun. Only add it for gateways whose mutations are user-facing and benefit from preview.

## Extension: Sub-Gateway Composition

When a gateway grows too large, extract related methods into sub-gateways accessed via properties:

```python
class GitGateway(ABC):
    """Main gateway: pure facade with property accessors."""

    @property
    @abstractmethod
    def branch(self) -> GitBranchOps:
        """Access branch operations."""

    @property
    @abstractmethod
    def remote(self) -> GitRemoteOps:
        """Access remote operations."""

class RealGitGateway(GitGateway):
    def __init__(self) -> None:
        self._branch = RealGitBranchOps()
        self._remote = RealGitRemoteOps()

    @property
    def branch(self) -> GitBranchOps:
        return self._branch

    @property
    def remote(self) -> GitRemoteOps:
        return self._remote
```

### When to Use Sub-Gateways

- Gateway has 15+ methods spanning distinct domains
- Methods naturally cluster (branch ops, remote ops, status ops)
- You want to inject only a subset of operations in some tests

### The Fake Shares State

```python
class FakeGitGateway(GitGateway):
    def __init__(self, *, branches: list[str] | None = None) -> None:
        # Shared state
        self._branches = branches or []
        # Sub-gateways share state
        self._branch_ops = FakeGitBranchOps(branches=self._branches)
        self._remote_ops = FakeGitRemoteOps(branches=self._branches)

    @property
    def branch(self) -> GitBranchOps:
        return self._branch_ops

    @property
    def remote(self) -> GitRemoteOps:
        return self._remote_ops
```

## Related Documentation

- `gateway-architecture.md` - Core gateway pattern
- `patterns.md` - Constructor injection and mutation tracking
- `testing-strategy.md` - Which layer to test at
