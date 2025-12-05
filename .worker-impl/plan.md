# Phase 4: GitRemotes Implementation Plan

## Goal

Extract remote operations from the monolithic `Git` class into a new parallel integration `GitRemotes`, following the pattern established by `GitWorktrees` (Phase 2) and `GitBranches` (Phase 3).

## Prerequisites

- Phase 2 complete: `GitWorktrees` exists
- Phase 3 complete: `GitBranches` exists
- `ErkContext` has `git_worktrees` and `git_branches` fields

## Pattern Reference

From previous phases, integrations are **parallel at ErkContext level**:
```python
@dataclass(frozen=True)
class ErkContext:
    git: Git
    git_worktrees: GitWorktrees   # Phase 2
    git_branches: GitBranches     # Phase 3
    git_remotes: GitRemotes       # Phase 4 (NEW)
    github: GitHub
    # ...
```

New access pattern after refactoring:
```python
ctx.git.commit(...)                    # Core Git operations
ctx.git_worktrees.add_worktree()       # Worktree operations
ctx.git_branches.checkout_branch()     # Branch operations
ctx.git_remotes.push_to_remote()       # Remote operations (NEW)
```

---

## Methods to Extract (6 methods)

| Method | Current Line | Read/Write | Description |
|--------|--------------|------------|-------------|
| `fetch_branch` | 419 | Write | Fetch branch from remote |
| `pull_branch` | 430 | Write | Pull branch from remote |
| `push_to_remote` | 533 | Write | Push branch to remote |
| `branch_exists_on_remote` | 442 | Read | Check if branch exists on remote |
| `get_remote_url` | 597 | Read | Get URL for remote |
| `fetch_pr_ref` | 485 | Write | Fetch PR ref into local branch |

---

## Files to Create

### 1. `packages/erk-shared/src/erk_shared/git/remotes/__init__.py`

```python
"""Git remote operations integration."""

from erk_shared.git.remotes.abc import GitRemotes
from erk_shared.git.remotes.dry_run import DryRunGitRemotes
from erk_shared.git.remotes.fake import FakeGitRemotes
from erk_shared.git.remotes.printing import PrintingGitRemotes
from erk_shared.git.remotes.real import RealGitRemotes

__all__ = [
    "GitRemotes",
    "DryRunGitRemotes",
    "FakeGitRemotes",
    "PrintingGitRemotes",
    "RealGitRemotes",
]
```

### 2. `packages/erk-shared/src/erk_shared/git/remotes/abc.py`

```python
"""Abstract interface for git remote operations."""

from abc import ABC, abstractmethod
from pathlib import Path


class GitRemotes(ABC):
    """Abstract interface for git remote operations.

    All implementations (real, fake, dry-run) must implement this interface.
    """

    @abstractmethod
    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        """Fetch a specific branch from a remote."""
        ...

    @abstractmethod
    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        """Pull a specific branch from a remote."""
        ...

    @abstractmethod
    def push_to_remote(
        self, cwd: Path, remote: str, branch: str, *, set_upstream: bool = False
    ) -> None:
        """Push a branch to a remote."""
        ...

    @abstractmethod
    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        """Check if a branch exists on a remote."""
        ...

    @abstractmethod
    def get_remote_url(self, repo_root: Path, remote: str = "origin") -> str:
        """Get the URL for a git remote."""
        ...

    @abstractmethod
    def fetch_pr_ref(self, repo_root: Path, remote: str, pr_number: int, local_branch: str) -> None:
        """Fetch a PR ref into a local branch."""
        ...
```

### 3. `packages/erk-shared/src/erk_shared/git/remotes/real.py`

Extract from `packages/erk-shared/src/erk_shared/git/real.py`:

| Method | Source Lines |
|--------|--------------|
| `fetch_branch` | ~500-510 |
| `pull_branch` | ~512-525 |
| `push_to_remote` | ~645-660 |
| `branch_exists_on_remote` | ~527-545 |
| `get_remote_url` | ~745-760 |
| `fetch_pr_ref` | ~560-580 |

