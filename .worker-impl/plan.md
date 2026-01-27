# Plan: Phase 3 - Remote Subgateway Extraction

**Part of Objective #6169, Phase 3**

## Goal

Extract 6 remote tracking operations from Git ABC into a new `git/remote_ops/` subgateway, following the established 5-layer pattern from `branch_ops/`.

## Methods to Extract

| Method | Type | Signature |
|--------|------|-----------|
| `fetch_branch` | mutation | `(repo_root: Path, remote: str, branch: str) -> None` |
| `pull_branch` | mutation | `(repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None` |
| `fetch_pr_ref` | mutation | `(*, repo_root: Path, remote: str, pr_number: int, local_branch: str) -> None` |
| `push_to_remote` | mutation | `(cwd: Path, remote: str, branch: str, *, set_upstream: bool, force: bool) -> None` |
| `pull_rebase` | mutation | `(cwd: Path, remote: str, branch: str) -> None` |
| `get_remote_url` | query | `(repo_root: Path, remote: str) -> str` |

## Migration Scope

- **51 callsites** across **27 files** to migrate
- Pattern: `git.fetch_branch(...)` → `git.remote.fetch_branch(...)`

## Implementation Steps

### Step 1: Create `git/remote_ops/abc.py`

Create the abstract interface with 6 methods.

```python
class GitRemoteOps(ABC):
    """Abstract interface for Git remote operations."""

    @abstractmethod
    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None: ...

    @abstractmethod
    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None: ...

    @abstractmethod
    def fetch_pr_ref(self, *, repo_root: Path, remote: str, pr_number: int, local_branch: str) -> None: ...

    @abstractmethod
    def push_to_remote(self, cwd: Path, remote: str, branch: str, *, set_upstream: bool, force: bool) -> None: ...

    @abstractmethod
    def pull_rebase(self, cwd: Path, remote: str, branch: str) -> None: ...

    @abstractmethod
    def get_remote_url(self, repo_root: Path, remote: str) -> str: ...
```

### Step 2: Create `git/remote_ops/real.py`

Move implementation from `git/real.py` to `RealGitRemoteOps`.

### Step 3: Create `git/remote_ops/fake.py`

Create `FakeGitRemoteOps` with:
- Constructor accepting pre-configured state (remote URLs, etc.)
- Mutation tracking lists for test assertions
- `link_mutation_tracking()` method for FakeGit integration

### Step 4: Create `git/remote_ops/dry_run.py`

Create `DryRunGitRemoteOps`:
- Mutations print `[DRY RUN] Would run: git push ...` messages
- Query (`get_remote_url`) delegates to wrapped implementation

### Step 5: Create `git/remote_ops/printing.py`

Create `PrintingGitRemoteOps`:
- Inherits from `PrintingBase`
- Prints styled output before delegating mutations
- Queries pass through without printing

### Step 6: Create `git/remote_ops/__init__.py`

Export `GitRemoteOps` for external imports.

### Step 7: Add `remote` property to Git ABC

```python
# In git/abc.py
if TYPE_CHECKING:
    from erk_shared.gateway.git.remote_ops.abc import GitRemoteOps

class Git(ABC):
    @property
    @abstractmethod
    def remote(self) -> GitRemoteOps:
        """Access remote operations subgateway."""
        ...
```

### Step 8: Wire into Git implementations

- **RealGit**: Create `RealGitRemoteOps` in `__init__`, return via property
- **FakeGit**: Create `FakeGitRemoteOps` in `__init__`, link mutation tracking
- **DryRunGit**: Lazy-wrap with `DryRunGitRemoteOps`
- **PrintingGit**: Lazy-wrap with `PrintingGitRemoteOps`

### Step 9: Migrate callsites

Update 51 callsites across 27 files:
- `git.fetch_branch(...)` → `git.remote.fetch_branch(...)`
- `git.push_to_remote(...)` → `git.remote.push_to_remote(...)`
- etc.

Key files:
- `src/erk/cli/commands/submit.py` (4 calls)
- `src/erk/cli/commands/admin.py` (4 calls)
- `src/erk/cli/commands/pr/checkout_cmd.py` (4 calls)
- `packages/erk-shared/src/erk_shared/gateway/pr/submit.py` (3 calls)
- `src/erk/core/health_checks.py` (3 calls)

### Step 10: Remove remote methods from Git ABC

Delete the 6 remote method signatures from `git/abc.py` and implementations from `git/real.py`, `git/fake.py`, `git/dry_run.py`, `git/printing.py`.

## Files to Create

```
packages/erk-shared/src/erk_shared/gateway/git/remote_ops/
├── __init__.py
├── abc.py
├── real.py
├── fake.py
├── dry_run.py
└── printing.py
```

## Files to Modify

- `packages/erk-shared/src/erk_shared/gateway/git/abc.py` - Add property, remove methods
- `packages/erk-shared/src/erk_shared/gateway/git/real.py` - Add property, remove methods
- `packages/erk-shared/src/erk_shared/gateway/git/fake.py` - Add property, remove methods
- `packages/erk-shared/src/erk_shared/gateway/git/dry_run.py` - Add property, remove methods
- `packages/erk-shared/src/erk_shared/gateway/git/printing.py` - Add property, remove methods
- 27 files with callsite migrations

## Verification

1. **Type check**: Run `ty` to verify all callsites updated correctly
2. **Unit tests**: Run `pytest packages/erk-shared/tests/unit/gateway/git/`
3. **Integration tests**: Run `pytest tests/integration/test_real_git.py`
4. **Full test suite**: Run `make fast-ci` to verify no regressions

## Related Documentation

- **Skills**: `dignified-python`, `fake-driven-testing`
- **Prior art**: `branch_ops/` subgateway (same pattern)
- **Objective**: #6169, Phase 3