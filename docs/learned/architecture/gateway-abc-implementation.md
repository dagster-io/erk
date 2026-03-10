---
title: Gateway ABC Implementation Checklist
last_audited: "2026-02-15 18:50 PT"
audit_result: clean
read_when:
  - "adding or modifying methods in any gateway ABC interface (Git, GitHub, Graphite)"
  - "implementing new gateway operations"
  - "composing one gateway inside another (e.g., GitHub composing GitHubIssues)"
tripwires:
  - action: "creating a new gateway ABC"
    warning: "Default is 3-file pattern (abc.py, real.py, fake.py). Only add dry_run.py if the gateway participates in a user-facing --dry-run feature. Most gateways do not."
  - action: "adding a new method to a dry-run-enabled gateway ABC (Git, LocalGitHub, Graphite)"
    warning: "Must implement in 4 places: abc.py, real.py, fake.py, dry_run.py."
  - action: "adding a new method to a 3-file gateway ABC"
    warning: "Must implement in 3 places: abc.py, real.py, fake.py."
  - action: "removing an abstract method from a gateway ABC"
    warning: "Must remove from all implementation files simultaneously (3 or 4 depending on pattern). Partial removal causes type checker errors. Update all call sites. Verify with grep across packages."
  - action: "adding subprocess.run or run_subprocess_with_context calls to a gateway real.py file"
    warning: "Must add integration tests in tests/integration/test_real_*.py. Real gateway methods with subprocess calls need tests that verify the actual subprocess behavior."
    pattern: "subprocess\\.run\\(|run_subprocess_with_context\\("
  - action: "making N sequential gh api calls in a loop when a single GraphQL query could fetch all data"
    warning: "Each gh subprocess call costs ~200-300ms overhead. Batch into a single GraphQL query with node fragments when fetching multiple items. See http-accelerated-plan-refresh.md for the dual-path pattern."
  - action: "using subprocess.run with git command outside of a gateway"
    warning: "Use the Git gateway instead. Direct subprocess calls bypass testability (fakes) and dry-run support. The Git ABC (erk_shared.gateway.git.abc.Git) likely already has a method for this operation. Only use subprocess directly in real.py gateway implementations."
    pattern: "subprocess\\.run\\(\\s*\\[.*[\"']git"
  - action: "changing gateway return type to discriminated union"
    warning: "Verify all implementations import the new types. For 4-file gateways: abc.py, real.py, fake.py, dry_run.py. For 3-file gateways: abc.py, real.py, fake.py."
  - action: "designing error handling for a new gateway method"
    warning: "Ask: does the caller continue after the failure? If yes, use discriminated union. If all callers terminate, use exceptions. See 'Non-Ideal State Decision Checklist' section."
  - action: "adding a new parameter to a gateway ABC method"
    warning: "All implementations must be updated (3 or 4 depending on pattern). Fake may accept but not track new parameters when assertion is not needed for tests."
  - action: "creating a gateway named ShellRunner, CommandRunner, SubprocessGateway, or similar mechanism-named gateway"
    warning: "Gateway names must reflect the TOOL being wrapped, not the execution mechanism. Use LocalGitHub for gh calls, Git for git calls, CmuxGateway for cmux calls, PromptExecutor for claude calls. A mechanism-named gateway is just moving the mock up one layer without gaining abstraction."
  - action: "creating a new gateway directory under packages/erk-shared/src/erk_shared/gateway/"
    warning: "Must also wire into ErkContext: add field to context.py dataclass, add parameter to for_test(), and wire Real* in production factory (src/erk/core/context.py). See 'New Gateway: ErkContext Wiring' section."
---

# Gateway ABC Implementation Checklist

## Scope

**These rules apply to production erk code** in `src/erk/` and `packages/erk-shared/`.

**Exception: erk-dev** (`packages/erk-dev/`) is developer tooling and is exempt from these rules. Direct `subprocess.run` with git commands is acceptable in erk-dev since it doesn't need gateway abstractions for its own operations.

## Naming Gateways

Gateways are named after the **tool or service** they wrap, not the **mechanism** used. `subprocess.run` is the mechanism; the gateway is named `Git`, `LocalGitHub`, `CmuxGateway`, etc.

If your gateway name ends in `Runner`, `Shell`, or `Subprocess` — or `Executor` unless it's a specific executor like `PromptExecutor` — reconsider the abstraction level. A gateway that wraps `subprocess.run` generically skips the meaningful abstraction and is no better than mocking `subprocess.run` directly.

## Default Gateway Pattern (3 Files)

