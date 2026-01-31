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
  - action: "removing an abstract method from a gateway ABC"
    warning: "Must remove from 5 places simultaneously: abc.py, real.py, fake.py, dry_run.py, printing.py. Partial removal causes type checker errors. Update all call sites to use subgateway property. Verify with grep across packages."
  - action: "adding subprocess.run or run_subprocess_with_context calls to a gateway real.py file"
    warning: "Must add integration tests in tests/integration/test_real_*.py. Real gateway methods with subprocess calls need tests that verify the actual subprocess behavior."
  - action: "using subprocess.run with git command outside of a gateway"
    warning: "Use the Git gateway instead. Direct subprocess calls bypass testability (fakes) and dry-run support. The Git ABC (erk_shared.gateway.git.abc.Git) likely already has a method for this operation. Only use subprocess directly in real.py gateway implementations."
  - action: "changing gateway return type to discriminated union"
    warning: "Verify all 5 implementations import the new types. Missing imports in abc.py, fake.py, dry_run.py, or printing.py break the gateway pattern."
  - action: "designing error handling for a new gateway method"
    warning: "Ask: does the caller continue after the failure? If yes, use discriminated union. If all callers terminate, use exceptions. See 'Non-Ideal State Decision Checklist' section."
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
| Git       | `packages/erk-shared/src/erk_shared/gateway/git/`       |
| GitHub    | `packages/erk-shared/src/erk_shared/gateway/github/`    |
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

## Non-Ideal State Decision Checklist

When designing error handling for a new gateway method, the key question is: **does the caller continue after the failure?**

This checklist helps you choose between discriminated unions and exceptions. For full pattern documentation, see [Discriminated Union Error Handling](discriminated-union-error-handling.md).

### Decision: Discriminated Union or Exception?

| Question                                                                        | If Yes              | If No               |
| ------------------------------------------------------------------------------- | ------------------- | ------------------- |
| Does at least one caller branch on the error and continue with different logic? | Discriminated union | Exception           |
| Does the error carry domain-meaningful fields beyond just `message`?            | Discriminated union | Exception           |
| Do all callers terminate on failure (extract message and stop)?                 | Exception           | Discriminated union |

### Checklist: Use a Discriminated Union When

- [ ] At least one caller branches on the error and continues with different logic
- [ ] Error type carries domain-meaningful fields beyond just `message`
- [ ] Error type implements the `NonIdealState` protocol (`error_type` + `message` properties) from `erk_shared.non_ideal_state`
- [ ] Type defined as `@dataclass(frozen=True)` in the gateway's `types.py` file
- [ ] All 5 implementations updated (abc, real, fake, dry_run, printing)

### Checklist: Use Exceptions When

- [ ] All callers terminate on failure (extract message and stop)
- [ ] No caller inspects error type or branches on error content
- [ ] Use `UserFacingCliError` at CLI boundary

### NonIdealState Protocol

All discriminated union error types must implement the `NonIdealState` protocol from `erk_shared.non_ideal_state`:

```python
class NonIdealState(Protocol):
    @property
    def error_type(self) -> str: ...

    @property
    def message(self) -> str: ...
```

### Type Colocation Rule

Non-ideal state types live in the gateway's `types.py` file, alongside the success types:

| Gateway        | Types location                                                       |
| -------------- | -------------------------------------------------------------------- |
| GitHub         | `packages/erk-shared/src/erk_shared/gateway/github/types.py`         |
| Git branch_ops | `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/types.py` |
| Git remote_ops | `packages/erk-shared/src/erk_shared/gateway/git/remote_ops/types.py` |
| BranchManager  | `packages/erk-shared/src/erk_shared/gateway/branch_manager/types.py` |

### Codebase Examples

**Methods using discriminated unions** (callers branch on error):

| Method           | Return type                                 | Gateway        |
| ---------------- | ------------------------------------------- | -------------- |
| `merge_pr`       | `MergeResult \| MergeError`                 | GitHub         |
| `push_to_remote` | `PushResult \| PushError`                   | Git remote_ops |
| `pull_rebase`    | `PullRebaseResult \| PullRebaseError`       | Git remote_ops |
| `create_branch`  | `CreateBranchResult \| BranchAlreadyExists` | Git branch_ops |
| `submit_branch`  | `SubmitBranchResult \| SubmitBranchError`   | BranchManager  |

