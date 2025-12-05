# Phase 2: GitWorktrees Implementation Plan

## Goal

Extract worktree operations from the monolithic `Git` class into a new parallel integration `GitWorktrees`, following the established pattern of `GitHub`/`GitHubIssues`.

## Pattern Reference

From `src/erk/core/context.py`, integrations are **parallel at ErkContext level**:
```python
@dataclass(frozen=True)
class ErkContext:
    git: Git
    github: GitHub
    issues: GitHubIssues          # Parallel to github, not nested
    issue_link_branches: IssueLinkBranches
    # ...
```

New access pattern after refactoring:
```python
ctx.git.commit(...)               # Core Git operations
ctx.git_worktrees.add_worktree()  # NEW: Separate worktree integration
```

---

## Files to Create

### 1. `packages/erk-shared/src/erk_shared/git/worktrees/__init__.py`

```python
"""Git worktree operations integration."""

from erk_shared.git.worktrees.abc import GitWorktrees
from erk_shared.git.worktrees.dry_run import DryRunGitWorktrees
from erk_shared.git.worktrees.fake import FakeGitWorktrees
from erk_shared.git.worktrees.printing import PrintingGitWorktrees
from erk_shared.git.worktrees.real import RealGitWorktrees

__all__ = [
    "GitWorktrees",
    "DryRunGitWorktrees",
    "FakeGitWorktrees",
    "PrintingGitWorktrees",
    "RealGitWorktrees",
]
```

### 2. `packages/erk-shared/src/erk_shared/git/worktrees/abc.py`

Extract these 8 methods from `packages/erk-shared/src/erk_shared/git/abc.py`:

| Method | Current Line | Read/Write |
|--------|--------------|------------|
| `list_worktrees` | 65 | Read |
| `add_worktree` | 185 | Write |
| `move_worktree` | 206 | Write |
| `remove_worktree` | 211 | Write |
| `prune_worktrees` | 259 | Write |
| `is_branch_checked_out` | 315 | Read |
| `find_worktree_for_branch` | 328 | Read |
| `get_git_common_dir` | 148 | Read |

```python
"""Abstract interface for git worktree operations."""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.git.abc import WorktreeInfo


class GitWorktrees(ABC):
    """Abstract interface for git worktree operations.

    All implementations (real, fake, dry-run) must implement this interface.
    """

    @abstractmethod
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        """List all worktrees in the repository."""
        ...

    @abstractmethod
    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory."""
        ...

    @abstractmethod
    def add_worktree(
        self,
        repo_root: Path,
        path: Path,
        *,
        branch: str | None,
        ref: str | None,
        create_branch: bool,
    ) -> None:
        """Add a new git worktree."""
        ...

    @abstractmethod
    def move_worktree(self, repo_root: Path, old_path: Path, new_path: Path) -> None:
        """Move a worktree to a new location."""
        ...

    @abstractmethod
    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool) -> None:
        """Remove a worktree."""
        ...

    @abstractmethod
    def prune_worktrees(self, repo_root: Path) -> None:
        """Prune stale worktree metadata."""
        ...

    @abstractmethod
    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        """Check if a branch is already checked out in any worktree."""
        ...

    @abstractmethod
    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        """Find worktree path for given branch name."""
        ...
```

### 3. `packages/erk-shared/src/erk_shared/git/worktrees/real.py`

Extract from `packages/erk-shared/src/erk_shared/git/real.py` (lines 23-58, 168-184, 246-297, 343-349, 366-380):