The default for new gateways is the **3-file pattern**:

| Implementation | Purpose                                          |
| -------------- | ------------------------------------------------ |
| `abc.py`       | Abstract method definition (contract)            |
| `real.py`      | Production implementation (subprocess/API calls) |
| `fake.py`      | Constructor-injected test data (unit tests)      |

Most gateways use this pattern: Cmux, Codespace, AgentLauncher, Browser, Clipboard, Shell, Console, Time, etc.

## Extended Gateway Pattern (4 Files) — Opt-In

Only add `dry_run.py` when the gateway **participates in a user-facing `--dry-run` feature**. This extra file is not free — it adds maintenance burden and must be kept in sync with every method change.

| Implementation | Purpose                                              |
| -------------- | ---------------------------------------------------- |
| `abc.py`       | Abstract method definition (contract)                |
| `real.py`      | Production implementation (subprocess/API calls)     |
| `fake.py`      | Constructor-injected test data (unit tests)          |
| `dry_run.py`   | Delegates read-only, no-ops mutations (preview mode) |

**Gateways currently opted into 4-file pattern:** Git, LocalGitHub, Graphite, AgentDocs.

These gateways have dry-run because they participate in erk's `--dry-run` CLI mode. **Do not add dry_run.py to a new gateway unless the gateway is wired into the dry-run context factory.**

## Gateway Locations

| Gateway     | Pattern | Location                                                 |
| ----------- | ------- | -------------------------------------------------------- |
| Git         | 4-file  | `packages/erk-shared/src/erk_shared/gateway/git/`        |
| LocalGitHub | 4-file  | `packages/erk-shared/src/erk_shared/gateway/github/`     |
| Graphite    | 4-file  | `packages/erk-shared/src/erk_shared/gateway/graphite/`   |
| AgentDocs   | 4-file  | `packages/erk-shared/src/erk_shared/gateway/agent_docs/` |
| Cmux        | 3-file  | `packages/erk-shared/src/erk_shared/gateway/cmux/`       |
| Codespace   | 3-file  | `packages/erk-shared/src/erk_shared/gateway/codespace/`  |

## New Gateway: ErkContext Wiring

After creating the gateway files, wire the new gateway into ErkContext so it's
available via dependency injection throughout the application.

### 1. Add field to ErkContext

**File**: `packages/erk-shared/src/erk_shared/context/context.py`

Add the gateway field to the `ErkContext` dataclass, grouped with related gateways:

```python
# Shell/CLI integrations
shell: Shell
codespace: Codespace
cmux: Cmux  # <-- new gateway
```

### 2. Add to test factory

**File**: `packages/erk-shared/src/erk_shared/context/context.py` (`ErkContext.for_test`)

Add an optional parameter with a default fake:

```python
@classmethod
def for_test(
    cls,
    *,
    cmux: Cmux | None = None,  # <-- new parameter
    ...
) -> ErkContext:
```

Resolve the default inside the method:

```python
resolved_cmux = cmux if cmux is not None else FakeCmux(workspace_ref="fake-ws")
```

### 3. Wire production implementation

**File**: `src/erk/core/context.py` (production context factory)

Import and instantiate the real implementation near other Real\* gateways:

```python
from erk_shared.gateway.cmux.real import RealCmux
...
ErkContext(
    ...
    cmux=RealCmux(),  # next to codespace=RealCodespace()
    ...
)
```

### Reference

See Codespace gateway for a minimal example:

- Field: `codespace: Codespace` in ErkContext
- Production: `codespace=RealCodespace()` in `src/erk/core/context.py`
- Test: `FakeCodespace(...)` default in `for_test()`

## Checklist for New Gateway Methods

When adding a new method to any gateway ABC:

1. [ ] Add abstract method to `abc.py` with docstring and type hints
2. [ ] Implement in `real.py` (subprocess for Git, `gh` CLI for LocalGitHub/Graphite)
3. [ ] Implement in `fake.py` with:
   - Constructor parameter for test data (if read method)
   - Mutation tracking list/set (if write method)
   - Read-only property for test assertions (if write method)
4. [ ] **Only for 4-file gateways:** Implement in `dry_run.py`:
   - Read-only methods: delegate to wrapped
   - Mutation methods: no-op, return success value
5. [ ] Add unit tests for Fake behavior
6. [ ] Add integration tests for Real (if feasible)

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
- [ ] All implementations updated (abc, real, fake, and dry_run for 4-file gateways)

### Checklist: Use Exceptions When