**Methods using exceptions** (all callers terminate):

| Method              | Exception       | Why                                                         |
| ------------------- | --------------- | ----------------------------------------------------------- |
| Worktree add/remove | `WorktreeError` | No caller inspects error content; all terminate identically |
| HTTP operations     | `HttpError`     | Generic transport failure; callers just surface the message |

## Return Type Changes

When changing an existing gateway method's return type (e.g., converting from exception-based to discriminated union), follow this comprehensive migration pattern:

**Complete Update Checklist**:

1. [ ] Define new types in `gateway/{name}/types.py`
2. [ ] Update ABC signature in `abc.py`
3. [ ] Update all 5 implementations:
   - [ ] `real.py` - Return appropriate error types for failure cases
   - [ ] `fake.py` - Return union types in test implementation
   - [ ] `dry_run.py` - Return appropriate success/error based on mode
   - [ ] `printing.py` - Update signature to return union
4. [ ] Update all call sites to handle new return type
5. [ ] Update tests to check `isinstance(result, ErrorType)`
6. [ ] Verify all imports include new types

**Canonical Examples**:

1. **PR #6294** (`merge_pr: bool | str` → `MergeResult | MergeError`):
   - Changed 4 files in gateway implementations
   - Updated 3 call sites in land workflow
   - Updated tests to use `isinstance(result, MergeError)`

2. **PR #6348** (Phase 4: Branch/Worktree Creation):
   - `create_branch()` - Exception-based → `CreateBranchResult` discriminated union
   - `add_worktree()` - Exception-based → `AddWorktreeResult` discriminated union
   - Updated all 5 implementations (real, fake, dry_run, printing, abc)
   - Updated call sites to handle `type` discriminant checking
   - Updated tests with fake error simulation patterns

**Critical**: Incomplete migrations break type safety. Use grep to find all call sites before starting.

## Canonical Examples: Worktree Gateway Conversions

The worktree sub-gateway provides concrete examples of discriminated union conversions following the NonIdealState protocol pattern.

### add_worktree: None → WorktreeAdded | WorktreeAddError

**Before** (exception-based):

```python
# abc.py
@abstractmethod
def add_worktree(self, *, repo_root: Path, path: Path, branch: str) -> None:
    """Add a new worktree. Raises WorktreeAddError on failure."""
```

**After** (discriminated union):

```python
# types.py - Define success and error types
@dataclass(frozen=True)
class WorktreeAdded:
    """Success result from adding a worktree."""
    path: Path
    branch: str

@dataclass(frozen=True)
class WorktreeAddError:
    """Error result from adding a worktree. Implements NonIdealState."""
    path: Path
    branch: str
    message: str

    @property
    def error_type(self) -> str:
        return "worktree-add-failed"

# abc.py - Update signature
@abstractmethod
def add_worktree(self, *, repo_root: Path, path: Path, branch: str) -> WorktreeAdded | WorktreeAddError:
    """Add a new worktree. Returns WorktreeAdded on success, WorktreeAddError on failure."""
```

**5-Place Implementation**:

| File           | Update                                                                         |
| -------------- | ------------------------------------------------------------------------------ |
| `types.py`     | Define `WorktreeAdded` and `WorktreeAddError` dataclasses                      |
| `abc.py`       | Update abstract method signature to return union                               |
| `real.py`      | Parse subprocess errors, return `WorktreeAddError` for failures                |
| `fake.py`      | Add `add_worktree_error: WorktreeAddError \| None` parameter, check first      |
| `dry_run.py`   | Return `WorktreeAdded` (no-op)                                                 |
| `printing.py`  | Update signature to return union                                               |
| **Call sites** | Replace try/except with `isinstance(result, WorktreeAddError)`                 |
| **Tests**      | Update to check `isinstance(result, WorktreeAddError)` instead of catching exc |

**Fake implementation pattern**:

