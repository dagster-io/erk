# Plan: No-Repo Infrastructure (Objective #8832, Node 1.4)

## Context

Objective #8832 decouples CLI commands from the git repo requirement. Nodes 1.1–1.3 (PR #8835) created `HttpClient`, `RemoteGitHub` gateway, and the `--repo` flag on `one-shot`. Node 1.4 creates the foundational infrastructure that all subsequent nodes depend on: a `@no_repo_required` decorator for Click commands and sentinel gateway implementations (`NoRepoGit`, `NoRepoGitHub`) that raise descriptive errors when repo-dependent operations are accidentally called outside a repo context.

Currently, `create_context()` constructs `RealGit` and `RealGitHub` even when `repo` is `NoRepoSentinel`. This means commands running outside a repo get cryptic subprocess failures instead of clear error messages. The sentinels fix this.

## Design Decisions

1. **Follow GraphiteDisabled pattern** — Sentinels are `@dataclass(frozen=True)` classes implementing the gateway ABCs. All methods raise `NoRepoError`.
2. **Git subgateway properties raise immediately** — Since Git is a pure facade with 10 property accessors, NoRepoGit raises `NoRepoError` on property access. No need to create 10 separate NoRepo subgateway classes.
3. **NoRepoGitHub returns NoRepoGitHubIssues for `.issues`** — The `issues` property returns a sentinel (not raises) because `PlannedPRBackend` and other services are constructed with `issues` as a separate parameter during context creation. The sentinel raises on actual method calls.
4. **Shared `NoRepoError` exception** — Single exception class used by all sentinels, with descriptive messages explaining what happened and how to fix it.
5. **`@no_repo_required` is a simple Click decorator** — Sets `command.no_repo_required = True`, inspectable by CLI infrastructure. No commands are converted in this PR — that's phases 2/3.

## Implementation

### Phase 1: Sentinel Infrastructure (erk-shared)

#### 1A. Create `NoRepoError` exception
**File:** `packages/erk-shared/src/erk_shared/gateway/no_repo.py` (new)

```python
class NoRepoError(Exception):
    """Raised when a repo-dependent gateway operation is called outside a git repository."""
    def __init__(self, operation: str) -> None:
        super().__init__(
            f"{operation} requires a local git repository.\n\n"
            "You are running outside a git repository. Either:\n"
            "  1. cd into a git repository\n"
            "  2. Use --repo owner/repo for remote operations"
        )
```

#### 1B. Create `NoRepoGit` sentinel
**File:** `packages/erk-shared/src/erk_shared/gateway/git/no_repo.py` (new)

- `@dataclass(frozen=True)` implementing `Git` ABC
- All 10 subgateway properties (`worktree`, `branch`, `remote`, `commit`, `status`, `rebase`, `tag`, `repo`, `analysis`, `config`) raise `NoRepoError` on access
- Pattern: `raise NoRepoError("Git worktree operations")`

#### 1C. Create `NoRepoGitHubIssues` sentinel
**File:** `packages/erk-shared/src/erk_shared/gateway/github/issues/no_repo.py` (new)

- `@dataclass(frozen=True)` implementing `GitHubIssues` ABC
- All ~17 methods raise `NoRepoError`
- Needed because `PlannedPRBackend(github, issues, ...)` takes issues as a separate param

#### 1D. Create `NoRepoGitHub` sentinel
**File:** `packages/erk-shared/src/erk_shared/gateway/github/no_repo.py` (new)