- [ ] All callers terminate on failure (extract message and stop)
- [ ] No caller inspects error type or branches on error content
- [ ] Use `UserFacingCliError` at CLI boundary

### NonIdealState Protocol

<!-- Source: packages/erk-shared/src/erk_shared/non_ideal_state.py, NonIdealState -->

All discriminated union error types must implement the `NonIdealState` protocol from `packages/erk-shared/src/erk_shared/non_ideal_state.py`. The protocol requires two read-only properties: `error_type` (machine-readable classification string) and `message` (human-readable description).

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

| Method           | Return type                               | Gateway        |
| ---------------- | ----------------------------------------- | -------------- |
| `merge_pr`       | `MergeResult \| MergeError`               | GitHub         |
| `push_to_remote` | `PushResult \| PushError`                 | Git remote_ops |
| `pull_rebase`    | `PullRebaseResult \| PullRebaseError`     | Git remote_ops |
| `create_branch`  | `BranchCreated \| BranchAlreadyExists`    | Git branch_ops |
| `submit_branch`  | `SubmitBranchResult \| SubmitBranchError` | BranchManager  |

**Methods using exceptions** (all callers terminate):

| Method              | Exception      | Why                                                         |
| ------------------- | -------------- | ----------------------------------------------------------- |
| Worktree add/remove | `RuntimeError` | No caller inspects error content; all terminate identically |
| HTTP operations     | `HttpError`    | Generic transport failure; callers just surface the message |

## Return Type Changes

When changing an existing gateway method's return type (e.g., converting from exception-based to discriminated union), follow this comprehensive migration pattern:

**Complete Update Checklist**:

1. [ ] Define new types in `gateway/{name}/types.py`
2. [ ] Update ABC signature in `abc.py`
3. [ ] Update all implementations:
   - [ ] `real.py` - Return appropriate error types for failure cases
   - [ ] `fake.py` - Return union types in test implementation
   - [ ] `dry_run.py` - Return appropriate success/error based on mode (4-file gateways only)
4. [ ] Update all call sites to handle new return type
5. [ ] Update tests to check `isinstance(result, ErrorType)`
6. [ ] Verify all imports include new types

**Canonical Example**:

**PR #6294** (`merge_pr: bool | str` → `MergeResult | MergeError`):

- Changed 4 files in gateway implementations
- Updated 3 call sites in land workflow
- Updated tests to use `isinstance(result, MergeError)`

**Critical**: Incomplete migrations break type safety. Use grep to find all call sites before starting.

## Read-Only vs Mutation Methods

### Read-Only Methods

**Examples**: `get_current_branch`, `get_pr`, `list_workflow_runs`

```python
# dry_run.py - Delegate to wrapped
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
```

## FakeGateway Pattern for Mutations

When adding a mutation method to a Fake:

```python
class FakeLocalGitHub(LocalGitHub):
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
# real.py - LBYL check existence, then delete
def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
    # Check if branch exists (show-ref), return early if missing
    # Then delete with -D (force) or -d flag
    ...
```

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/branch_ops/real.py -->

**Key principle**: Use LBYL _to implement_ idempotency for operations that would otherwise fail on missing resources. This is different from operations that are _already_ idempotent (like `git fetch`), which don't need LBYL checks.

See the canonical implementation in `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/real.py`.

**Verification checklist** for idempotent behavioral changes:

1. **ABC** (`abc.py`) - Update docstring to document idempotent behavior
2. **Real** (`real.py`) - Add LBYL check and early return
3. **Fake** (`fake.py`) - Verify fake already handles idempotency (usually does)
4. **DryRun** (`dry_run.py`) - Update if gateway uses 4-file pattern
5. **Integration test** (`tests/integration/test_real_*.py`) - Add test for missing resource case
6. **Unit tests** (`tests/unit/`) - Update any tests that assumed failure on missing resource

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

When one gateway composes another (e.g., LocalGitHub composes GitHubIssues), follow these patterns:

### ABC: Abstract Property

```python
class LocalGitHub(ABC):
    @property
    @abstractmethod
    def issues(self) -> GitHubIssues:
        """Return the composed GitHubIssues gateway."""
        ...
```

### Real: Compose Real + Factory Method

```python
class RealLocalGitHub(LocalGitHub):
    def __init__(self, time: Time, repo_info: RepoInfo | None, *, issues: GitHubIssues) -> None:
        self._issues = issues
        # ...

    @property
    def issues(self) -> GitHubIssues:
        return self._issues

    # Note: RealLocalGitHub does not have a for_test() factory method.
    # Tests should use FakeLocalGitHub from tests.fakes.gateway.github instead.
```