```python
# fake.py
class FakeGitWorktree(GitWorktree):
    def __init__(
        self,
        *,
        add_worktree_error: WorktreeAddError | None = None,
    ) -> None:
        self._add_worktree_error = add_worktree_error

    def add_worktree(self, *, repo_root: Path, path: Path, branch: str) -> WorktreeAdded | WorktreeAddError:
        # Check injected error FIRST (before any success logic)
        if self._add_worktree_error is not None:
            return self._add_worktree_error

        # Success path
        return WorktreeAdded(path=path, branch=branch)
```

**Call site migration** (18 call sites throughout codebase):

```python
# Before
try:
    ops.git_worktree.add_worktree(repo_root=root, path=wt_path, branch=branch)
except WorktreeAddError as e:
    return SetupError(error_type="worktree-creation-failed", message=str(e))

# After
result = ops.git_worktree.add_worktree(repo_root=root, path=wt_path, branch=branch)
if isinstance(result, WorktreeAddError):
    return SetupError(
        error_type="worktree-creation-failed",
        message=f"Failed to create worktree at {wt_path}\n\n{result.message}",
    )
# Type narrowing: result is now WorktreeAdded
```

**Reference PR**: #6350 (add_worktree conversion)

### remove_worktree: None → WorktreeRemoved | WorktreeRemoveError

**Before** (exception-based):

```python
@abstractmethod
def remove_worktree(self, *, repo_root: Path, path: Path) -> None:
    """Remove a worktree. Raises WorktreeRemoveError on failure."""
```

**After** (discriminated union with mixed exception handling):

```python
# types.py
@dataclass(frozen=True)
class WorktreeRemoved:
    """Success result from removing a worktree."""
    path: Path

@dataclass(frozen=True)
class WorktreeRemoveError:
    """Error result from removing a worktree. Implements NonIdealState."""
    path: Path
    message: str

    @property
    def error_type(self) -> str:
        return "worktree-remove-failed"

# abc.py
@abstractmethod
def remove_worktree(self, *, repo_root: Path, path: Path) -> WorktreeRemoved | WorktreeRemoveError:
    """Remove a worktree. Returns WorktreeRemoved on success, WorktreeRemoveError on failure.

    Note: Cleanup operations like 'git worktree prune' may still raise exceptions
    if they fail, as this indicates corrupted repository state.
    """
```

**Key pattern**: Main operation returns discriminated union, but cleanup operations (like `git worktree prune`) remain exception-based because their failure indicates corrupted state. See [gateway-specific-patterns.md](gateway-specific-patterns.md) for details.

**LBYL violation fix**: Before this conversion, `delete_cmd.py:150-168` used `_remove_worktree_safe()` wrapper:

```python
# Before (LBYL violation)
def _remove_worktree_safe(ops: Operations, repo_root: Path, path: Path) -> None:
    """Remove worktree, catching errors."""
    try:
        ops.git_worktree.remove_worktree(repo_root=repo_root, path=path)
    except WorktreeRemoveError:
        pass  # Ignore errors
```

The discriminated union pattern eliminates the need for try/except wrappers - callers can use `isinstance()` checks instead:

```python
# After (LBYL-compliant)
result = ops.git_worktree.remove_worktree(repo_root=root, path=wt_path)
if isinstance(result, WorktreeRemoveError):
    click.echo(f"Warning: Failed to remove worktree: {result.message}", err=True)
```

**Call sites**: 12 total (4 production, 8 test)

**Reference PR**: #6346 (remove_worktree conversion)

### File Paths for Worktree Gateway

All implementations are in the worktree sub-gateway:

```
packages/erk-shared/src/erk_shared/gateway/git/worktree/
├── abc.py         # GitWorktree ABC with abstract methods
├── types.py       # WorktreeAdded, WorktreeAddError, WorktreeRemoved, WorktreeRemoveError
├── real.py        # Subprocess-based implementation
├── fake.py        # Test double with error injection
├── dry_run.py     # No-op wrapper returning success types
└── printing.py    # Verbose output wrapper
```

### NonIdealState Protocol Pattern

All error types implement the `NonIdealState` protocol from `remote_ops/types.py`:

```python
class NonIdealState(Protocol):
    @property
    def error_type(self) -> str:
        """Machine-readable error classification."""
        ...
```

This enables:

- Consistent error handling across gateways
- Type-safe error classification
- CLI output formatting from discriminated unions

