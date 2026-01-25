---
title: Gateway ABC Implementation Checklist
read_when:
  - "adding or modifying methods in any gateway ABC interface (Git, GitHub, Graphite)"
  - "implementing new gateway operations"
  - "composing one gateway inside another (e.g., GitHub composing GitHubIssues)"
tripwires:
  - action: "adding a new method to Git ABC"
    warning: "Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py."
  - action: "adding a new method to GitHub ABC"
    warning: "Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py."
  - action: "adding a new method to Graphite ABC"
    warning: "Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py."
  - action: "adding subprocess.run or run_subprocess_with_context calls to a gateway real.py file"
    warning: "Must add integration tests in tests/integration/test_real_*.py. Real gateway methods with subprocess calls need tests that verify the actual subprocess behavior."
  - action: "using subprocess.run with git command outside of a gateway"
    warning: "Use the Git gateway instead. Direct subprocess calls bypass testability (fakes) and dry-run support. The Git ABC (erk_shared.git.abc.Git) likely already has a method for this operation. Only use subprocess directly in real.py gateway implementations."
---

# Gateway ABC Implementation Checklist

All gateway ABCs (Git, GitHub, Graphite) follow the same 5-file pattern. When adding a new method to any gateway, you must implement it in **5 places**:

## Scope

**These rules apply to production erk code** in `src/erk/` and `packages/erk-shared/`.

**Exception: erk-dev** (`packages/erk-dev/`) is developer tooling and is exempt from these rules. Direct `subprocess.run` with git commands is acceptable in erk-dev since it doesn't need gateway abstractions for its own operations.

| Implementation | Purpose                                              |
| -------------- | ---------------------------------------------------- |
| `abc.py`       | Abstract method definition (contract)                |
| `real.py`      | Production implementation (subprocess/API calls)     |
| `fake.py`      | Constructor-injected test data (unit tests)          |
| `dry_run.py`   | Delegates read-only, no-ops mutations (preview mode) |
| `printing.py`  | Delegates to wrapped, prints mutations (verbose)     |

## Gateway Locations

| Gateway   | Location                                                |
| --------- | ------------------------------------------------------- |
| Git       | `packages/erk-shared/src/erk_shared/git/`               |
| GitHub    | `packages/erk-shared/src/erk_shared/github/`            |
| Graphite  | `packages/erk-shared/src/erk_shared/gateway/graphite/`  |
| Codespace | `packages/erk-shared/src/erk_shared/gateway/codespace/` |

## Simplified Gateway Pattern (3 Files)

Some gateways don't benefit from dry-run or printing wrappers. The Codespace gateway uses a simplified 3-file pattern:

| Implementation | Purpose                    |
| -------------- | -------------------------- |
| `abc.py`       | Abstract method definition |
| `real.py`      | Production implementation  |
| `fake.py`      | Test double                |

**When to use 3-file pattern:**

- Process replacement operations (`os.execvp`) where dry-run doesn't apply
- External SSH/remote execution where "printing" the command isn't useful
- Operations that are inherently all-or-nothing

**Example:** Codespace SSH execution replaces the current process, so there's no meaningful "dry-run" - you either exec into the codespace or you don't.

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

## Concrete Example: Adding a Parameter to an Existing Method

PR #5739 demonstrates adding a `force: bool` parameter to `GitBranchOps.create_branch()`. This shows the 5-file update pattern for modifying an existing method signature.

### The Change

The `create_branch()` method signature changed from:

```python
def create_branch(self, cwd: Path, branch_name: str, start_point: str) -> None
```

To:

```python
def create_branch(self, cwd: Path, branch_name: str, start_point: str, *, force: bool) -> None
```

This enables callers to force-update branches when needed (e.g., auto-fixing diverged parents).

### Step 1: ABC Signature (abc.py)

Update the abstract method with the new parameter:

```python
@abstractmethod
def create_branch(
    self, cwd: Path, branch_name: str, start_point: str, *, force: bool
) -> None:
    """Create a branch, optionally force-updating if it exists.

    Args:
        cwd: Working directory
        branch_name: Name of branch to create
        start_point: Commit/branch to base the new branch on
        force: Use -f flag to move existing branch to start_point
    """
    ...
```

### Step 2: Real Implementation (real.py)

Pass force flag to subprocess command:

```python
def create_branch(
    self, cwd: Path, branch_name: str, start_point: str, *, force: bool
) -> None:
    """Create a new branch without checking it out."""
    cmd = ["git", "branch"]
    if force:
        cmd.append("-f")
    cmd.extend([branch_name, start_point])
    run_subprocess_with_context(
        cmd=cmd,
        operation_context=f"create branch '{branch_name}' from '{start_point}'",
        cwd=cwd,
    )
```

### Step 3: Fake Implementation (fake.py)

Update mutation tracking tuple to include the new parameter:

```python
def __init__(self, ...) -> None:
    # Mutation tracking: (cwd, branch_name, start_point, force)
    self._created_branches: list[tuple[Path, str, str, bool]] = []

def create_branch(
    self, cwd: Path, branch_name: str, start_point: str, *, force: bool
) -> None:
    """Record branch creation for test assertions."""
    self._created_branches.append((cwd, branch_name, start_point, force))

@property
def created_branches(self) -> list[tuple[Path, str, str, bool]]:
    """Get list of branches created during test."""
    return self._created_branches.copy()
```

**CRITICAL**: This changes the tuple format from 3-tuple to 4-tuple, affecting all test assertions that unpack this tuple. See [Mutation Tracking Test Patterns](../testing/mutation-tracking-patterns.md) for how to handle cascading updates.

### Step 4: DryRun Implementation (dry_run.py)

No-op in dry-run mode (show what would happen, don't execute):

```python
def create_branch(
    self, cwd: Path, branch_name: str, start_point: str, *, force: bool
) -> None:
    """Print dry-run message instead of creating branch."""
    force_flag = " -f" if force else ""
    user_output(
        f"[DRY RUN] Would run: git branch{force_flag} {branch_name} {start_point}"
    )
```

### Step 5: Printing Implementation (printing.py)

Delegate to wrapped implementation while optionally printing:

```python
def create_branch(
    self, cwd: Path, branch_name: str, start_point: str, *, force: bool
) -> None:
    """Create branch (delegates to wrapped)."""
    self._wrapped.create_branch(
        cwd, branch_name, start_point, force=force
    )
```

### Cascade to Callers

All callers must be updated to pass the new parameter. Callers decide when to use `force=True`:

```python
# In GitBranchManager.create_branch()
self._git_branch_ops.create_branch(
    repo_root, branch_name, base_branch, force=False  # Normal creation
)

# In GraphiteBranchManager._ensure_local_matches_remote()
self._git_branch_ops.create_branch(
    repo_root, local_branch, f"origin/{local_branch}", force=True  # Auto-fix divergence
)
```

### Key Insights

1. **Parameter consistency**: The same `force` parameter must appear in all 5 implementations
2. **Tuple expansion**: Fake's mutation tuple expands, affecting 8+ test files
3. **Caller responsibility**: Each caller decides when to use `force=True`
4. **Safety properties**: Force-update is only safe in specific contexts (documented in [Force Flag Design](force-flags.md))

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

## Gateway Composition

When one gateway composes another (e.g., GitHub composes GitHubIssues), follow these patterns:

### ABC: Abstract Property

```python
class GitHub(ABC):
    @property
    @abstractmethod
    def issues(self) -> GitHubIssues:
        """Return the composed GitHubIssues gateway."""
        ...
```

### Real: Compose Real + Factory Method

```python
class RealGitHub(GitHub):
    def __init__(self, time: Time, repo_info: RepoInfo | None, *, issues: GitHubIssues) -> None:
        self._issues = issues
        # ...

    @property
    def issues(self) -> GitHubIssues:
        return self._issues

    @classmethod
    def for_test(cls, *, time: Time | None = None, repo_info: RepoInfo | None = None) -> "RealGitHub":
        """Factory for tests that need Real implementation with sensible defaults."""
        from erk_shared.gateway.time.fake import FakeTime
        from erk_shared.github.issues import RealGitHubIssues
        effective_time = time if time is not None else FakeTime()
        return cls(
            time=effective_time,
            repo_info=repo_info,
            issues=RealGitHubIssues(target_repo=None, time=effective_time),
        )
```

### Fake: Separate Data vs Gateway Parameters

**Critical**: Use distinct parameter names to avoid collision:

- `foo_data` for test data (e.g., `issues_data: list[IssueInfo]`)
- `foo_gateway` for composed gateway (e.g., `issues_gateway: GitHubIssues`)

```python
class FakeGitHub(GitHub):
    def __init__(
        self,
        *,
        issues_data: list[IssueInfo] | None = None,  # Test data for internal use
        issues_gateway: GitHubIssues | None = None,  # Composed gateway
    ) -> None:
        self._issues_data = issues_data or []
        self._issues_gateway = issues_gateway or FakeGitHubIssues()

    @property
    def issues(self) -> GitHubIssues:
        return self._issues_gateway
```

### DryRun: Compose DryRun Variant Internally

```python
class DryRunGitHub(GitHub):
    def __init__(self, wrapped: GitHub) -> None:
        self._wrapped = wrapped
        self._issues = DryRunGitHubIssues(wrapped.issues)

    @property
    def issues(self) -> GitHubIssues:
        return self._issues
```

### Printing: Delegate to Wrapped

```python
class PrintingGitHub(GitHub):
    @property
    def issues(self) -> GitHubIssues:
        return self._wrapped.issues
```

## Common Pitfall

**Printing implementations often fall behind** - when adding a new method, verify PrintingGit/PrintingGitHub/PrintingGraphite is updated alongside the other implementations.

## Dependency Injection for Testability

When adding methods that benefit from testability (lock waiting, retry logic, timeouts), consider injecting dependencies via constructor rather than adding parameters to each method.

**Example Pattern** (from `RealGit`):

```python
class RealGit(Git):
    def __init__(self, *, time: Time | None = None) -> None:
        # Accept optional dependency, default to production implementation
        self._time = time if time is not None else RealTime()

    def checkout_branch(self, repo_root: Path, branch: str) -> None:
        # Use injected dependency before operation
        wait_for_index_lock(repo_root, self._time)
        # ... actual git operation
```

**Benefits**:

- Centralizes all dependencies in one place (constructor)
- Enables testing with `FakeTime` without blocking in unit tests
- Consistent with erk's dependency injection pattern for all gateways
- Lock-waiting and retry logic execute instantly in tests

**Reference Implementation**: `packages/erk-shared/src/erk_shared/git/lock.py` and `packages/erk-shared/src/erk_shared/git/real.py`

## Sub-Gateway Pattern for Method Extraction

When a subset of gateway methods needs to be accessed through a higher-level abstraction (like BranchManager), extract them into a sub-gateway.

### Motivation

The BranchManager abstraction handles Graphite vs Git differences. To enforce that callers use BranchManager for branch mutations (not raw gateways), mutation methods were extracted into sub-gateways:

- `GitBranchOps`: Branch mutations from Git ABC
- `GraphiteBranchOps`: Branch mutations from Graphite ABC

Query methods remain on the main gateways for convenience.

### Sub-Gateway Structure

```
packages/erk-shared/src/erk_shared/git/
├── abc.py             # Main Git ABC (queries + branch_ops property)
├── branch_ops/        # Sub-gateway for mutations
│   ├── __init__.py
│   ├── abc.py         # GitBranchOps ABC
│   ├── real.py
│   ├── fake.py
│   ├── dry_run.py
│   └── printing.py
```

### ABC Composition

The main gateway ABC exposes the sub-gateway via a property:

```python
class Git(ABC):
    @property
    @abstractmethod
    def branch_ops(self) -> GitBranchOps:
        """Return the branch operations sub-gateway."""
        ...

    # Query methods remain here
    @abstractmethod
    def get_current_branch(self, cwd: Path) -> str:
        ...
```

### Query vs Mutation Split

| Category | Where       | Examples                                                                 |
| -------- | ----------- | ------------------------------------------------------------------------ |
| Query    | Main ABC    | `get_current_branch()`, `list_local_branches()`, `get_repository_root()` |
| Mutation | Sub-gateway | `create_branch()`, `delete_branch()`, `checkout_branch()`                |

### Why Split?

1. **Enforcement**: Callers can't bypass BranchManager to mutate branches directly
2. **Clarity**: Clear distinction between read and write operations
3. **Testing**: FakeBranchManager can track mutations without full gateway wiring

### Implementation Checklist

When extracting methods to a sub-gateway:

1. [ ] Create sub-gateway directory (`branch_ops/`)
2. [ ] Implement 5 files: abc.py, real.py, fake.py, dry_run.py, printing.py
3. [ ] Add `@property` to main ABC returning sub-gateway
4. [ ] Update all 5 main gateway implementations to compose sub-gateway
5. [ ] Create factory method in Fake to link sub-gateway state

### FakeGit/FakeGraphite Sub-Gateway Linking

Fakes need special handling to share state between main gateway and sub-gateway:

```python
class FakeGit(Git):
    def __init__(self) -> None:
        self._branch_ops = FakeGitBranchOps()

    @property
    def branch_ops(self) -> GitBranchOps:
        return self._branch_ops

    @classmethod
    def create_linked_branch_ops(cls) -> tuple["FakeGit", FakeGitBranchOps]:
        """Create FakeGit with linked FakeGitBranchOps for testing.

        Returns both so tests can assert on branch_ops mutations.
        """
        fake = cls()
        return fake, fake._branch_ops
```

### Reference Implementation

- Git sub-gateway: `packages/erk-shared/src/erk_shared/git/branch_ops/`
- Graphite sub-gateway: `packages/erk-shared/src/erk_shared/gateway/graphite/branch_ops/`

## Time Injection for Retry-Enabled Gateways

Gateways that implement retry logic need Time dependency injection for testability.

### Pattern

Accept optional `Time` in `__init__` with default to `RealTime()`:

```python
class RealGitHub(GitHub):
    def __init__(self, time: Time, repo_info: RepoInfo | None, ...) -> None:
        from erk_shared.gateway.time.real import RealTime
        self._time = time if time is not None else RealTime()

    def fetch_with_retry(self, ...) -> str:
        return execute_gh_command_with_retry(cmd, cwd, self._time)
```

### Benefits

- Tests use `FakeTime` - retry loops complete instantly
- Retry delays can be asserted in tests
- Consistent with erk's DI pattern

See [GitHub API Retry Mechanism](github-api-retry-mechanism.md) for the full retry pattern.

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
