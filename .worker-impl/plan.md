# Phase 3: GitBranches Implementation Plan

## Goal

Extract branch operations from the monolithic `Git` class into a new parallel integration `GitBranches`, following the pattern established by `GitWorktrees` in Phase 2.

## Prerequisites

- Phase 2 complete: `GitWorktrees` exists at `packages/erk-shared/src/erk_shared/git/worktrees/`
- `ErkContext` has `git_worktrees` field

## Pattern Reference

From Phase 2, integrations are **parallel at ErkContext level**:
```python
@dataclass(frozen=True)
class ErkContext:
    git: Git
    git_worktrees: GitWorktrees   # Phase 2
    git_branches: GitBranches     # Phase 3 (NEW)
    github: GitHub
    # ...
```

New access pattern after refactoring:
```python
ctx.git.commit(...)                    # Core Git operations
ctx.git_worktrees.add_worktree()       # Worktree operations
ctx.git_branches.checkout_branch()     # Branch operations (NEW)
```

---

## Methods to Extract (12 methods)

| Method | Current Line | Read/Write | Description |
|--------|--------------|------------|-------------|
| `get_current_branch` | 70 | Read | Get currently checked-out branch |
| `detect_trunk_branch` | 75 | Read | Auto-detect main/master |
| `validate_trunk_branch` | 91 | Read | Verify trunk branch exists |
| `list_local_branches` | 107 | Read | List all local branches |
| `list_remote_branches` | 119 | Read | List remote branches |
| `create_tracking_branch` | 134 | Write | Create local tracking branch |
| `create_branch` | 232 | Write | Create new branch |
| `delete_branch` | 243 | Write | Delete local branch |
| `delete_branch_with_graphite` | 254 | Write | Delete via gt command |
| `checkout_branch` | 222 | Write | Switch to branch |
| `checkout_detached` | 227 | Write | Checkout detached HEAD |
| `get_branch_head` | 341 | Read | Get commit SHA for branch |

---

## Files to Create

### 1. `packages/erk-shared/src/erk_shared/git/branches/__init__.py`

```python
"""Git branch operations integration."""

from erk_shared.git.branches.abc import GitBranches
from erk_shared.git.branches.dry_run import DryRunGitBranches
from erk_shared.git.branches.fake import FakeGitBranches
from erk_shared.git.branches.printing import PrintingGitBranches
from erk_shared.git.branches.real import RealGitBranches

__all__ = [
    "GitBranches",
    "DryRunGitBranches",
    "FakeGitBranches",
    "PrintingGitBranches",
    "RealGitBranches",
]
```

### 2. `packages/erk-shared/src/erk_shared/git/branches/abc.py`

```python
"""Abstract interface for git branch operations."""

from abc import ABC, abstractmethod
from pathlib import Path


class GitBranches(ABC):
    """Abstract interface for git branch operations.

    All implementations (real, fake, dry-run) must implement this interface.
    """

    @abstractmethod
    def get_current_branch(self, cwd: Path) -> str | None:
        """Get the currently checked-out branch."""
        ...

    @abstractmethod
    def detect_trunk_branch(self, repo_root: Path) -> str:
        """Auto-detect the trunk branch name (main/master)."""
        ...

    @abstractmethod
    def validate_trunk_branch(self, repo_root: Path, name: str) -> str:
        """Validate that a configured trunk branch exists."""
        ...

    @abstractmethod
    def list_local_branches(self, repo_root: Path) -> list[str]:
        """List all local branch names."""
        ...

    @abstractmethod
    def list_remote_branches(self, repo_root: Path) -> list[str]:
        """List all remote branch names (e.g., 'origin/main')."""
        ...

    @abstractmethod
    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        """Create a local tracking branch from a remote branch."""
        ...

    @abstractmethod
    def create_branch(self, cwd: Path, branch_name: str, start_point: str) -> None:
        """Create a new branch without checking it out."""
        ...

    @abstractmethod
    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        """Delete a local branch."""
        ...

    @abstractmethod
    def delete_branch_with_graphite(self, repo_root: Path, branch: str, *, force: bool) -> None:
        """Delete a branch using Graphite's gt delete command."""
        ...

    @abstractmethod
    def checkout_branch(self, cwd: Path, branch: str) -> None:
        """Checkout a branch in the given directory."""
        ...

    @abstractmethod
    def checkout_detached(self, cwd: Path, ref: str) -> None:
        """Checkout a detached HEAD at the given ref."""
        ...

    @abstractmethod
    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        """Get the commit SHA at the head of a branch."""
        ...
```

### 3. `packages/erk-shared/src/erk_shared/git/branches/real.py`

Extract from `packages/erk-shared/src/erk_shared/git/real.py`:

| Method | Source Lines |
|--------|--------------|
| `get_current_branch` | 60-76 |
| `detect_trunk_branch` | 78-111 |
| `validate_trunk_branch` | 113-139 |
| `list_local_branches` | 141-149 |
| `list_remote_branches` | 151-158 |
| `create_tracking_branch` | 160-166 |
| `create_branch` | 315-321 |
| `delete_branch` | 323-330 |
| `delete_branch_with_graphite` | 332-341 |
| `checkout_branch` | 299-305 |
| `checkout_detached` | 307-313 |
| `get_branch_head` | 382-394 |

```python
"""Production GitBranches implementation using subprocess."""

import subprocess
from pathlib import Path

from erk_shared.git.branches.abc import GitBranches
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitBranches(GitBranches):
    """Production implementation using subprocess."""

    def get_current_branch(self, cwd: Path) -> str | None:
        # Copy from RealGit.get_current_branch
        ...

    def detect_trunk_branch(self, repo_root: Path) -> str:
        # Copy from RealGit.detect_trunk_branch
        ...

    # ... (all 12 methods)
```

### 4. `packages/erk-shared/src/erk_shared/git/branches/fake.py`

Extract from `packages/erk-shared/src/erk_shared/git/fake.py`:

```python
"""Fake git branch operations for testing."""

import subprocess
from pathlib import Path

from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.branches.abc import GitBranches


class FakeGitBranches(GitBranches):
    """In-memory fake implementation of git branch operations.

    State Management:
    - current_branches: dict[Path, str | None] - Mapping of cwd -> current branch
    - trunk_branches: dict[Path, str] - Mapping of repo_root -> trunk branch
    - local_branches: dict[Path, list[str]] - Mapping of repo_root -> local branches
    - remote_branches: dict[Path, list[str]] - Mapping of repo_root -> remote branches
    - branch_heads: dict[str, str] - Mapping of branch name -> commit SHA
    - worktrees: dict[Path, list[WorktreeInfo]] - For checkout validation

    Mutation Tracking:
    - deleted_branches: list[str]
    - checked_out_branches: list[tuple[Path, str]]
    - detached_checkouts: list[tuple[Path, str]]
    - created_tracking_branches: list[tuple[str, str]]
    """

    def __init__(
        self,
        *,
        current_branches: dict[Path, str | None] | None = None,
        trunk_branches: dict[Path, str] | None = None,
        local_branches: dict[Path, list[str]] | None = None,
        remote_branches: dict[Path, list[str]] | None = None,
        branch_heads: dict[str, str] | None = None,
        worktrees: dict[Path, list[WorktreeInfo]] | None = None,
        delete_branch_raises: dict[str, Exception] | None = None,
        tracking_branch_failures: dict[str, str] | None = None,
    ) -> None:
        self._current_branches = current_branches or {}
        self._trunk_branches = trunk_branches or {}
        self._local_branches = local_branches or {}
        self._remote_branches = remote_branches or {}
        self._branch_heads = branch_heads or {}
        self._worktrees = worktrees or {}
        self._delete_branch_raises = delete_branch_raises or {}
        self._tracking_branch_failures = tracking_branch_failures or {}

        # Mutation tracking
        self._deleted_branches: list[str] = []
        self._checked_out_branches: list[tuple[Path, str]] = []
        self._detached_checkouts: list[tuple[Path, str]] = []
        self._created_tracking_branches: list[tuple[str, str]] = []

    # ... implementations from FakeGit

    # Read-only properties for test assertions
    @property
    def deleted_branches(self) -> list[str]:
        return self._deleted_branches.copy()

    @property
    def checked_out_branches(self) -> list[tuple[Path, str]]:
        return self._checked_out_branches.copy()

    @property
    def detached_checkouts(self) -> list[tuple[Path, str]]:
        return self._detached_checkouts.copy()

    @property
    def created_tracking_branches(self) -> list[tuple[str, str]]:
        return self._created_tracking_branches.copy()
```

### 5. `packages/erk-shared/src/erk_shared/git/branches/dry_run.py`