### Fake: Separate Data vs Gateway Parameters

**Critical**: Use distinct parameter names to avoid collision:

- `foo_data` for test data (e.g., `issues_data: list[IssueInfo]`)
- `foo_gateway` for composed gateway (e.g., `issues_gateway: GitHubIssues`)

```python
class FakeLocalGitHub(LocalGitHub):
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
class DryRunLocalGitHub(LocalGitHub):
    def __init__(self, wrapped: LocalGitHub) -> None:
        self._wrapped = wrapped
        self._issues = DryRunGitHubIssues(wrapped.issues)

    @property
    def issues(self) -> GitHubIssues:
        return self._issues
```

## Dependency Injection for Testability

When adding methods that benefit from testability (lock waiting, retry logic, timeouts), consider injecting dependencies via constructor rather than adding parameters to each method.

**Example Pattern** (from `RealGitBranchOps`):

```python
class RealGitBranchOps(GitBranchOps):
    def __init__(self, *, time: Time) -> None:
        self._time = time

    def checkout_branch(self, cwd: Path, branch: str) -> None:
        # Use injected dependency before operation
        wait_for_index_lock(cwd, self._time)
        # ... actual git operation
```

The parent `RealGit` creates subgateways with the shared Time dependency:

```python
class RealGit(Git):
    def __init__(self, time: Time | None = None) -> None:
        self._time = time if time is not None else RealTime()
        self._branch = RealGitBranchOps(time=self._time)
        self._remote = RealGitRemoteOps(time=self._time)
        # ... other subgateways
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

All methods (both queries and mutations) now live on subgateways. The main Git ABC is a pure facade with only property accessors.

### Sub-Gateway Structure

```
packages/erk-shared/src/erk_shared/gateway/git/
├── abc.py             # Main Git ABC (pure facade with property accessors)
├── branch_ops/        # Sub-gateway for branch operations
│   ├── __init__.py
│   ├── abc.py         # GitBranchOps ABC
│   ├── real.py
│   ├── fake.py
│   └── dry_run.py
```

### ABC Composition

The main gateway ABC exposes the sub-gateway via a property:

```python
class Git(ABC):
    @property
    @abstractmethod
    def branch(self) -> GitBranchOps:
        """Access branch operations subgateway."""
        ...

    # Git ABC is now a pure facade - all methods live on subgateways
    # Other property accessors: worktree, remote, commit, status, rebase, tag, repo, analysis, config
```

### Query vs Mutation Split

The Git ABC is now a **pure facade** -- it contains ONLY property accessors to subgateways. Both query and mutation methods live on subgateways:

| Subgateway    | Property accessor | Examples                                                     |
| ------------- | ----------------- | ------------------------------------------------------------ |
| `branch_ops/` | `git.branch`      | `get_current_branch()`, `create_branch()`, `delete_branch()` |
| `repo_ops/`   | `git.repo`        | `get_repository_root()`                                      |
| `remote_ops/` | `git.remote`      | `push_to_remote()`, `fetch()`                                |
| `worktree/`   | `git.worktree`    | `list_worktrees()`, `add_worktree()`                         |
| `rebase_ops/` | `git.rebase`      | `rebase_onto()`, `rebase_abort()`                            |

### Why Pure Facade?

1. **Enforcement**: Callers can't bypass BranchManager to mutate branches directly
2. **Clear ownership**: Each operation belongs to exactly one subgateway
3. **Discoverability**: Callers navigate through properties (IDE autocomplete)
4. **Testing**: FakeBranchManager can track mutations without full gateway wiring

### Implementation Checklist

When extracting methods to a sub-gateway:

1. [ ] Create sub-gateway directory (`branch_ops/`)
2. [ ] Implement files: abc.py, real.py, fake.py (and dry_run.py for 4-file gateways)
3. [ ] Add `@property` to main ABC returning sub-gateway
4. [ ] Update all main gateway implementations to compose sub-gateway
5. [ ] Create factory method in Fake to link sub-gateway state

### FakeGit/FakeGraphite Sub-Gateway Linking

Fakes need special handling to share state between main gateway and sub-gateway:

```python
class FakeGit(Git):
    @property
    def branch(self) -> GitBranchOps:
        return self._branch_gateway

    def create_linked_branch_ops(self) -> FakeGitBranchOps:
        """Return the FakeGitBranchOps linked to this FakeGit's state.

        The returned FakeGitBranchOps shares mutable state and mutation tracking
        with this FakeGit instance. This allows tests to check FakeGit properties
        like deleted_branches while mutations happen through BranchManager.
        """
        ...