```python
"""Production GitWorktrees implementation using subprocess."""

from pathlib import Path

from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.worktrees.abc import GitWorktrees
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitWorktrees(GitWorktrees):
    """Production implementation using subprocess."""

    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        # Copy implementation from RealGit.list_worktrees (lines 23-58)
        ...

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        # Copy implementation from RealGit.get_git_common_dir (lines 168-184)
        ...

    def add_worktree(self, repo_root: Path, path: Path, *, branch: str | None, ref: str | None, create_branch: bool) -> None:
        # Copy implementation from RealGit.add_worktree (lines 246-268)
        ...

    def move_worktree(self, repo_root: Path, old_path: Path, new_path: Path) -> None:
        # Copy implementation from RealGit.move_worktree (lines 270-277)
        ...

    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool) -> None:
        # Copy implementation from RealGit.remove_worktree (lines 279-297)
        ...

    def prune_worktrees(self, repo_root: Path) -> None:
        # Copy implementation from RealGit.prune_worktrees (lines 343-349)
        ...

    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        # Copy implementation from RealGit.is_branch_checked_out (lines 366-372)
        ...

    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        # Copy implementation from RealGit.find_worktree_for_branch (lines 374-380)
        ...
```

### 4. `packages/erk-shared/src/erk_shared/git/worktrees/fake.py`

Extract from `packages/erk-shared/src/erk_shared/git/fake.py`:

```python
"""Fake git worktree operations for testing."""

from pathlib import Path

from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.worktrees.abc import GitWorktrees


class FakeGitWorktrees(GitWorktrees):
    """In-memory fake implementation of git worktree operations.

    State Management:
    - worktrees: dict[Path, list[WorktreeInfo]] - Mapping of repo_root -> worktrees
    - git_common_dirs: dict[Path, Path] - Mapping of cwd -> git common directory
    - existing_paths: set[Path] - Paths that exist in the fake filesystem

    Mutation Tracking:
    - added_worktrees: list[tuple[Path, str | None]]
    - removed_worktrees: list[Path]
    """

    def __init__(
        self,
        *,
        worktrees: dict[Path, list[WorktreeInfo]] | None = None,
        git_common_dirs: dict[Path, Path] | None = None,
        existing_paths: set[Path] | None = None,
    ) -> None:
        self._worktrees = worktrees or {}
        self._git_common_dirs = git_common_dirs or {}
        self._existing_paths = existing_paths or set()

        # Mutation tracking
        self._added_worktrees: list[tuple[Path, str | None]] = []
        self._removed_worktrees: list[Path] = []

    # Extract implementations from FakeGit (lines 174-195, 250-271, 294-338, 418-436)
    ...

    # Read-only properties for test assertions
    @property
    def added_worktrees(self) -> list[tuple[Path, str | None]]:
        return self._added_worktrees.copy()

    @property
    def removed_worktrees(self) -> list[Path]:
        return self._removed_worktrees.copy()
```

### 5. `packages/erk-shared/src/erk_shared/git/worktrees/dry_run.py`

Follow pattern from `packages/erk-shared/src/erk_shared/git/dry_run.py`:

```python
"""No-op GitWorktrees wrapper for dry-run mode."""

from pathlib import Path

from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.worktrees.abc import GitWorktrees
from erk_shared.output.output import user_output


class DryRunGitWorktrees(GitWorktrees):
    """No-op wrapper that prevents execution of destructive operations."""

    def __init__(self, wrapped: GitWorktrees) -> None:
        self._wrapped = wrapped

    # Read-only: delegate
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        return self._wrapped.list_worktrees(repo_root)

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        return self._wrapped.get_git_common_dir(cwd)

    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        return self._wrapped.is_branch_checked_out(repo_root, branch)

    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        return self._wrapped.find_worktree_for_branch(repo_root, branch)

    # Write operations: print dry-run message
    def add_worktree(self, repo_root: Path, path: Path, *, branch: str | None, ref: str | None, create_branch: bool) -> None:
        if branch and create_branch:
            base_ref = ref or "HEAD"
            user_output(f"[DRY RUN] Would run: git worktree add -b {branch} {path} {base_ref}")
        elif branch:
            user_output(f"[DRY RUN] Would run: git worktree add {path} {branch}")
        else:
            base_ref = ref or "HEAD"
            user_output(f"[DRY RUN] Would run: git worktree add {path} {base_ref}")

    def move_worktree(self, repo_root: Path, old_path: Path, new_path: Path) -> None:
        user_output(f"[DRY RUN] Would run: git worktree move {old_path} {new_path}")

    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool) -> None:
        force_flag = "--force " if force else ""
        user_output(f"[DRY RUN] Would run: git worktree remove {force_flag}{path}")

    def prune_worktrees(self, repo_root: Path) -> None:
        user_output("[DRY RUN] Would run: git worktree prune")
```