### Cross-Reference

See [discriminated-union-error-handling.md](discriminated-union-error-handling.md) for complete examples of WorktreeAdded/WorktreeAddError and BranchCreated/BranchCreateError patterns with call site examples.

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

### LBYL Existence Methods

Some resources benefit from existence-check methods that enable Look Before You Leap validation. This pattern prevents cryptic errors when fetching non-existent resources.

**Examples**: `issue_exists`, `branch_exists`, `pr_exists`

**When to add existence methods:**

- When `get_X()` returns a sentinel (e.g., `PRNotFound`) rather than raising
- When callers frequently need to validate before operating on a resource
- When error messages from `get_X()` on missing resources are unclear

**Implementation pattern:**

```python
# abc.py - Simple boolean return
@abstractmethod
def issue_exists(self, repo_root: Path, number: int) -> bool:
    """Check if an issue exists (read-only)."""
    ...

# real.py - Lightweight check (avoid fetching full resource)
def issue_exists(self, repo_root: Path, number: int) -> bool:
    cmd = ["gh", "issue", "view", str(number), "--json", "number"]
    result = subprocess.run(cmd, cwd=repo_root, capture_output=True)
    return result.returncode == 0
```

**Caller usage (LBYL):**

```python
# Check existence before fetching
if not ctx.github.issues.issue_exists(repo.root, issue_number):
    user_output(f"Error: Issue #{issue_number} not found")
    raise SystemExit(1)

# Safe to fetch - we know it exists
issue = ctx.github.issues.get_issue(repo.root, issue_number)
```

See [LBYL Gateway Pattern](lbyl-gateway-pattern.md) for complete pattern documentation.

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

### Idempotent Mutations

**Pattern**: Some mutations should be idempotent - they succeed whether or not the resource exists. Examples: deleting a branch that's already gone, closing a PR that's already closed.

**Implementation**: Use LBYL (Look Before You Leap) to check existence before attempting the operation:

```python
# real.py - Check existence first, return early if missing
def delete_branch(self, repo_root: Path, branch_name: str) -> None:
    """Delete a local branch.

    Idempotent: if branch doesn't exist, returns successfully.
    """
    # LBYL check - does branch exist?
    result = run_subprocess_with_context(
        ["git", "show-ref", "--verify", f"refs/heads/{branch_name}"],
        cwd=repo_root,
        check=False,
    )

    if result.returncode != 0:
        # Branch doesn't exist - already in desired state
        return

    # Branch exists - proceed with deletion
    run_subprocess_with_context(
        ["git", "branch", "-D", branch_name],
        cwd=repo_root,
        check=True,
    )
```

**Key principle**: Use LBYL _to implement_ idempotency for operations that would otherwise fail on missing resources. This is different from operations that are _already_ idempotent (like `git fetch`), which don't need LBYL checks.

See the canonical implementation at `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/real.py:38-59`.

**5-file verification checklist** for idempotent behavioral changes:

1. **ABC** (`abc.py`) - Update docstring to document idempotent behavior
2. **Real** (`real.py`) - Add LBYL check and early return
3. **Fake** (`fake.py`) - Verify fake already handles idempotency (usually does)
4. **Integration test** (`tests/integration/test_real_*.py`) - Add test for missing resource case
5. **Unit tests** (`tests/unit/`) - Update any tests that assumed failure on missing resource

**Example integration test**:

```python
def test_delete_branch_idempotent_when_branch_missing() -> None:
    """delete_branch should succeed even if branch doesn't exist."""
    ctx = create_context(dry_run=False, script_mode=True)
    repo_root = create_temp_git_repo()

    # Don't create the branch - just try to delete it
    ctx.git.branch.delete_branch(repo_root, "nonexistent-branch")

    # Should not raise - idempotent operation
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
        from erk_shared.gateway.github.issues import RealGitHubIssues
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

**Reference Implementation**: `packages/erk-shared/src/erk_shared/gateway/git/lock.py` and `packages/erk-shared/src/erk_shared/gateway/git/real.py`

## Sub-Gateway Pattern for Method Extraction

When a subset of gateway methods needs to be accessed through a higher-level abstraction (like BranchManager), extract them into a sub-gateway.

### Motivation

The BranchManager abstraction handles Graphite vs Git differences. To enforce that callers use BranchManager for branch mutations (not raw gateways), mutation methods were extracted into sub-gateways:

- `GitBranchOps`: Branch mutations from Git ABC
- `GraphiteBranchOps`: Branch mutations from Graphite ABC

Query methods remain on the main gateways for convenience.

### Sub-Gateway Structure

```
packages/erk-shared/src/erk_shared/gateway/git/
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