```python
"""Production GitRemotes implementation using subprocess."""

from pathlib import Path

from erk_shared.git.remotes.abc import GitRemotes
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitRemotes(GitRemotes):
    """Production implementation using subprocess."""

    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        # Copy from RealGit.fetch_branch
        ...

    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        # Copy from RealGit.pull_branch
        ...

    def push_to_remote(
        self, cwd: Path, remote: str, branch: str, *, set_upstream: bool = False
    ) -> None:
        # Copy from RealGit.push_to_remote
        ...

    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        # Copy from RealGit.branch_exists_on_remote
        ...

    def get_remote_url(self, repo_root: Path, remote: str = "origin") -> str:
        # Copy from RealGit.get_remote_url
        ...

    def fetch_pr_ref(self, repo_root: Path, remote: str, pr_number: int, local_branch: str) -> None:
        # Copy from RealGit.fetch_pr_ref
        ...
```

### 4. `packages/erk-shared/src/erk_shared/git/remotes/fake.py`

```python
"""Fake git remote operations for testing."""

from pathlib import Path

from erk_shared.git.remotes.abc import GitRemotes


class FakeGitRemotes(GitRemotes):
    """In-memory fake implementation of git remote operations.

    State Management:
    - remote_branches: dict[Path, dict[str, list[str]]] - repo_root -> remote -> branches
    - remote_urls: dict[Path, dict[str, str]] - repo_root -> remote -> URL

    Mutation Tracking:
    - fetched_branches: list[tuple[str, str]] - (remote, branch) pairs
    - pulled_branches: list[tuple[str, str, bool]] - (remote, branch, ff_only) tuples
    - pushed_branches: list[tuple[str, str, bool]] - (remote, branch, set_upstream) tuples
    - fetched_pr_refs: list[tuple[str, int, str]] - (remote, pr_number, local_branch) tuples
    """

    def __init__(
        self,
        *,
        remote_branches: dict[Path, dict[str, list[str]]] | None = None,
        remote_urls: dict[Path, dict[str, str]] | None = None,
    ) -> None:
        self._remote_branches = remote_branches or {}
        self._remote_urls = remote_urls or {}

        # Mutation tracking
        self._fetched_branches: list[tuple[str, str]] = []
        self._pulled_branches: list[tuple[str, str, bool]] = []
        self._pushed_branches: list[tuple[str, str, bool]] = []
        self._fetched_pr_refs: list[tuple[str, int, str]] = []

    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        self._fetched_branches.append((remote, branch))

    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        self._pulled_branches.append((remote, branch, ff_only))

    def push_to_remote(
        self, cwd: Path, remote: str, branch: str, *, set_upstream: bool = False
    ) -> None:
        self._pushed_branches.append((remote, branch, set_upstream))

    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        repo_remotes = self._remote_branches.get(repo_root, {})
        branches = repo_remotes.get(remote, [])
        return branch in branches

    def get_remote_url(self, repo_root: Path, remote: str = "origin") -> str:
        repo_urls = self._remote_urls.get(repo_root, {})
        if remote not in repo_urls:
            msg = f"Remote '{remote}' not found"
            raise ValueError(msg)
        return repo_urls[remote]

    def fetch_pr_ref(self, repo_root: Path, remote: str, pr_number: int, local_branch: str) -> None:
        self._fetched_pr_refs.append((remote, pr_number, local_branch))

    # Read-only properties for test assertions
    @property
    def fetched_branches(self) -> list[tuple[str, str]]:
        return self._fetched_branches.copy()

    @property
    def pulled_branches(self) -> list[tuple[str, str, bool]]:
        return self._pulled_branches.copy()

    @property
    def pushed_branches(self) -> list[tuple[str, str, bool]]:
        return self._pushed_branches.copy()

    @property
    def fetched_pr_refs(self) -> list[tuple[str, int, str]]:
        return self._fetched_pr_refs.copy()
```

### 5. `packages/erk-shared/src/erk_shared/git/remotes/dry_run.py`

```python
"""No-op GitRemotes wrapper for dry-run mode."""

from pathlib import Path

from erk_shared.git.remotes.abc import GitRemotes


class DryRunGitRemotes(GitRemotes):
    """No-op wrapper that prevents execution of remote operations."""

    def __init__(self, wrapped: GitRemotes) -> None:
        self._wrapped = wrapped

    # Read-only: delegate
    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        # Return True to allow dry-run to continue
        return True

    def get_remote_url(self, repo_root: Path, remote: str = "origin") -> str:
        return self._wrapped.get_remote_url(repo_root, remote)

    # Write operations: no-op
    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        pass  # No-op

    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        pass  # No-op

    def push_to_remote(
        self, cwd: Path, remote: str, branch: str, *, set_upstream: bool = False
    ) -> None:
        pass  # No-op

    def fetch_pr_ref(self, repo_root: Path, remote: str, pr_number: int, local_branch: str) -> None:
        pass  # No-op
```