### 6. `packages/erk-shared/src/erk_shared/git/worktrees/printing.py`

Follow pattern from `packages/erk-shared/src/erk_shared/git/printing.py`:

```python
"""Printing GitWorktrees wrapper for verbose output."""

from pathlib import Path

from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.worktrees.abc import GitWorktrees
from erk_shared.printing.base import PrintingBase


class PrintingGitWorktrees(PrintingBase, GitWorktrees):
    """Wrapper that prints operations before delegating."""

    # Read-only: delegate without printing
    def list_worktrees(self, repo_root: Path) -> list[WorktreeInfo]:
        return self._wrapped.list_worktrees(repo_root)

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        return self._wrapped.get_git_common_dir(cwd)

    def is_branch_checked_out(self, repo_root: Path, branch: str) -> Path | None:
        return self._wrapped.is_branch_checked_out(repo_root, branch)

    def find_worktree_for_branch(self, repo_root: Path, branch: str) -> Path | None:
        return self._wrapped.find_worktree_for_branch(repo_root, branch)

    # Write operations: delegate without printing (not used in land-stack)
    def add_worktree(self, repo_root: Path, path: Path, *, branch: str | None, ref: str | None, create_branch: bool) -> None:
        self._wrapped.add_worktree(repo_root, path, branch=branch, ref=ref, create_branch=create_branch)

    def move_worktree(self, repo_root: Path, old_path: Path, new_path: Path) -> None:
        self._wrapped.move_worktree(repo_root, old_path, new_path)

    def remove_worktree(self, repo_root: Path, path: Path, *, force: bool) -> None:
        self._wrapped.remove_worktree(repo_root, path, force=force)

    def prune_worktrees(self, repo_root: Path) -> None:
        self._wrapped.prune_worktrees(repo_root)
```

---

## Files to Modify

### 1. `src/erk/core/context.py`

Add `git_worktrees` field to `ErkContext`:

```python
@dataclass(frozen=True)
class ErkContext:
    git: Git
    git_worktrees: GitWorktrees  # NEW
    github: GitHub
    # ...
```

Update `create_context()`:
```python
from erk_shared.git.worktrees import RealGitWorktrees, DryRunGitWorktrees

def create_context(*, dry_run: bool, script: bool = False) -> ErkContext:
    # ...
    git_worktrees: GitWorktrees = RealGitWorktrees()

    if dry_run:
        git_worktrees = DryRunGitWorktrees(git_worktrees)

    return ErkContext(
        git=git,
        git_worktrees=git_worktrees,  # NEW
        # ...
    )
```

Update `ErkContext.minimal()` and `ErkContext.for_test()` factory methods.

### 2. Callsite Migration

Find all usages of the 8 worktree methods and migrate:

```bash
# Find callsites
rg "\.list_worktrees\(" --type py
rg "\.add_worktree\(" --type py
rg "\.move_worktree\(" --type py
rg "\.remove_worktree\(" --type py
rg "\.prune_worktrees\(" --type py
rg "\.is_branch_checked_out\(" --type py
rg "\.find_worktree_for_branch\(" --type py
rg "\.get_git_common_dir\(" --type py
```

Migration pattern:
```python
# Before
ctx.git.list_worktrees(repo_root)
ctx.git.add_worktree(repo_root, path, branch=branch, ref=ref, create_branch=True)

# After
ctx.git_worktrees.list_worktrees(repo_root)
ctx.git_worktrees.add_worktree(repo_root, path, branch=branch, ref=ref, create_branch=True)
```