### Reference Implementations

Sub-gateways for branch mutations:

- Git branch_ops: `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/`
- Graphite branch_ops: `packages/erk-shared/src/erk_shared/gateway/graphite/branch_ops/`

Sub-gateway for worktree operations:

- Git worktree: `packages/erk-shared/src/erk_shared/gateway/git/worktree/`

The worktree sub-gateway follows the same 5-file pattern with methods: `list_worktrees()`, `add_worktree()`, `move_worktree()`, `remove_worktree()`, `prune_worktrees()`, `find_worktree_for_branch()`.

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

## Callback Injection for Subgateway Dependencies

When a subgateway needs to call methods from sibling subgateways or the parent gateway, use callback injection to avoid circular imports.

### Pattern

Pass parent methods as `Callable` parameters in the constructor:

```python
class RealGitRebaseOps(GitRebaseOps):
    def __init__(
        self,
        get_git_common_dir: Callable[[Path], Path],
        get_conflicted_files: Callable[[Path], list[str]],
    ) -> None:
        self._get_git_common_dir = get_git_common_dir
        self._get_conflicted_files = get_conflicted_files
```

### Why Not Direct Imports?

Direct imports would create circular dependencies:

- `rebase_ops/real.py` imports `status_ops/abc.py`
- `status_ops/real.py` imports common types
- Common types import `git/abc.py`
- `git/abc.py` imports `rebase_ops/abc.py`

Callback injection breaks this cycle by deferring the dependency to runtime.

### Reference Implementation

`RealGitRebaseOps` in `packages/erk-shared/src/erk_shared/gateway/git/rebase_ops/real.py` demonstrates this pattern.

## Integration with Fake-Driven Testing

This pattern aligns with the [Fake-Driven Testing Architecture](../testing/):

- **Real**: Layer 5 (Business Logic Integration Tests) - production implementation
- **Fake**: Layer 4 (Business Logic Tests) - in-memory test double for fast tests
- **DryRun**: Preview mode for CLI operations
- **Printing**: Verbose output for debugging

## Reference Implementation: BeadsGateway

For new service integrations, the BeadsGateway (`packages/erk-shared/src/erk_shared/gateway/beads/`) provides a clean 5-file pattern example:

```
beads/
├── abc.py        # Abstract interface
├── real.py       # Production implementation
├── fake.py       # Test double with builder pattern
├── dry_run.py    # Preview mode wrapper
└── printing.py   # Verbose output wrapper
```

**Key patterns demonstrated:**

- Service integration via HTTP/API calls
- Test fake with fluent builder for state setup
- Dry-run wrapper that returns mock success values
- Printing wrapper that logs then delegates

## ABC Method Removal Pattern

When removing dead convenience methods from gateway ABCs (methods with zero production callers), follow this synchronization pattern.

### When to Remove Methods

Remove methods that meet ALL these criteria:

1. **Zero production callers** - No code in `src/erk/` or `packages/erk-shared/` uses the method
2. **Convenience wrapper** - Method just forwards to a subgateway property (e.g., `git.method()` → `git.subgateway.method()`)
3. **Dead code** - Not part of the core gateway contract

### 5-Place Synchronization Requirement

When removing a method from an ABC, you MUST remove it from all 5 implementations simultaneously:

1. `abc.py` - Remove abstract method definition
2. `real.py` - Remove production implementation
3. `fake.py` - Remove fake implementation
4. `dry_run.py` - Remove dry-run implementation
5. `printing.py` - Remove printing implementation

**Partial removal causes type checker errors** - if you remove from abc.py but forget printing.py, the type checker will complain that PrintingGit doesn't implement the abstract method.

### Caller Migration Pattern