- `@dataclass(frozen=True)` implementing `GitHub` ABC
- `issues` property returns `NoRepoGitHubIssues()` (doesn't raise — needed for composition)
- All ~30 other methods raise `NoRepoError`

### Phase 2: Context Wiring

#### 2A. Wire sentinels into `create_context()`
**File:** `src/erk/core/context.py` — modify `create_context()`

In the no-repo branch (after `repo = discover_repo_or_sentinel(...)`):

```python
if isinstance(repo, NoRepoSentinel):
    git = NoRepoGit()  # Replace RealGit with sentinel
    # github/issues use sentinels too
    issues = NoRepoGitHubIssues()
    github = NoRepoGitHub()
    # ... rest of no-repo construction
else:
    # existing code path unchanged
```

Key changes:
- `git` is swapped from `RealGit` to `NoRepoGit` after repo discovery (RealGit is still used for `discover_repo_or_sentinel` call)
- `github` uses `NoRepoGitHub` instead of `RealGitHub`
- `issues` uses `NoRepoGitHubIssues` instead of `RealGitHubIssues`
- `graphite` already handled (uses `GraphiteDisabled`)
- Services like `plan_store`, `plan_list_service`, `objective_list_service` get the sentinels — they'll raise clear errors if used

### Phase 3: Decorator

#### 3A. Create `@no_repo_required` decorator
**File:** `src/erk/cli/no_repo.py` (new)

```python
import functools
import click

def no_repo_required(fn):
    """Mark a Click command as not requiring a git repository.

    Inspectable via command.no_repo_required attribute.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    wrapper.no_repo_required = True
    return wrapper
```

No commands are converted in this PR. The decorator is infrastructure for phases 2/3.

### Phase 4: Tests

#### 4A. Test NoRepoGit
**File:** `tests/unit/gateway/git/test_no_repo.py` (new)

- Test each subgateway property access raises `NoRepoError`
- Test error message includes operation name and remediation steps

#### 4B. Test NoRepoGitHub
**File:** `tests/unit/gateway/github/test_no_repo.py` (new)

- Test `issues` property returns `NoRepoGitHubIssues` (doesn't raise)
- Test representative methods raise `NoRepoError`
- Test `NoRepoGitHubIssues` methods raise `NoRepoError`

#### 4C. Test `@no_repo_required` decorator
**File:** `tests/unit/cli/test_no_repo.py` (new)

- Test decorator sets `no_repo_required = True` on wrapper
- Test undecorated commands don't have the attribute

#### 4D. Test context wiring
**File:** `tests/unit/core/test_context_no_repo.py` (new)

- Test `create_context()` when outside a git repo produces sentinels
- Test `ctx.git` is `NoRepoGit`
- Test `ctx.github` is `NoRepoGitHub`
- Test accessing `ctx.git.branch` raises `NoRepoError`

## Files Modified

| File | Action |
|------|--------|
| `packages/erk-shared/src/erk_shared/gateway/no_repo.py` | Create (NoRepoError) |
| `packages/erk-shared/src/erk_shared/gateway/git/no_repo.py` | Create (NoRepoGit) |
| `packages/erk-shared/src/erk_shared/gateway/github/no_repo.py` | Create (NoRepoGitHub) |
| `packages/erk-shared/src/erk_shared/gateway/github/issues/no_repo.py` | Create (NoRepoGitHubIssues) |
| `src/erk/cli/no_repo.py` | Create (@no_repo_required) |
| `src/erk/core/context.py` | Modify (wire sentinels in create_context) |
| `tests/unit/gateway/git/test_no_repo.py` | Create |
| `tests/unit/gateway/github/test_no_repo.py` | Create |
| `tests/unit/cli/test_no_repo.py` | Create |
| `tests/unit/core/test_context_no_repo.py` | Create |

## Key Patterns to Reuse

- **GraphiteDisabled** (`packages/erk-shared/src/erk_shared/gateway/graphite/disabled.py`): Sentinel pattern with `@dataclass(frozen=True)`, reason enum, descriptive errors
- **NoRepoSentinel** (`packages/erk-shared/src/erk_shared/context/types.py`): Existing sentinel for repo absence
- **GitHub ABC** (`packages/erk-shared/src/erk_shared/gateway/github/abc.py`): 30+ methods to implement
- **GitHubIssues ABC** (`packages/erk-shared/src/erk_shared/gateway/github/issues/abc.py`): 17 methods to implement
- **Git ABC** (`packages/erk-shared/src/erk_shared/gateway/git/abc.py`): 10 subgateway properties

## Verification

1. Run `make fast-ci` — all unit tests pass
2. Run `ty` — no type errors from sentinel implementations
3. Manual: Run `erk` from a non-git directory → should get clear `NoRepoError` messages instead of subprocess failures when commands try to use git/github
4. Existing tests: No regressions — `context_for_test()` and `minimal_context()` are unchanged
