# Plan: Phase 5 - Status Subgateway Extraction

**Part of Objective #6169, Steps 5.1-5.5**

## Goal

Extract status query operations from Git ABC into a dedicated `git/status_ops/` subgateway module, following the established pattern from remote_ops (Phase 3).

## Key Insight: All Read-Only

All 5 status methods are **read-only queries** - they don't mutate state. This simplifies:

- FakeGitStatusOps: No mutation tracking needed (unlike remote_ops)
- DryRunGitStatusOps: Simply delegates everything (no no-ops)
- PrintingGitStatusOps: Simply delegates without printing (read-only ops don't print)

## Methods to Extract

| Method                    | Signature                                                 | Purpose                                   |
| ------------------------- | --------------------------------------------------------- | ----------------------------------------- |
| `has_staged_changes`      | `(repo_root: Path) -> bool`                               | Check if repo has staged changes          |
| `has_uncommitted_changes` | `(cwd: Path) -> bool`                                     | Check if worktree has uncommitted changes |
| `get_file_status`         | `(cwd: Path) -> tuple[list[str], list[str], list[str]]`   | Get staged, modified, untracked files     |
| `check_merge_conflicts`   | `(cwd: Path, base_branch: str, head_branch: str) -> bool` | Check if merge would have conflicts       |
| `get_conflicted_files`    | `(cwd: Path) -> list[str]`                                | Get list of files with merge conflicts    |

---

## Implementation Steps

### Step 1: Create `status_ops/__init__.py`

**File:** `packages/erk-shared/src/erk_shared/gateway/git/status_ops/__init__.py`

```python
"""Git status operations subgateway."""

from erk_shared.gateway.git.status_ops.abc import GitStatusOps
from erk_shared.gateway.git.status_ops.dry_run import DryRunGitStatusOps
from erk_shared.gateway.git.status_ops.fake import FakeGitStatusOps
from erk_shared.gateway.git.status_ops.printing import PrintingGitStatusOps
from erk_shared.gateway.git.status_ops.real import RealGitStatusOps

__all__ = [
    "GitStatusOps",
    "RealGitStatusOps",
    "FakeGitStatusOps",
    "DryRunGitStatusOps",
    "PrintingGitStatusOps",
]
```

### Step 2: Create `status_ops/abc.py`

**File:** `packages/erk-shared/src/erk_shared/gateway/git/status_ops/abc.py`

```python
"""Abstract base class for Git status operations.

This sub-gateway extracts status query operations from the main Git gateway,
including staged changes, uncommitted changes, file status, and conflict detection.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class GitStatusOps(ABC):
    """Abstract interface for Git status operations.

    This interface contains ONLY query operations (no mutations).
    All implementations (real, fake, dry-run, printing) must implement this interface.
    """

    @abstractmethod
    def has_staged_changes(self, repo_root: Path) -> bool:
        """Check if the repository has staged changes.

        Args:
            repo_root: Path to the git repository root

        Returns:
            True if there are staged changes, False otherwise
        """
        ...

    @abstractmethod
    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check if a worktree has uncommitted changes.

        Uses git status --porcelain to detect any uncommitted changes.
        Returns False if git command fails (worktree might be in invalid state).

        Args:
            cwd: Working directory to check

        Returns:
            True if there are any uncommitted changes (staged, modified, or untracked)
        """
        ...

    @abstractmethod
    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get lists of staged, modified, and untracked files.

        Args:
            cwd: Working directory

        Returns:
            Tuple of (staged, modified, untracked) file lists
        """
        ...

    @abstractmethod
    def check_merge_conflicts(self, cwd: Path, base_branch: str, head_branch: str) -> bool:
        """Check if merging would have conflicts using git merge-tree.

        Args:
            cwd: Working directory
            base_branch: Base branch to merge into
            head_branch: Head branch to merge from

        Returns:
            True if merge would have conflicts, False otherwise
        """
        ...

    @abstractmethod
    def get_conflicted_files(self, cwd: Path) -> list[str]:
        """Get list of files with merge conflicts from git status --porcelain.

        Returns file paths with conflict status codes (UU, AA, DD, AU, UA, DU, UD).

        Args:
            cwd: Working directory

        Returns:
            List of file paths with conflicts
        """
        ...
```

### Step 3: Create `status_ops/real.py`

**File:** `packages/erk-shared/src/erk_shared/gateway/git/status_ops/real.py`

Copy implementations from `packages/erk-shared/src/erk_shared/gateway/git/real.py` lines 75-101, 116-147, 258-290.

```python
"""Production implementation of Git status operations using subprocess."""

import subprocess
from pathlib import Path

from erk_shared.gateway.git.status_ops.abc import GitStatusOps
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitStatusOps(GitStatusOps):
    """Real implementation of Git status operations using subprocess."""

    def has_staged_changes(self, repo_root: Path) -> bool:
        """Check if the repository has staged changes."""
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode in (0, 1):
            return result.returncode == 1
        result.check_returncode()
        return False

    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check if a worktree has uncommitted changes."""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False
        return bool(result.stdout.strip())

    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get lists of staged, modified, and untracked files."""
        result = run_subprocess_with_context(
            cmd=["git", "status", "--porcelain"],
            operation_context="get file status",
            cwd=cwd,
        )

        staged = []
        modified = []
        untracked = []

        for line in result.stdout.splitlines():
            if not line:
                continue

            status_code = line[:2]
            filename = line[3:]

            # Check if file is staged (first character is not space)
            if status_code[0] != " " and status_code[0] != "?":
                staged.append(filename)

            # Check if file is modified (second character is not space)
            if status_code[1] != " " and status_code[1] != "?":
                modified.append(filename)

            # Check if file is untracked
            if status_code == "??":
                untracked.append(filename)

        return staged, modified, untracked

    def check_merge_conflicts(self, cwd: Path, base_branch: str, head_branch: str) -> bool:
        """Check if merging would have conflicts using git merge-tree."""
        result = subprocess.run(
            ["git", "merge-tree", "--write-tree", base_branch, head_branch],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode != 0

    def get_conflicted_files(self, cwd: Path) -> list[str]:
        """Parse git status --porcelain for UU/AA/DD/AU/UA/DU/UD status codes."""
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return []

        conflict_codes = {"UU", "AA", "DD", "AU", "UA", "DU", "UD"}
        conflicted = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            status = line[:2]
            if status in conflict_codes:
                # File path starts at position 3
                conflicted.append(line[3:])
        return conflicted
```

### Step 4: Create `status_ops/fake.py`

**File:** `packages/erk-shared/src/erk_shared/gateway/git/status_ops/fake.py`

```python
"""Fake implementation of Git status operations for testing."""

from __future__ import annotations

from pathlib import Path

from erk_shared.gateway.git.status_ops.abc import GitStatusOps


class FakeGitStatusOps(GitStatusOps):
    """In-memory fake implementation of Git status operations.

    This fake accepts pre-configured state in its constructor.
    All operations are read-only queries, so no mutation tracking is needed.

    Constructor Injection:
    ---------------------
    - staged_repos: Set of repo roots that have staged changes
    - file_statuses: Mapping of cwd -> (staged, modified, untracked) files
    - merge_conflicts: Mapping of (base_branch, head_branch) -> has conflicts
    - conflicted_files: List of files with merge conflicts
    """

    def __init__(
        self,
        *,
        staged_repos: set[Path] | None = None,
        file_statuses: dict[Path, tuple[list[str], list[str], list[str]]] | None = None,
        merge_conflicts: dict[tuple[str, str], bool] | None = None,
        conflicted_files: list[str] | None = None,
    ) -> None:
        """Create FakeGitStatusOps with pre-configured state.

        Args:
            staged_repos: Set of repo roots that should report staged changes
            file_statuses: Mapping of cwd -> (staged, modified, untracked) files
            merge_conflicts: Mapping of (base_branch, head_branch) -> has conflicts
            conflicted_files: List of files with merge conflicts
        """
        self._staged_repos = staged_repos if staged_repos is not None else set()
        self._file_statuses = file_statuses if file_statuses is not None else {}
        self._merge_conflicts = merge_conflicts if merge_conflicts is not None else {}
        self._conflicted_files = conflicted_files if conflicted_files is not None else []

    def has_staged_changes(self, repo_root: Path) -> bool:
        """Report whether the repository has staged changes."""
        return repo_root in self._staged_repos

    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check if a worktree has uncommitted changes."""
        staged, modified, untracked = self._file_statuses.get(cwd, ([], [], []))
        return bool(staged or modified or untracked)

    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get lists of staged, modified, and untracked files."""
        return self._file_statuses.get(cwd, ([], [], []))

    def check_merge_conflicts(self, cwd: Path, base_branch: str, head_branch: str) -> bool:
        """Check if merging would have conflicts using git merge-tree."""
        return self._merge_conflicts.get((base_branch, head_branch), False)

    def get_conflicted_files(self, cwd: Path) -> list[str]:
        """Get list of files with merge conflicts."""
        return list(self._conflicted_files)

    # ============================================================================
    # Link State (for integration with FakeGit)
    # ============================================================================

    def link_state(
        self,
        *,
        staged_repos: set[Path],
        file_statuses: dict[Path, tuple[list[str], list[str], list[str]]],
        merge_conflicts: dict[tuple[str, str], bool],
        conflicted_files: list[str],
    ) -> None:
        """Link this fake's state to FakeGit's state dictionaries.

        This allows FakeGit to share mutable state with this subgateway,
        enabling tests that modify state via FakeGit to see changes
        reflected in status operations.

        Args:
            staged_repos: FakeGit's _repos_with_staged_changes set
            file_statuses: FakeGit's _file_statuses dict
            merge_conflicts: FakeGit's _merge_conflicts dict
            conflicted_files: FakeGit's _conflicted_files list
        """
        self._staged_repos = staged_repos
        self._file_statuses = file_statuses
        self._merge_conflicts = merge_conflicts
        self._conflicted_files = conflicted_files
```

### Step 5: Create `status_ops/dry_run.py`

**File:** `packages/erk-shared/src/erk_shared/gateway/git/status_ops/dry_run.py`

```python
"""No-op Git status operations wrapper for dry-run mode.

Since all status operations are read-only queries, this wrapper
simply delegates all calls to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.gateway.git.status_ops.abc import GitStatusOps


class DryRunGitStatusOps(GitStatusOps):
    """Pass-through wrapper for status operations in dry-run mode.

    All status operations are read-only queries, so they are simply
    delegated to the wrapped implementation without modification.

    Usage:
        real_ops = RealGitStatusOps()
        dry_run_ops = DryRunGitStatusOps(real_ops)

        # All operations delegate to wrapped
        has_staged = dry_run_ops.has_staged_changes(repo_root)
    """

    def __init__(self, wrapped: GitStatusOps) -> None:
        """Create a dry-run wrapper around a GitStatusOps implementation.

        Args:
            wrapped: The GitStatusOps implementation to wrap (usually RealGitStatusOps)
        """
        self._wrapped = wrapped

    # ============================================================================
    # All operations are read-only - delegate directly
    # ============================================================================

    def has_staged_changes(self, repo_root: Path) -> bool:
        """Check for staged changes (read-only, delegates to wrapped)."""
        return self._wrapped.has_staged_changes(repo_root)

    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check for uncommitted changes (read-only, delegates to wrapped)."""
        return self._wrapped.has_uncommitted_changes(cwd)

    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get file status (read-only, delegates to wrapped)."""
        return self._wrapped.get_file_status(cwd)

    def check_merge_conflicts(self, cwd: Path, base_branch: str, head_branch: str) -> bool:
        """Check merge conflicts (read-only, delegates to wrapped)."""
        return self._wrapped.check_merge_conflicts(cwd, base_branch, head_branch)

    def get_conflicted_files(self, cwd: Path) -> list[str]:
        """Get conflicted files (read-only, delegates to wrapped)."""
        return self._wrapped.get_conflicted_files(cwd)
```

### Step 6: Create `status_ops/printing.py`

**File:** `packages/erk-shared/src/erk_shared/gateway/git/status_ops/printing.py`

```python
"""Printing Git status operations wrapper for verbose output.

Since all status operations are read-only queries, this wrapper
simply delegates all calls without printing (read-only ops don't print).
"""

from pathlib import Path

from erk_shared.gateway.git.status_ops.abc import GitStatusOps
from erk_shared.printing.base import PrintingBase


class PrintingGitStatusOps(PrintingBase, GitStatusOps):
    """Pass-through wrapper for status operations with printing support.

    All status operations are read-only queries, so they are delegated
    to the wrapped implementation without printing output.

    Usage:
        printing_ops = PrintingGitStatusOps(real_ops, script_mode=False, dry_run=False)

        # All operations delegate without printing (read-only)
        has_staged = printing_ops.has_staged_changes(repo_root)
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    # ============================================================================
    # All operations are read-only - delegate without printing
    # ============================================================================

    def has_staged_changes(self, repo_root: Path) -> bool:
        """Check for staged changes (read-only, no printing)."""
        return self._wrapped.has_staged_changes(repo_root)

    def has_uncommitted_changes(self, cwd: Path) -> bool:
        """Check for uncommitted changes (read-only, no printing)."""
        return self._wrapped.has_uncommitted_changes(cwd)

    def get_file_status(self, cwd: Path) -> tuple[list[str], list[str], list[str]]:
        """Get file status (read-only, no printing)."""
        return self._wrapped.get_file_status(cwd)

    def check_merge_conflicts(self, cwd: Path, base_branch: str, head_branch: str) -> bool:
        """Check merge conflicts (read-only, no printing)."""
        return self._wrapped.check_merge_conflicts(cwd, base_branch, head_branch)

    def get_conflicted_files(self, cwd: Path) -> list[str]:
        """Get conflicted files (read-only, no printing)."""
        return self._wrapped.get_conflicted_files(cwd)
```

### Step 7: Add `status` Property to Git ABC

**File:** `packages/erk-shared/src/erk_shared/gateway/git/abc.py`

Add import at top (in TYPE_CHECKING block):

```python
if TYPE_CHECKING:
    from erk_shared.gateway.git.branch_ops.abc import GitBranchOps
    from erk_shared.gateway.git.remote_ops.abc import GitRemoteOps
    from erk_shared.gateway.git.status_ops.abc import GitStatusOps  # ADD THIS
    from erk_shared.gateway.git.worktree.abc import Worktree
```

Add property after `remote` property (around line 117):

```python
    @property
    @abstractmethod
    def status(self) -> GitStatusOps:
        """Access status operations subgateway."""
        ...
```

### Step 8: Update `RealGit`

**File:** `packages/erk-shared/src/erk_shared/gateway/git/real.py`

Add imports:

```python
from erk_shared.gateway.git.status_ops.abc import GitStatusOps
from erk_shared.gateway.git.status_ops.real import RealGitStatusOps
```

In `__init__`, add:

```python
self._status = RealGitStatusOps()
```

Add property:

```python
    @property
    def status(self) -> GitStatusOps:
        """Access status operations subgateway."""
        return self._status
```

### Step 9: Update `FakeGit`

**File:** `packages/erk-shared/src/erk_shared/gateway/git/fake.py`

Add imports:

```python
from erk_shared.gateway.git.status_ops.abc import GitStatusOps
from erk_shared.gateway.git.status_ops.fake import FakeGitStatusOps
```

In `__init__`, after remote_gateway creation (around line 316), add:

```python
        # Status operations subgateway - linked to FakeGit's state
        self._status_gateway = FakeGitStatusOps(
            staged_repos=self._repos_with_staged_changes,
            file_statuses=self._file_statuses,
            merge_conflicts=self._merge_conflicts,
            conflicted_files=self._conflicted_files,
        )
        # Link state so FakeGit modifications are visible to status subgateway
        self._status_gateway.link_state(
            staged_repos=self._repos_with_staged_changes,
            file_statuses=self._file_statuses,
            merge_conflicts=self._merge_conflicts,
            conflicted_files=self._conflicted_files,
        )
```

Add property after `remote` property:

```python
    @property
    def status(self) -> GitStatusOps:
        """Access status operations subgateway."""
        return self._status_gateway
```

### Step 10: Update `DryRunGit`

**File:** `packages/erk-shared/src/erk_shared/gateway/git/dry_run.py`

Add imports:

```python
from erk_shared.gateway.git.status_ops.abc import GitStatusOps
from erk_shared.gateway.git.status_ops.dry_run import DryRunGitStatusOps
```

Add property after `remote` property:

```python
    @property
    def status(self) -> GitStatusOps:
        """Access status operations subgateway (wrapped with DryRunGitStatusOps)."""
        return DryRunGitStatusOps(self._wrapped.status)
```

### Step 11: Update `PrintingGit`

**File:** `packages/erk-shared/src/erk_shared/gateway/git/printing.py`

Add imports:

```python
from erk_shared.gateway.git.status_ops.abc import GitStatusOps
from erk_shared.gateway.git.status_ops.printing import PrintingGitStatusOps
```

Add property after `remote` property:

```python
    @property
    def status(self) -> GitStatusOps:
        """Access status operations subgateway (wrapped with PrintingGitStatusOps)."""
        return PrintingGitStatusOps(
            self._wrapped.status, script_mode=self._script_mode, dry_run=self._dry_run
        )
```

### Step 12: Migrate Callsites

Replace all `git.has_staged_changes(` with `git.status.has_staged_changes(`:

- `src/erk/cli/commands/wt/create_cmd.py:303`
- `packages/erk-shared/src/erk_shared/gateway/gt/operations/quick_submit.py:50`

Replace all `git.has_uncommitted_changes(` with `git.status.has_uncommitted_changes(`:

- `src/erk/cli/commands/navigation_helpers.py:67`
- `src/erk/cli/commands/pr/submit_cmd.py:317`
- `src/erk/cli/commands/submit_helpers.py:48`
- `src/erk/cli/commands/stack/consolidate_cmd.py:274`
- `src/erk/cli/commands/stack/split_old/command.py:65`
- `src/erk/cli/commands/stack/move_cmd.py:119,138,186`
- `src/erk/cli/commands/land_cmd.py:649`
- `src/erk/cli/commands/slot/common.py:179,285`
- `src/erk/cli/commands/slot/unassign_cmd.py:57`
- `src/erk/cli/commands/slot/list_cmd.py:195`
- `packages/erk-statusline/src/erk_statusline/statusline.py:175`
- `packages/erk-shared/src/erk_shared/gateway/gt/operations/pre_analysis.py:76`
- `packages/erk-shared/src/erk_shared/gateway/pr/submit.py:170`

Replace all `git.get_file_status(` with `git.status.get_file_status(`:

- `src/erk/status/collectors/git.py:49`

Replace all `git.check_merge_conflicts(` with `git.status.check_merge_conflicts(`:

- `packages/erk-shared/src/erk_shared/gateway/gt/operations/pre_analysis.py:199`

Replace all `git.get_conflicted_files(` with `git.status.get_conflicted_files(`:

- `src/erk/cli/commands/pr/fix_conflicts_cmd.py:58`
- `src/erk/cli/commands/exec/scripts/rebase_with_conflict_resolution.py:246`

### Step 13: Remove Status Methods from Git ABC and Implementations

**From `abc.py`** - Remove these method declarations:

- `has_staged_changes` (lines 124-126)
- `has_uncommitted_changes` (lines 128-141)
- `get_file_status` (lines 157-165)
- `check_merge_conflicts` (lines 235-237)
- `get_conflicted_files` (lines 239-251)

**From `real.py`** - Remove these method implementations:

- `has_staged_changes` (lines 75-87)
- `has_uncommitted_changes` (lines 89-100)
- `get_file_status` (lines 116-147)
- `check_merge_conflicts` (lines 258-267)
- `get_conflicted_files` (lines 269-290)

**From `fake.py`** - Remove these method implementations:

- `has_staged_changes` (lines 356-358)
- `has_uncommitted_changes` (lines 360-363)
- `get_file_status` (lines 369-371)
- `check_merge_conflicts` (lines 592-594)
- `get_conflicted_files` (lines 596-598)

**From `dry_run.py`** - Remove these delegation methods:

- `has_staged_changes` (lines 70-72)
- `has_uncommitted_changes` (lines 74-76)
- `get_file_status` (lines 82-84)
- `check_merge_conflicts` (lines 122-124)
- `get_conflicted_files` (lines 126-128)

**From `printing.py`** - Remove these delegation methods:

- `has_staged_changes` (lines 87-89)
- `has_uncommitted_changes` (lines 91-93)
- `get_file_status` (lines 124-126)
- `check_merge_conflicts` (lines 171-173)
- `get_conflicted_files` (lines 175-177)

### Step 14: Update Tests

**Update existing fake tests** in `tests/unit/fakes/test_fake_git.py`:

- Change `git_ops.has_uncommitted_changes(cwd)` to `git_ops.status.has_uncommitted_changes(cwd)`
- Change `git_ops.get_file_status(cwd)` to `git_ops.status.get_file_status(cwd)`

**Create new test file** `tests/unit/fakes/test_fake_git_status_ops.py`:

```python
"""Tests for FakeGitStatusOps."""

from pathlib import Path

import pytest

from erk_shared.gateway.git.status_ops.fake import FakeGitStatusOps


class TestHasStagedChanges:
    def test_returns_false_when_repo_not_in_staged_repos(self) -> None:
        ops = FakeGitStatusOps()
        assert not ops.has_staged_changes(Path("/repo"))

    def test_returns_true_when_repo_in_staged_repos(self) -> None:
        repo = Path("/repo")
        ops = FakeGitStatusOps(staged_repos={repo})
        assert ops.has_staged_changes(repo)


class TestHasUncommittedChanges:
    def test_returns_false_with_no_status(self) -> None:
        ops = FakeGitStatusOps()
        assert not ops.has_uncommitted_changes(Path("/cwd"))

    def test_returns_true_with_staged_files(self) -> None:
        cwd = Path("/cwd")
        ops = FakeGitStatusOps(file_statuses={cwd: (["file.py"], [], [])})
        assert ops.has_uncommitted_changes(cwd)

    def test_returns_true_with_modified_files(self) -> None:
        cwd = Path("/cwd")
        ops = FakeGitStatusOps(file_statuses={cwd: ([], ["file.py"], [])})
        assert ops.has_uncommitted_changes(cwd)

    def test_returns_true_with_untracked_files(self) -> None:
        cwd = Path("/cwd")
        ops = FakeGitStatusOps(file_statuses={cwd: ([], [], ["file.py"])})
        assert ops.has_uncommitted_changes(cwd)


class TestGetFileStatus:
    def test_returns_empty_lists_for_unknown_cwd(self) -> None:
        ops = FakeGitStatusOps()
        staged, modified, untracked = ops.get_file_status(Path("/cwd"))
        assert staged == []
        assert modified == []
        assert untracked == []

    def test_returns_configured_status(self) -> None:
        cwd = Path("/cwd")
        ops = FakeGitStatusOps(
            file_statuses={cwd: (["staged.py"], ["modified.py"], ["untracked.py"])}
        )
        staged, modified, untracked = ops.get_file_status(cwd)
        assert staged == ["staged.py"]
        assert modified == ["modified.py"]
        assert untracked == ["untracked.py"]


class TestCheckMergeConflicts:
    def test_returns_false_for_unknown_branches(self) -> None:
        ops = FakeGitStatusOps()
        assert not ops.check_merge_conflicts(Path("/cwd"), "main", "feature")

    def test_returns_configured_conflict_status(self) -> None:
        ops = FakeGitStatusOps(merge_conflicts={("main", "feature"): True})
        assert ops.check_merge_conflicts(Path("/cwd"), "main", "feature")


class TestGetConflictedFiles:
    def test_returns_empty_list_by_default(self) -> None:
        ops = FakeGitStatusOps()
        assert ops.get_conflicted_files(Path("/cwd")) == []

    def test_returns_configured_conflicted_files(self) -> None:
        ops = FakeGitStatusOps(conflicted_files=["file1.py", "file2.py"])
        assert ops.get_conflicted_files(Path("/cwd")) == ["file1.py", "file2.py"]


class TestLinkState:
    def test_links_to_external_state(self) -> None:
        ops = FakeGitStatusOps()
        repo = Path("/repo")
        cwd = Path("/cwd")

        # External state
        staged_repos: set[Path] = set()
        file_statuses: dict[Path, tuple[list[str], list[str], list[str]]] = {}
        merge_conflicts: dict[tuple[str, str], bool] = {}
        conflicted_files: list[str] = []

        ops.link_state(
            staged_repos=staged_repos,
            file_statuses=file_statuses,
            merge_conflicts=merge_conflicts,
            conflicted_files=conflicted_files,
        )

        # Modify external state
        staged_repos.add(repo)
        file_statuses[cwd] = (["file.py"], [], [])
        merge_conflicts[("main", "feature")] = True
        conflicted_files.append("conflict.py")

        # Verify ops sees changes
        assert ops.has_staged_changes(repo)
        assert ops.has_uncommitted_changes(cwd)
        assert ops.check_merge_conflicts(cwd, "main", "feature")
        assert ops.get_conflicted_files(cwd) == ["conflict.py"]
```

---

## Verification

1. **Type check:** `make ty` or `ty check packages/erk-shared/src/`
2. **Lint:** `make lint` or `ruff check`
3. **Unit tests:** `pytest tests/unit/fakes/test_fake_git_status_ops.py tests/unit/fakes/test_fake_git.py -v`
4. **Integration tests:** `pytest tests/integration/test_real_git.py -v`
5. **Full test suite:** `make test-unit`

---

## Files Summary

**New files (7):**

```
packages/erk-shared/src/erk_shared/gateway/git/status_ops/
├── __init__.py
├── abc.py
├── real.py
├── fake.py
├── dry_run.py
└── printing.py

tests/unit/fakes/test_fake_git_status_ops.py
```

**Modified files:**

- `packages/erk-shared/src/erk_shared/gateway/git/abc.py`
- `packages/erk-shared/src/erk_shared/gateway/git/real.py`
- `packages/erk-shared/src/erk_shared/gateway/git/fake.py`
- `packages/erk-shared/src/erk_shared/gateway/git/dry_run.py`
- `packages/erk-shared/src/erk_shared/gateway/git/printing.py`
- 18+ callsite files (listed in Step 12)
- `tests/unit/fakes/test_fake_git.py`

---

## Related Documentation

- **Skills loaded:** `dignified-python`, `fake-driven-testing`
- **Prior art:** PR #6171 (remote_ops extraction)
- **Objective:** #6169