```python
"""No-op GitBranches wrapper for dry-run mode."""

from pathlib import Path

from erk_shared.git.branches.abc import GitBranches
from erk_shared.output.output import user_output


class DryRunGitBranches(GitBranches):
    """No-op wrapper that prevents execution of destructive operations."""

    def __init__(self, wrapped: GitBranches) -> None:
        self._wrapped = wrapped

    # Read-only: delegate
    def get_current_branch(self, cwd: Path) -> str | None:
        return self._wrapped.get_current_branch(cwd)

    def detect_trunk_branch(self, repo_root: Path) -> str:
        return self._wrapped.detect_trunk_branch(repo_root)

    def validate_trunk_branch(self, repo_root: Path, name: str) -> str:
        return self._wrapped.validate_trunk_branch(repo_root, name)

    def list_local_branches(self, repo_root: Path) -> list[str]:
        return self._wrapped.list_local_branches(repo_root)

    def list_remote_branches(self, repo_root: Path) -> list[str]:
        return self._wrapped.list_remote_branches(repo_root)

    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        return self._wrapped.get_branch_head(repo_root, branch)

    # Write operations: no-op or print dry-run message
    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        pass  # No-op

    def create_branch(self, cwd: Path, branch_name: str, start_point: str) -> None:
        user_output(f"[DRY RUN] Would run: git branch {branch_name} {start_point}")

    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        flag = "-D" if force else "-d"
        user_output(f"[DRY RUN] Would run: git branch {flag} {branch_name}")

    def delete_branch_with_graphite(self, repo_root: Path, branch: str, *, force: bool) -> None:
        force_flag = "-f " if force else ""
        user_output(f"[DRY RUN] Would run: gt delete {force_flag}{branch}")

    def checkout_branch(self, cwd: Path, branch: str) -> None:
        pass  # No-op

    def checkout_detached(self, cwd: Path, ref: str) -> None:
        pass  # No-op
```

### 6. `packages/erk-shared/src/erk_shared/git/branches/printing.py`

```python
"""Printing GitBranches wrapper for verbose output."""

from pathlib import Path

from erk_shared.git.branches.abc import GitBranches
from erk_shared.printing.base import PrintingBase


class PrintingGitBranches(PrintingBase, GitBranches):
    """Wrapper that prints operations before delegating."""

    # Read-only: delegate without printing
    def get_current_branch(self, cwd: Path) -> str | None:
        return self._wrapped.get_current_branch(cwd)

    def detect_trunk_branch(self, repo_root: Path) -> str:
        return self._wrapped.detect_trunk_branch(repo_root)

    def validate_trunk_branch(self, repo_root: Path, name: str) -> str:
        return self._wrapped.validate_trunk_branch(repo_root, name)

    def list_local_branches(self, repo_root: Path) -> list[str]:
        return self._wrapped.list_local_branches(repo_root)

    def list_remote_branches(self, repo_root: Path) -> list[str]:
        return self._wrapped.list_remote_branches(repo_root)

    def get_branch_head(self, repo_root: Path, branch: str) -> str | None:
        return self._wrapped.get_branch_head(repo_root, branch)

    # Write operations: print then delegate
    def checkout_branch(self, cwd: Path, branch: str) -> None:
        self._emit(self._format_command(f"git checkout {branch}"))
        self._wrapped.checkout_branch(cwd, branch)

    def checkout_detached(self, cwd: Path, ref: str) -> None:
        self._wrapped.checkout_detached(cwd, ref)

    def create_tracking_branch(self, repo_root: Path, branch: str, remote_ref: str) -> None:
        self._wrapped.create_tracking_branch(repo_root, branch, remote_ref)

    def create_branch(self, cwd: Path, branch_name: str, start_point: str) -> None:
        self._wrapped.create_branch(cwd, branch_name, start_point)

    def delete_branch(self, cwd: Path, branch_name: str, *, force: bool) -> None:
        self._wrapped.delete_branch(cwd, branch_name, force=force)

    def delete_branch_with_graphite(self, repo_root: Path, branch: str, *, force: bool) -> None:
        self._wrapped.delete_branch_with_graphite(repo_root, branch, force=force)
```

---

## Files to Modify

### 1. `src/erk/core/context.py`

Add `git_branches` field to `ErkContext`:

```python
@dataclass(frozen=True)
class ErkContext:
    git: Git
    git_worktrees: GitWorktrees
    git_branches: GitBranches  # NEW
    github: GitHub
    # ...
```

Update `create_context()`:
```python
from erk_shared.git.branches import RealGitBranches, DryRunGitBranches

def create_context(*, dry_run: bool, script: bool = False) -> ErkContext:
    # ...
    git_branches: GitBranches = RealGitBranches()

    if dry_run:
        git_branches = DryRunGitBranches(git_branches)

    return ErkContext(
        git=git,
        git_worktrees=git_worktrees,
        git_branches=git_branches,  # NEW
        # ...
    )
```

Update `ErkContext.minimal()` and `ErkContext.for_test()` factory methods.

### 2. Callsite Migration

Find all usages of the 12 branch methods and migrate:

```bash
# Find callsites
rg "\.get_current_branch\(" --type py
rg "\.detect_trunk_branch\(" --type py
rg "\.validate_trunk_branch\(" --type py
rg "\.list_local_branches\(" --type py
rg "\.list_remote_branches\(" --type py
rg "\.create_tracking_branch\(" --type py
rg "\.create_branch\(" --type py
rg "\.delete_branch\(" --type py
rg "\.delete_branch_with_graphite\(" --type py
rg "\.checkout_branch\(" --type py
rg "\.checkout_detached\(" --type py
rg "\.get_branch_head\(" --type py
```