### 3. Remove Methods from Git ABC

After all callsites are migrated, remove the 8 methods from:
- `packages/erk-shared/src/erk_shared/git/abc.py`
- `packages/erk-shared/src/erk_shared/git/real.py`
- `packages/erk-shared/src/erk_shared/git/fake.py`
- `packages/erk-shared/src/erk_shared/git/dry_run.py`
- `packages/erk-shared/src/erk_shared/git/printing.py`

**Keep `WorktreeInfo` in `abc.py`** - it's a shared type.

---

## Implementation Steps

1. **Create directory and files**
   ```bash
   mkdir -p packages/erk-shared/src/erk_shared/git/worktrees
   ```

2. **Create ABC** (`abc.py`)
   - Define `GitWorktrees` ABC with 8 abstract methods
   - Import `WorktreeInfo` from `erk_shared.git.abc`

3. **Create Real implementation** (`real.py`)
   - Copy method implementations from `RealGit`
   - Keep all subprocess patterns identical

4. **Create Fake implementation** (`fake.py`)
   - Extract worktree-related state from `FakeGit.__init__`
   - Copy method implementations
   - Add mutation tracking properties

5. **Create DryRun wrapper** (`dry_run.py`)
   - Delegate reads to wrapped
   - Print messages for writes

6. **Create Printing wrapper** (`printing.py`)
   - Delegate all to wrapped

7. **Create `__init__.py`** with exports

8. **Add to ErkContext**
   - Add `git_worktrees: GitWorktrees` field
   - Update `create_context()`, `minimal()`, `for_test()`

9. **Migrate callsites**
   - Search for all 8 method usages
   - Update each to use `ctx.git_worktrees`

10. **Remove from Git**
    - Delete 8 methods from Git ABC and implementations
    - Verify all tests pass

11. **Run CI**
    - `uv run pyright`
    - `uv run pytest`

---

## Exit Criteria

- [ ] `GitWorktrees` ABC exists with 8 abstract methods
- [ ] `RealGitWorktrees` implements all 8 methods
- [ ] `FakeGitWorktrees` implements all 8 methods with mutation tracking
- [ ] `DryRunGitWorktrees` wraps real implementation
- [ ] `PrintingGitWorktrees` provides logging decorator
- [ ] `ErkContext.git_worktrees` field exists
- [ ] All callsites migrated from `ctx.git.X` to `ctx.git_worktrees.X`
- [ ] 8 methods removed from `Git` ABC
- [ ] All tests pass
- [ ] pyright passes

---

## Skills to Load

- `dignified-python-313` - Modern Python type syntax
- `fake-driven-testing` - 5-layer testing architecture

## Critical Files

**Create:**
- `packages/erk-shared/src/erk_shared/git/worktrees/__init__.py`
- `packages/erk-shared/src/erk_shared/git/worktrees/abc.py`
- `packages/erk-shared/src/erk_shared/git/worktrees/real.py`
- `packages/erk-shared/src/erk_shared/git/worktrees/fake.py`
- `packages/erk-shared/src/erk_shared/git/worktrees/dry_run.py`
- `packages/erk-shared/src/erk_shared/git/worktrees/printing.py`

**Modify:**
- `src/erk/core/context.py` - Add `git_worktrees` field
- `packages/erk-shared/src/erk_shared/git/abc.py` - Remove 8 methods (keep `WorktreeInfo`)
- `packages/erk-shared/src/erk_shared/git/real.py` - Remove 8 methods
- `packages/erk-shared/src/erk_shared/git/fake.py` - Remove 8 methods
- `packages/erk-shared/src/erk_shared/git/dry_run.py` - Remove 8 methods
- `packages/erk-shared/src/erk_shared/git/printing.py` - Remove 8 methods
- All files with callsites (find via grep)

**Reference:**
- `packages/erk-shared/src/erk_shared/github/issues/` - Pattern for sub-integration