### 6. `packages/erk-shared/src/erk_shared/git/remotes/printing.py`

```python
"""Printing GitRemotes wrapper for verbose output."""

from pathlib import Path

from erk_shared.git.remotes.abc import GitRemotes
from erk_shared.printing.base import PrintingBase


class PrintingGitRemotes(PrintingBase, GitRemotes):
    """Wrapper that prints operations before delegating."""

    # Read-only: delegate without printing
    def branch_exists_on_remote(self, repo_root: Path, remote: str, branch: str) -> bool:
        return self._wrapped.branch_exists_on_remote(repo_root, remote, branch)

    def get_remote_url(self, repo_root: Path, remote: str = "origin") -> str:
        return self._wrapped.get_remote_url(repo_root, remote)

    # Write operations: print then delegate
    def fetch_branch(self, repo_root: Path, remote: str, branch: str) -> None:
        self._emit(self._format_command(f"git fetch {remote} {branch}"))
        self._wrapped.fetch_branch(repo_root, remote, branch)

    def pull_branch(self, repo_root: Path, remote: str, branch: str, *, ff_only: bool) -> None:
        ff_flag = " --ff-only" if ff_only else ""
        self._emit(self._format_command(f"git pull{ff_flag} {remote} {branch}"))
        self._wrapped.pull_branch(repo_root, remote, branch, ff_only=ff_only)

    def push_to_remote(
        self, cwd: Path, remote: str, branch: str, *, set_upstream: bool = False
    ) -> None:
        upstream_flag = "-u " if set_upstream else ""
        self._emit(self._format_command(f"git push {upstream_flag}{remote} {branch}"))
        self._wrapped.push_to_remote(cwd, remote, branch, set_upstream=set_upstream)

    def fetch_pr_ref(self, repo_root: Path, remote: str, pr_number: int, local_branch: str) -> None:
        self._emit(self._format_command(f"git fetch {remote} pull/{pr_number}/head:{local_branch}"))
        self._wrapped.fetch_pr_ref(repo_root, remote, pr_number, local_branch)
```

---

## Files to Modify

### 1. `src/erk/core/context.py`

Add `git_remotes` field to `ErkContext`:

```python
@dataclass(frozen=True)
class ErkContext:
    git: Git
    git_worktrees: GitWorktrees
    git_branches: GitBranches
    git_remotes: GitRemotes  # NEW
    github: GitHub
    # ...
```

Update `create_context()`:
```python
from erk_shared.git.remotes import RealGitRemotes, DryRunGitRemotes

def create_context(*, dry_run: bool, script: bool = False) -> ErkContext:
    # ...
    git_remotes: GitRemotes = RealGitRemotes()

    if dry_run:
        git_remotes = DryRunGitRemotes(git_remotes)

    return ErkContext(
        git=git,
        git_worktrees=git_worktrees,
        git_branches=git_branches,
        git_remotes=git_remotes,  # NEW
        # ...
    )
```

Update `ErkContext.minimal()` and `ErkContext.for_test()` factory methods.

### 2. Callsite Migration

Find all usages of the 6 remote methods and migrate:

```bash
# Find callsites
rg "\.fetch_branch\(" --type py
rg "\.pull_branch\(" --type py
rg "\.push_to_remote\(" --type py
rg "\.branch_exists_on_remote\(" --type py
rg "\.get_remote_url\(" --type py
rg "\.fetch_pr_ref\(" --type py
```

Migration pattern:
```python
# Before
ctx.git.push_to_remote(cwd, "origin", branch, set_upstream=True)
ctx.git.fetch_branch(repo_root, "origin", branch)

# After
ctx.git_remotes.push_to_remote(cwd, "origin", branch, set_upstream=True)
ctx.git_remotes.fetch_branch(repo_root, "origin", branch)
```

### 3. Remove Methods from Git ABC

After all callsites are migrated, remove the 6 methods from:
- `packages/erk-shared/src/erk_shared/git/abc.py`
- `packages/erk-shared/src/erk_shared/git/real.py`
- `packages/erk-shared/src/erk_shared/git/fake.py`
- `packages/erk-shared/src/erk_shared/git/dry_run.py`
- `packages/erk-shared/src/erk_shared/git/printing.py`