```

### Reference Implementations

Sub-gateways for branch mutations:

- Git branch_ops: `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/`
- Graphite branch_ops: `packages/erk-shared/src/erk_shared/gateway/graphite/branch_ops/`

Sub-gateway for worktree operations:

- Git worktree: `packages/erk-shared/src/erk_shared/gateway/git/worktree/`

The worktree sub-gateway follows the same 4-file pattern with methods: `list_worktrees()`, `add_worktree()`, `move_worktree()`, `remove_worktree()`, `prune_worktrees()`, `find_worktree_for_branch()`. Note: Worktree operations use exceptions (RuntimeError), not discriminated unions.

## Time Injection for Retry-Enabled Gateways

Gateways that implement retry logic need Time dependency injection for testability.

### Pattern

Accept optional `Time` in `__init__` with default to `RealTime()`:

```python
class RealLocalGitHub(LocalGitHub):
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
    def __init__(self, get_git_common_dir: Callable, get_conflicted_files: Callable) -> None:
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

## ABC Method Removal Pattern

When removing dead convenience methods from gateway ABCs (methods with zero production callers), follow this synchronization pattern.

### When to Remove Methods

Remove methods that meet ALL these criteria:

1. **Zero production callers** - No code in `src/erk/` or `packages/erk-shared/` uses the method
2. **Convenience wrapper** - Method just forwards to a subgateway property (e.g., `git.method()` → `git.subgateway.method()`)
3. **Dead code** - Not part of the core gateway contract

### Synchronization Requirement

When removing a method from an ABC, you MUST remove it from all implementations simultaneously:

- `abc.py` - Remove abstract method definition
- `real.py` - Remove production implementation
- `fake.py` - Remove fake implementation
- `dry_run.py` - Remove dry-run implementation (4-file gateways only)

**Partial removal causes type checker errors** - if you remove from abc.py but forget another implementation, the type checker will complain about missing abstract method implementations.

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
3. Batch removal in a single PR (maintain synchronization across all implementation files)

### Reference Implementation

PR #6285: [Remove rebase_onto/rebase_abort from Git ABC and dead convenience methods](https://github.com/owner/repo/pull/6285)

This PR demonstrates:

- Synchronization across all implementation files
- Caller migration to subgateway properties
- Verification via grep across packages

## Reference Implementation: Git Remote Ops (4-File Pattern)

The `remote_ops/` sub-gateway provides a clean example of the 4-file pattern with discriminated union return types:

```
packages/erk-shared/src/erk_shared/gateway/git/remote_ops/
├── abc.py        # push_to_remote() -> PushResult | PushError
├── real.py       # try/except boundary, subprocess calls
├── fake.py       # Constructor-injected errors, mutation tracking
└── dry_run.py    # Returns PushResult() without executing
```

Key patterns demonstrated:

- **Discriminated union returns**: Methods return `Success | Error` instead of raising
- **Error boundary in real.py**: `try/except RuntimeError` converts to `PushError`
- **Fake configuration**: `FakeGitRemoteOps(push_to_remote_error=PushError(...))` injects failures
- **Mutation tracking**: `fake.pushed_branches` records successful pushes for test assertions

See PR #6329 for the migration that introduced this pattern.

## Completed Migrations to Gateway Pattern

Notable examples of migrating raw subprocess calls to gateway methods:

| Script                       | Old Pattern                            | New Pattern                                | PR    |
| ---------------------------- | -------------------------------------- | ------------------------------------------ | ----- |
| `download_remote_session.py` | `subprocess.run(["git", "show", ...])` | `git.commit.read_file_from_ref(ref, path)` | #8584 |

After PR #8584, all callers of `read_file_from_ref` are gateway-based: fetch_sessions, push_session, get_learn_sessions, and download_remote_session.

<!-- Source: src/erk/cli/commands/exec/scripts/download_remote_session.py:77-81 -->

## Related Documentation

- [Erk Architecture Patterns](erk-architecture.md) - Dependency injection, dry-run patterns
- [Protocol vs ABC](protocol-vs-abc.md) - Why gateways use ABC instead of Protocol
- [Subprocess Wrappers](subprocess-wrappers.md) - How Real implementations wrap subprocess calls
- [GitHub GraphQL Patterns](github-graphql.md) - GraphQL mutation patterns for GitHub
- [Gateway Error Boundaries](gateway-error-boundaries.md) - Where exceptions become discriminated unions
- [Gateway Signature Migration](gateway-signature-migration.md) - How to update all call sites when signatures change