Before removing, migrate all call sites to use the subgateway property:

```python
# Before (convenience method)
current_branch = git.get_current_branch(repo_root)

# After (subgateway property)
current_branch = git.branch.get_current_branch(repo_root)
```

### Verification Steps

After removing a method:

1. Run type checker (`ty`) to verify no abstract method errors
2. Grep across packages for the removed method name:
   ```bash
   grep -r "removed_method_name" src/ packages/
   ```
3. Ensure zero matches in production code (tests may still reference for historical reasons)

### Example: Git ABC Cleanup

PR #6285 removed 16 methods from the Git ABC:

- **14 convenience methods** (e.g., `get_current_branch`, `create_branch`, `delete_branch`)
- **2 rebase methods** (`rebase_onto`, `rebase_abort`)

**Migration mapping**:

| Removed Method         | Migrated To                       |
| ---------------------- | --------------------------------- |
| `get_current_branch()` | `git.branch.get_current_branch()` |
| `create_branch()`      | `git.branch.create_branch()`      |
| `delete_branch()`      | `git.branch.delete_branch()`      |
| `rebase_onto()`        | `git.rebase.rebase_onto()`        |

**Result**: Git ABC reduced to exactly 10 abstract property accessors (pure facade pattern).

### Rationale: Pure Facade Goal

Gateway ABCs should contain ONLY property accessors to subgateways, not convenience methods. This enforces:

- **Clear ownership** - Each operation belongs to exactly one subgateway
- **Discoverability** - Callers navigate through properties (IDE autocomplete)
- **Maintainability** - Fewer methods = smaller surface area

### Periodic Audit Recommendation

Convenience methods accumulate over time as new subgateways are added. Periodically audit gateway ABCs for methods that could be removed:

1. Search for methods that delegate to subgateways
2. Check for zero production callers
3. Batch removal in a single PR (maintain 5-file synchronization)

### Reference Implementation

PR #6285: [Remove rebase_onto/rebase_abort from Git ABC and dead convenience methods from PrintingGit](https://github.com/owner/repo/pull/6285)

This PR demonstrates:

- 5-place synchronization (abc, real, fake, dry_run, printing)
- Caller migration to subgateway properties
- Verification via grep across packages

## Reference Implementation: Git Remote Ops (5-Place Pattern)

The `remote_ops/` sub-gateway provides a clean example of the 5-place pattern with discriminated union return types:

```
packages/erk-shared/src/erk_shared/gateway/git/remote_ops/
├── abc.py        # push_to_remote() -> PushResult | PushError
├── real.py       # try/except boundary, subprocess calls
├── fake.py       # Constructor-injected errors, mutation tracking
├── dry_run.py    # Returns PushResult() without executing
└── printing.py   # Logs then delegates
```

Key patterns demonstrated:

- **Discriminated union returns**: Methods return `Success | Error` instead of raising
- **Error boundary in real.py**: `try/except RuntimeError` converts to `PushError`
- **Fake configuration**: `FakeGitRemoteOps(push_to_remote_error=PushError(...))` injects failures
- **Mutation tracking**: `fake.pushed_branches` records successful pushes for test assertions

See PR #6329 for the migration that introduced this pattern.

## Reference: PR #6300 Gateway Consolidation

PR #6300 refactored PR submission from a monolithic function to a gateway-backed pipeline architecture. This established:

- Sub-gateway extraction for branch operations (`branch_ops/`)
- Pipeline step functions that consume gateways through `ErkContext`
- The pattern of gateway methods returning discriminated unions consumed by pipeline steps

## Related Documentation

- [Erk Architecture Patterns](erk-architecture.md) - Dependency injection, dry-run patterns
- [Protocol vs ABC](protocol-vs-abc.md) - Why gateways use ABC instead of Protocol
- [Subprocess Wrappers](subprocess-wrappers.md) - How Real implementations wrap subprocess calls
- [GitHub GraphQL Patterns](github-graphql.md) - GraphQL mutation patterns for GitHub
- [Gateway Error Boundaries](gateway-error-boundaries.md) - Where exceptions become discriminated unions
- [Gateway Signature Migration](gateway-signature-migration.md) - How to update all call sites when signatures change