---

## Implementation Steps

1. **Create directory and files**
   ```bash
   mkdir -p packages/erk-shared/src/erk_shared/git/remotes
   ```

2. **Create ABC** (`abc.py`)
   - Define `GitRemotes` ABC with 6 abstract methods

3. **Create Real implementation** (`real.py`)
   - Copy method implementations from `RealGit`
   - Keep all subprocess patterns identical

4. **Create Fake implementation** (`fake.py`)
   - Simple state management for remote branches/URLs
   - Mutation tracking for test assertions

5. **Create DryRun wrapper** (`dry_run.py`)
   - Delegate reads to wrapped
   - No-op for writes

6. **Create Printing wrapper** (`printing.py`)
   - Print then delegate for write operations

7. **Create `__init__.py`** with exports

8. **Add to ErkContext**
   - Add `git_remotes: GitRemotes` field
   - Update `create_context()`, `minimal()`, `for_test()`

9. **Migrate callsites**
   - Search for all 6 method usages
   - Update each to use `ctx.git_remotes`

10. **Remove from Git**
    - Delete 6 methods from Git ABC and implementations
    - Verify all tests pass

11. **Run CI**
    - `uv run pyright`
    - `uv run pytest`

---

## Exit Criteria

- [ ] `GitRemotes` ABC exists with 6 abstract methods
- [ ] `RealGitRemotes` implements all 6 methods
- [ ] `FakeGitRemotes` implements all 6 methods with mutation tracking
- [ ] `DryRunGitRemotes` wraps real implementation
- [ ] `PrintingGitRemotes` provides logging decorator
- [ ] `ErkContext.git_remotes` field exists
- [ ] All callsites migrated from `ctx.git.X` to `ctx.git_remotes.X`
- [ ] 6 methods removed from `Git` ABC
- [ ] All tests pass
- [ ] pyright passes

---

## Remaining Git Methods After Phase 4

After extracting Worktrees (8), Branches (12), and Remotes (6), the core `Git` ABC will have approximately **25 methods** remaining:

**Status/Inspection (10):**
- `has_staged_changes`
- `has_uncommitted_changes`
- `is_worktree_clean`
- `get_file_status`
- `get_ahead_behind`
- `get_all_branch_sync_info`
- `get_recent_commits`
- `get_commit_message`
- `get_branch_last_commit_time`
- `check_merge_conflicts`

**Commit Operations (5):**
- `stage_files`
- `add_all`
- `commit`
- `amend_commit`
- `count_commits_ahead`

**Config/Metadata (2):**
- `set_branch_issue`
- `get_branch_issue`

**Diff/Repository (2):**
- `get_diff_to_branch`
- `get_repository_root`

**Filesystem (3):**
- `path_exists`
- `is_dir`
- `safe_chdir`

---

## Skills to Load

- `dignified-python-313` - Modern Python type syntax
- `fake-driven-testing` - 5-layer testing architecture

## Critical Files

**Create:**
- `packages/erk-shared/src/erk_shared/git/remotes/__init__.py`
- `packages/erk-shared/src/erk_shared/git/remotes/abc.py`
- `packages/erk-shared/src/erk_shared/git/remotes/real.py`
- `packages/erk-shared/src/erk_shared/git/remotes/fake.py`
- `packages/erk-shared/src/erk_shared/git/remotes/dry_run.py`
- `packages/erk-shared/src/erk_shared/git/remotes/printing.py`

**Modify:**
- `src/erk/core/context.py` - Add `git_remotes` field
- `packages/erk-shared/src/erk_shared/git/abc.py` - Remove 6 methods
- `packages/erk-shared/src/erk_shared/git/real.py` - Remove 6 methods
- `packages/erk-shared/src/erk_shared/git/fake.py` - Remove 6 methods
- `packages/erk-shared/src/erk_shared/git/dry_run.py` - Remove 6 methods
- `packages/erk-shared/src/erk_shared/git/printing.py` - Remove 6 methods
- All files with callsites (find via grep)

**Reference:**
- `packages/erk-shared/src/erk_shared/git/worktrees/` - Phase 2 pattern
- `packages/erk-shared/src/erk_shared/git/branches/` - Phase 3 pattern