Migration pattern:
```python
# Before
ctx.git.checkout_branch(cwd, branch)
ctx.git.get_current_branch(cwd)

# After
ctx.git_branches.checkout_branch(cwd, branch)
ctx.git_branches.get_current_branch(cwd)
```

### 3. Remove Methods from Git ABC

After all callsites are migrated, remove the 12 methods from:
- `packages/erk-shared/src/erk_shared/git/abc.py`
- `packages/erk-shared/src/erk_shared/git/real.py`
- `packages/erk-shared/src/erk_shared/git/fake.py`
- `packages/erk-shared/src/erk_shared/git/dry_run.py`
- `packages/erk-shared/src/erk_shared/git/printing.py`

---

## Implementation Steps

1. **Create directory and files**
   ```bash
   mkdir -p packages/erk-shared/src/erk_shared/git/branches
   ```

2. **Create ABC** (`abc.py`)
   - Define `GitBranches` ABC with 12 abstract methods

3. **Create Real implementation** (`real.py`)
   - Copy method implementations from `RealGit`
   - Keep all subprocess patterns identical

4. **Create Fake implementation** (`fake.py`)
   - Extract branch-related state from `FakeGit.__init__`
   - Copy method implementations
   - Add mutation tracking properties
   - **Note:** `checkout_branch` needs access to worktrees for validation

5. **Create DryRun wrapper** (`dry_run.py`)
   - Delegate reads to wrapped
   - No-op or print messages for writes

6. **Create Printing wrapper** (`printing.py`)
   - Delegate all to wrapped

7. **Create `__init__.py`** with exports

8. **Add to ErkContext**
   - Add `git_branches: GitBranches` field
   - Update `create_context()`, `minimal()`, `for_test()`

9. **Migrate callsites**
   - Search for all 12 method usages
   - Update each to use `ctx.git_branches`

10. **Remove from Git**
    - Delete 12 methods from Git ABC and implementations
    - Verify all tests pass

11. **Run CI**
    - `uv run pyright`
    - `uv run pytest`

---

## Special Consideration: checkout_branch Validation

In `FakeGit.checkout_branch()`, there's validation that checks if a branch is already checked out in another worktree:

```python
def checkout_branch(self, cwd: Path, branch: str) -> None:
    # Check if branch is already checked out in a different worktree
    for _repo_root, worktrees in self._worktrees.items():
        for wt in worktrees:
            if wt.branch == branch and wt.path.resolve() != cwd.resolve():
                msg = f"fatal: '{branch}' is already checked out at '{wt.path}'"
                raise RuntimeError(msg)
    ...
```

For `FakeGitBranches`, we have two options:

1. **Pass worktrees to constructor** - `FakeGitBranches(worktrees=...)` for validation
2. **Skip validation in fake** - Real git handles this, fake doesn't need to replicate

Recommendation: **Option 1** - Pass worktrees to constructor for test fidelity.

---

## Exit Criteria

- [ ] `GitBranches` ABC exists with 12 abstract methods
- [ ] `RealGitBranches` implements all 12 methods
- [ ] `FakeGitBranches` implements all 12 methods with mutation tracking
- [ ] `DryRunGitBranches` wraps real implementation
- [ ] `PrintingGitBranches` provides logging decorator
- [ ] `ErkContext.git_branches` field exists
- [ ] All callsites migrated from `ctx.git.X` to `ctx.git_branches.X`
- [ ] 12 methods removed from `Git` ABC
- [ ] All tests pass
- [ ] pyright passes

---

## Skills to Load

- `dignified-python-313` - Modern Python type syntax
- `fake-driven-testing` - 5-layer testing architecture

## Critical Files

**Create:**
- `packages/erk-shared/src/erk_shared/git/branches/__init__.py`
- `packages/erk-shared/src/erk_shared/git/branches/abc.py`
- `packages/erk-shared/src/erk_shared/git/branches/real.py`
- `packages/erk-shared/src/erk_shared/git/branches/fake.py`
- `packages/erk-shared/src/erk_shared/git/branches/dry_run.py`
- `packages/erk-shared/src/erk_shared/git/branches/printing.py`

**Modify:**
- `src/erk/core/context.py` - Add `git_branches` field
- `packages/erk-shared/src/erk_shared/git/abc.py` - Remove 12 methods
- `packages/erk-shared/src/erk_shared/git/real.py` - Remove 12 methods
- `packages/erk-shared/src/erk_shared/git/fake.py` - Remove 12 methods
- `packages/erk-shared/src/erk_shared/git/dry_run.py` - Remove 12 methods
- `packages/erk-shared/src/erk_shared/git/printing.py` - Remove 12 methods
- All files with callsites (find via grep)

**Reference:**
- `packages/erk-shared/src/erk_shared/git/worktrees/` - Phase 2 pattern