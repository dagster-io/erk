# Phase 8: Cleanup - Config & Repo Decision

**Objective:** #6169 - Git Gateway Pure Facade Refactoring
**Phase:** 8 of 8 (final phase)
**Prerequisites:** Phases 5 (Status), 6 (Rebase), 7 (Tag) must be merged first

## Summary

Evaluate and resolve the 7 remaining methods on Git ABC after Phases 5-7 complete:

| Method                | Callsites | Category | Decision                   |
| --------------------- | --------- | -------- | -------------------------- |
| `get_repository_root` | 21+       | Repo     | **Extract to RepoOps**     |
| `get_git_common_dir`  | 4         | Repo     | **Extract to RepoOps**     |
| `count_commits_ahead` | 5         | Analysis | **Extract to AnalysisOps** |
| `get_merge_base`      | 1         | Analysis | **Extract to AnalysisOps** |
| `get_diff_to_branch`  | 1         | Analysis | **Extract to AnalysisOps** |
| `config_set`          | 1         | Config   | **Extract to ConfigOps**   |
| `get_git_user_name`   | 0         | Config   | **Extract to ConfigOps**   |

**Result:** Pure facade with 10 subgateway properties (existing 7 + new 3).

---

## Implementation Approach

Extract three new subgateways to achieve a pure facade. Each follows the established 5-layer pattern from Phases 3-5.

### Subgateway 1: RepoOps (2 methods)

Fundamental repository location queries.

```python
class GitRepoOps(ABC):
    """Repository location and validation operations."""

    @abstractmethod
    def get_repository_root(self, cwd: Path) -> Path:
        """Get the repository root directory."""
        ...

    @abstractmethod
    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory (handles worktrees)."""
        ...
```

### Subgateway 2: AnalysisOps (3 methods)

Branch comparison and diff operations.

```python
class GitAnalysisOps(ABC):
    """Branch analysis and comparison operations."""

    @abstractmethod
    def count_commits_ahead(self, cwd: Path, base_branch: str) -> int:
        """Count commits in HEAD that are not in base_branch."""
        ...

    @abstractmethod
    def get_merge_base(self, repo_root: Path, ref1: str, ref2: str) -> str | None:
        """Get the merge base commit SHA between two refs."""
        ...

    @abstractmethod
    def get_diff_to_branch(self, cwd: Path, branch: str) -> str:
        """Get diff between branch and HEAD."""
        ...
```

### Subgateway 3: ConfigOps (2 methods)

Git configuration read/write.

```python
class GitConfigOps(ABC):
    """Git configuration operations."""

    @abstractmethod
    def config_set(self, cwd: Path, key: str, value: str, *, scope: str) -> None:
        """Set a git configuration value."""
        ...

    @abstractmethod
    def get_git_user_name(self, cwd: Path) -> str | None:
        """Get the configured git user.name."""
        ...
```

---

## Detailed Implementation Steps

### Step 1: Create RepoOps Subgateway

**Directory:** `packages/erk-shared/src/erk_shared/gateway/git/repo_ops/`

#### 1.1 Create `repo_ops/__init__.py`

```python
"""Repository operations sub-gateway.

This module provides a separate gateway for repository location operations.

Import from submodules:
- abc: GitRepoOps
- real: RealGitRepoOps
- fake: FakeGitRepoOps
- dry_run: DryRunGitRepoOps
- printing: PrintingGitRepoOps
"""
```

#### 1.2 Create `repo_ops/abc.py`

```python
"""Abstract interface for git repository operations."""

from abc import ABC, abstractmethod
from pathlib import Path


class GitRepoOps(ABC):
    """Abstract interface for Git repository location operations.

    This interface contains query operations for repository structure.
    All implementations (real, fake, dry-run, printing) must implement this interface.
    """

    # ============================================================================
    # Query Operations
    # ============================================================================

    @abstractmethod
    def get_repository_root(self, cwd: Path) -> Path:
        """Get the repository root directory.

        Uses `git rev-parse --show-toplevel` to find the repository root.

        Args:
            cwd: Working directory to start search from

        Returns:
            Path to the repository root

        Raises:
            subprocess.CalledProcessError: If not in a git repository
        """
        ...

    @abstractmethod
    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory.

        Returns the path to the shared .git directory. For worktrees, this
        returns the main repository's .git directory. Returns None gracefully
        if not in a git repository (unlike get_repository_root which raises).

        Args:
            cwd: Working directory

        Returns:
            Path to the .git common directory, or None if not in a git repo
        """
        ...
```

#### 1.3 Create `repo_ops/real.py`

```python
"""Real implementation of git repository operations."""

import subprocess
from pathlib import Path

from erk_shared.gateway.git.repo_ops.abc import GitRepoOps


class RealGitRepoOps(GitRepoOps):
    """Real implementation of Git repository operations using subprocess."""

    # ============================================================================
    # Query Operations
    # ============================================================================

    def get_repository_root(self, cwd: Path) -> Path:
        """Get the repository root directory."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory."""
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        git_common_dir = result.stdout.strip()
        # Handle relative paths returned by git
        if not Path(git_common_dir).is_absolute():
            return (cwd / git_common_dir).resolve()
        return Path(git_common_dir)
```

#### 1.4 Create `repo_ops/fake.py`

```python
"""Fake implementation of git repository operations for testing."""

from pathlib import Path

from erk_shared.gateway.git.repo_ops.abc import GitRepoOps


class FakeGitRepoOps(GitRepoOps):
    """In-memory fake implementation for testing.

    Constructor Injection: pre-configured state passed via constructor.
    """

    def __init__(
        self,
        *,
        repository_roots: dict[Path, Path] | None = None,
        git_common_dirs: dict[Path, Path | None] | None = None,
    ) -> None:
        """Create FakeGitRepoOps with pre-configured state.

        Args:
            repository_roots: Mapping of cwd -> repo root
            git_common_dirs: Mapping of cwd -> git common dir (None if not in repo)
        """
        self._repository_roots = repository_roots if repository_roots is not None else {}
        self._git_common_dirs = git_common_dirs if git_common_dirs is not None else {}

    # ============================================================================
    # Query Operations
    # ============================================================================

    def get_repository_root(self, cwd: Path) -> Path:
        """Get the repository root directory."""
        if cwd in self._repository_roots:
            return self._repository_roots[cwd]
        # Walk up to find a configured root
        for path in [cwd] + list(cwd.parents):
            if path in self._repository_roots:
                return self._repository_roots[path]
        raise subprocess.CalledProcessError(128, "git rev-parse --show-toplevel")

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Get the common git directory."""
        if cwd in self._git_common_dirs:
            return self._git_common_dirs[cwd]
        # Walk up to find a configured common dir
        for path in [cwd] + list(cwd.parents):
            if path in self._git_common_dirs:
                return self._git_common_dirs[path]
        return None

    # ============================================================================
    # Test Setup (FakeGit integration)
    # ============================================================================

    def link_state(
        self,
        *,
        repository_roots: dict[Path, Path],
        git_common_dirs: dict[Path, Path | None],
    ) -> None:
        """Link this fake's state to FakeGit's state.

        Args:
            repository_roots: FakeGit's repository roots mapping
            git_common_dirs: FakeGit's git common dirs mapping
        """
        self._repository_roots = repository_roots
        self._git_common_dirs = git_common_dirs
```

**Note:** Add `import subprocess` at top for the CalledProcessError.

#### 1.5 Create `repo_ops/dry_run.py`

```python
"""Dry-run wrapper for git repository operations."""

from pathlib import Path

from erk_shared.gateway.git.repo_ops.abc import GitRepoOps


class DryRunGitRepoOps(GitRepoOps):
    """Dry-run wrapper that delegates read-only operations.

    All operations in RepoOps are read-only, so this simply delegates.
    """

    def __init__(self, wrapped: GitRepoOps) -> None:
        """Create a dry-run wrapper around a GitRepoOps implementation."""
        self._wrapped = wrapped

    # ============================================================================
    # Query Operations (delegate to wrapped implementation)
    # ============================================================================

    def get_repository_root(self, cwd: Path) -> Path:
        """Query operation (read-only, delegates to wrapped)."""
        return self._wrapped.get_repository_root(cwd)

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Query operation (read-only, delegates to wrapped)."""
        return self._wrapped.get_git_common_dir(cwd)
```

#### 1.6 Create `repo_ops/printing.py`

```python
"""Printing wrapper for git repository operations."""

from pathlib import Path

from erk_shared.gateway.git.printing_base import PrintingBase
from erk_shared.gateway.git.repo_ops.abc import GitRepoOps


class PrintingGitRepoOps(PrintingBase, GitRepoOps):
    """Wrapper that delegates without printing (all operations are read-only)."""

    # Inherits __init__, _emit, and _format_command from PrintingBase

    # ============================================================================
    # Query Operations (delegate without printing)
    # ============================================================================

    def get_repository_root(self, cwd: Path) -> Path:
        """Query operation (read-only, no printing)."""
        return self._wrapped.get_repository_root(cwd)

    def get_git_common_dir(self, cwd: Path) -> Path | None:
        """Query operation (read-only, no printing)."""
        return self._wrapped.get_git_common_dir(cwd)
```

---

### Step 2: Create AnalysisOps Subgateway

**Directory:** `packages/erk-shared/src/erk_shared/gateway/git/analysis_ops/`

#### 2.1 Create `analysis_ops/__init__.py`

```python
"""Analysis operations sub-gateway.

This module provides a separate gateway for branch analysis operations.

Import from submodules:
- abc: GitAnalysisOps
- real: RealGitAnalysisOps
- fake: FakeGitAnalysisOps
- dry_run: DryRunGitAnalysisOps
- printing: PrintingGitAnalysisOps
"""
```

#### 2.2 Create `analysis_ops/abc.py`

```python
"""Abstract interface for git analysis operations."""

from abc import ABC, abstractmethod
from pathlib import Path


class GitAnalysisOps(ABC):
    """Abstract interface for Git branch analysis operations.

    This interface contains query operations for comparing branches and commits.
    All implementations (real, fake, dry-run, printing) must implement this interface.
    """

    # ============================================================================
    # Query Operations
    # ============================================================================

    @abstractmethod
    def count_commits_ahead(self, cwd: Path, base_branch: str) -> int:
        """Count commits in HEAD that are not in base_branch.

        Uses `git rev-list --count {base_branch}..HEAD`.

        Args:
            cwd: Working directory
            base_branch: Branch to compare against

        Returns:
            Number of commits ahead, or 0 on error
        """
        ...

    @abstractmethod
    def get_merge_base(self, repo_root: Path, ref1: str, ref2: str) -> str | None:
        """Get the merge base commit SHA between two refs.

        The merge base is the best common ancestor of two commits, useful
        for determining how branches have diverged.

        Args:
            repo_root: Path to the git repository root
            ref1: First ref (branch name, commit SHA, or remote ref)
            ref2: Second ref (branch name, commit SHA, or remote ref)

        Returns:
            Commit SHA of the merge base, or None if refs have no common ancestor
        """
        ...

    @abstractmethod
    def get_diff_to_branch(self, cwd: Path, branch: str) -> str:
        """Get diff between branch and HEAD.

        Uses two-dot syntax `git diff {branch}..HEAD` to show what will
        change when merged.

        Args:
            cwd: Working directory
            branch: Branch to diff against

        Returns:
            Full diff as string
        """
        ...
```

#### 2.3 Create `analysis_ops/real.py`

```python
"""Real implementation of git analysis operations."""

import subprocess
from pathlib import Path

from erk_shared.gateway.git.analysis_ops.abc import GitAnalysisOps


class RealGitAnalysisOps(GitAnalysisOps):
    """Real implementation of Git analysis operations using subprocess."""

    # ============================================================================
    # Query Operations
    # ============================================================================

    def count_commits_ahead(self, cwd: Path, base_branch: str) -> int:
        """Count commits in HEAD that are not in base_branch."""
        result = subprocess.run(
            ["git", "rev-list", "--count", f"{base_branch}..HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return 0
        return int(result.stdout.strip())

    def get_merge_base(self, repo_root: Path, ref1: str, ref2: str) -> str | None:
        """Get the merge base commit SHA between two refs."""
        result = subprocess.run(
            ["git", "merge-base", ref1, ref2],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()

    def get_diff_to_branch(self, cwd: Path, branch: str) -> str:
        """Get diff between branch and HEAD."""
        result = subprocess.run(
            ["git", "diff", f"{branch}..HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout
```

#### 2.4 Create `analysis_ops/fake.py`

```python
"""Fake implementation of git analysis operations for testing."""

from pathlib import Path

from erk_shared.gateway.git.analysis_ops.abc import GitAnalysisOps


class FakeGitAnalysisOps(GitAnalysisOps):
    """In-memory fake implementation for testing.

    Constructor Injection: pre-configured state passed via constructor.
    """

    def __init__(
        self,
        *,
        commits_ahead: dict[tuple[Path, str], int] | None = None,
        merge_bases: dict[tuple[Path, str, str], str | None] | None = None,
        diffs: dict[tuple[Path, str], str] | None = None,
    ) -> None:
        """Create FakeGitAnalysisOps with pre-configured state.

        Args:
            commits_ahead: Mapping of (cwd, base_branch) -> commit count
            merge_bases: Mapping of (repo_root, ref1, ref2) -> merge base SHA
            diffs: Mapping of (cwd, branch) -> diff string
        """
        self._commits_ahead = commits_ahead if commits_ahead is not None else {}
        self._merge_bases = merge_bases if merge_bases is not None else {}
        self._diffs = diffs if diffs is not None else {}

    # ============================================================================
    # Query Operations
    # ============================================================================

    def count_commits_ahead(self, cwd: Path, base_branch: str) -> int:
        """Count commits in HEAD that are not in base_branch."""
        return self._commits_ahead.get((cwd, base_branch), 0)

    def get_merge_base(self, repo_root: Path, ref1: str, ref2: str) -> str | None:
        """Get the merge base commit SHA between two refs."""
        return self._merge_bases.get((repo_root, ref1, ref2))

    def get_diff_to_branch(self, cwd: Path, branch: str) -> str:
        """Get diff between branch and HEAD."""
        return self._diffs.get((cwd, branch), "")

    # ============================================================================
    # Test Setup (FakeGit integration)
    # ============================================================================

    def link_state(
        self,
        *,
        commits_ahead: dict[tuple[Path, str], int],
        merge_bases: dict[tuple[Path, str, str], str | None],
        diffs: dict[tuple[Path, str], str],
    ) -> None:
        """Link this fake's state to FakeGit's state.

        Args:
            commits_ahead: FakeGit's commits ahead mapping
            merge_bases: FakeGit's merge bases mapping
            diffs: FakeGit's diffs mapping
        """
        self._commits_ahead = commits_ahead
        self._merge_bases = merge_bases
        self._diffs = diffs
```

#### 2.5 Create `analysis_ops/dry_run.py`

```python
"""Dry-run wrapper for git analysis operations."""

from pathlib import Path

from erk_shared.gateway.git.analysis_ops.abc import GitAnalysisOps


class DryRunGitAnalysisOps(GitAnalysisOps):
    """Dry-run wrapper that delegates read-only operations.

    All operations in AnalysisOps are read-only, so this simply delegates.
    """

    def __init__(self, wrapped: GitAnalysisOps) -> None:
        """Create a dry-run wrapper around a GitAnalysisOps implementation."""
        self._wrapped = wrapped

    # ============================================================================
    # Query Operations (delegate to wrapped implementation)
    # ============================================================================

    def count_commits_ahead(self, cwd: Path, base_branch: str) -> int:
        """Query operation (read-only, delegates to wrapped)."""
        return self._wrapped.count_commits_ahead(cwd, base_branch)

    def get_merge_base(self, repo_root: Path, ref1: str, ref2: str) -> str | None:
        """Query operation (read-only, delegates to wrapped)."""
        return self._wrapped.get_merge_base(repo_root, ref1, ref2)

    def get_diff_to_branch(self, cwd: Path, branch: str) -> str:
        """Query operation (read-only, delegates to wrapped)."""
        return self._wrapped.get_diff_to_branch(cwd, branch)
```

#### 2.6 Create `analysis_ops/printing.py`

```python
"""Printing wrapper for git analysis operations."""

from pathlib import Path

from erk_shared.gateway.git.printing_base import PrintingBase
from erk_shared.gateway.git.analysis_ops.abc import GitAnalysisOps


class PrintingGitAnalysisOps(PrintingBase, GitAnalysisOps):
    """Wrapper that delegates without printing (all operations are read-only)."""

    # Inherits __init__, _emit, and _format_command from PrintingBase

    # ============================================================================
    # Query Operations (delegate without printing)
    # ============================================================================

    def count_commits_ahead(self, cwd: Path, base_branch: str) -> int:
        """Query operation (read-only, no printing)."""
        return self._wrapped.count_commits_ahead(cwd, base_branch)

    def get_merge_base(self, repo_root: Path, ref1: str, ref2: str) -> str | None:
        """Query operation (read-only, no printing)."""
        return self._wrapped.get_merge_base(repo_root, ref1, ref2)

    def get_diff_to_branch(self, cwd: Path, branch: str) -> str:
        """Query operation (read-only, no printing)."""
        return self._wrapped.get_diff_to_branch(cwd, branch)
```

---

### Step 3: Create ConfigOps Subgateway

**Directory:** `packages/erk-shared/src/erk_shared/gateway/git/config_ops/`

#### 3.1 Create `config_ops/__init__.py`

```python
"""Configuration operations sub-gateway.

This module provides a separate gateway for git configuration operations.

Import from submodules:
- abc: GitConfigOps
- real: RealGitConfigOps
- fake: FakeGitConfigOps
- dry_run: DryRunGitConfigOps
- printing: PrintingGitConfigOps
"""
```

#### 3.2 Create `config_ops/abc.py`

```python
"""Abstract interface for git configuration operations."""

from abc import ABC, abstractmethod
from pathlib import Path


class GitConfigOps(ABC):
    """Abstract interface for Git configuration operations.

    This interface contains both mutation and query operations for git config.
    All implementations (real, fake, dry-run, printing) must implement this interface.
    """

    # ============================================================================
    # Mutation Operations
    # ============================================================================

    @abstractmethod
    def config_set(self, cwd: Path, key: str, value: str, *, scope: str) -> None:
        """Set a git configuration value.

        Args:
            cwd: Working directory
            key: Configuration key (e.g., "user.name", "user.email")
            value: Configuration value
            scope: Configuration scope ("local", "global", or "system")

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...

    # ============================================================================
    # Query Operations
    # ============================================================================

    @abstractmethod
    def get_git_user_name(self, cwd: Path) -> str | None:
        """Get the configured git user.name.

        Args:
            cwd: Working directory

        Returns:
            The configured user.name, or None if not set
        """
        ...
```

#### 3.3 Create `config_ops/real.py`

```python
"""Real implementation of git configuration operations."""

import subprocess
from pathlib import Path

from erk_shared.gateway.git.config_ops.abc import GitConfigOps


class RealGitConfigOps(GitConfigOps):
    """Real implementation of Git configuration operations using subprocess."""

    # ============================================================================
    # Mutation Operations
    # ============================================================================

    def config_set(self, cwd: Path, key: str, value: str, *, scope: str) -> None:
        """Set a git configuration value."""
        subprocess.run(
            ["git", "config", f"--{scope}", key, value],
            cwd=cwd,
            check=True,
        )

    # ============================================================================
    # Query Operations
    # ============================================================================

    def get_git_user_name(self, cwd: Path) -> str | None:
        """Get the configured git user.name."""
        result = subprocess.run(
            ["git", "config", "user.name"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip()
```

#### 3.4 Create `config_ops/fake.py`

```python
"""Fake implementation of git configuration operations for testing."""

from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.git.config_ops.abc import GitConfigOps


@dataclass(frozen=True)
class ConfigSetRecord:
    """Record of a config_set operation."""

    cwd: Path
    key: str
    value: str
    scope: str


class FakeGitConfigOps(GitConfigOps):
    """In-memory fake implementation for testing.

    Constructor Injection: pre-configured state passed via constructor.
    Mutation Tracking: tracks config_set calls for test assertions.
    """

    def __init__(
        self,
        *,
        user_names: dict[Path, str | None] | None = None,
        config_values: dict[tuple[Path, str], str] | None = None,
    ) -> None:
        """Create FakeGitConfigOps with pre-configured state.

        Args:
            user_names: Mapping of cwd -> user.name value
            config_values: Mapping of (cwd, key) -> config value
        """
        self._user_names = user_names if user_names is not None else {}
        self._config_values = config_values if config_values is not None else {}

        # Mutation tracking
        self._config_sets: list[ConfigSetRecord] = []

    # ============================================================================
    # Mutation Operations
    # ============================================================================

    def config_set(self, cwd: Path, key: str, value: str, *, scope: str) -> None:
        """Set a git configuration value."""
        self._config_sets.append(ConfigSetRecord(cwd=cwd, key=key, value=value, scope=scope))
        self._config_values[(cwd, key)] = value
        # Special handling for user.name
        if key == "user.name":
            self._user_names[cwd] = value

    # ============================================================================
    # Query Operations
    # ============================================================================

    def get_git_user_name(self, cwd: Path) -> str | None:
        """Get the configured git user.name."""
        if cwd in self._user_names:
            return self._user_names[cwd]
        # Walk up to find a configured value
        for path in list(cwd.parents):
            if path in self._user_names:
                return self._user_names[path]
        return None

    # ============================================================================
    # Mutation Tracking Properties
    # ============================================================================

    @property
    def config_sets(self) -> list[ConfigSetRecord]:
        """Read-only access to config_set operations for test assertions."""
        return list(self._config_sets)

    # ============================================================================
    # Link Mutation Tracking (for integration with FakeGit)
    # ============================================================================

    def link_mutation_tracking(
        self,
        *,
        config_sets: list[ConfigSetRecord],
    ) -> None:
        """Link this fake's mutation tracking to FakeGit's tracking lists.

        Args:
            config_sets: FakeGit's _config_sets list
        """
        self._config_sets = config_sets

    def link_state(
        self,
        *,
        user_names: dict[Path, str | None],
        config_values: dict[tuple[Path, str], str],
    ) -> None:
        """Link this fake's state to FakeGit's state.

        Args:
            user_names: FakeGit's user names mapping
            config_values: FakeGit's config values mapping
        """
        self._user_names = user_names
        self._config_values = config_values
```

#### 3.5 Create `config_ops/dry_run.py`

```python
"""Dry-run wrapper for git configuration operations."""

from pathlib import Path

from erk_shared.gateway.git.config_ops.abc import GitConfigOps


class DryRunGitConfigOps(GitConfigOps):
    """No-op wrapper that prevents execution of destructive operations.

    config_set is a no-op in dry-run mode.
    Query operations delegate to the wrapped implementation.
    """

    def __init__(self, wrapped: GitConfigOps) -> None:
        """Create a dry-run wrapper around a GitConfigOps implementation."""
        self._wrapped = wrapped

    # ============================================================================
    # Mutation Operations (no-ops in dry-run mode)
    # ============================================================================

    def config_set(self, cwd: Path, key: str, value: str, *, scope: str) -> None:
        """No-op for config_set in dry-run mode."""
        pass  # Do nothing - prevents actual config change

    # ============================================================================
    # Query Operations (delegate to wrapped implementation)
    # ============================================================================

    def get_git_user_name(self, cwd: Path) -> str | None:
        """Query operation (read-only, delegates to wrapped)."""
        return self._wrapped.get_git_user_name(cwd)
```

#### 3.6 Create `config_ops/printing.py`

```python
"""Printing wrapper for git configuration operations."""

from pathlib import Path

from erk_shared.gateway.git.printing_base import PrintingBase
from erk_shared.gateway.git.config_ops.abc import GitConfigOps


class PrintingGitConfigOps(PrintingBase, GitConfigOps):
    """Wrapper that prints operations before delegating.

    Mutation operations print styled output before delegating.
    Query operations delegate without printing.
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    # ============================================================================
    # Mutation Operations (print before delegating)
    # ============================================================================

    def config_set(self, cwd: Path, key: str, value: str, *, scope: str) -> None:
        """Config set with printed output."""
        self._emit(self._format_command(f"git config --{scope} {key} {value}"))
        self._wrapped.config_set(cwd, key, value, scope=scope)

    # ============================================================================
    # Query Operations (delegate without printing)
    # ============================================================================

    def get_git_user_name(self, cwd: Path) -> str | None:
        """Query operation (read-only, no printing)."""
        return self._wrapped.get_git_user_name(cwd)
```

---

### Step 4: Update Git ABC

**File:** `packages/erk-shared/src/erk_shared/gateway/git/abc.py`

#### 4.1 Add TYPE_CHECKING imports

```python
if TYPE_CHECKING:
    from erk_shared.gateway.git.analysis_ops.abc import GitAnalysisOps
    from erk_shared.gateway.git.branch_ops.abc import GitBranchOps
    from erk_shared.gateway.git.commit_ops.abc import GitCommitOps
    from erk_shared.gateway.git.config_ops.abc import GitConfigOps
    from erk_shared.gateway.git.remote_ops.abc import GitRemoteOps
    from erk_shared.gateway.git.repo_ops.abc import GitRepoOps
    from erk_shared.gateway.git.worktree.abc import Worktree
    # Plus status_ops, rebase_ops, tag_ops from Phases 5-7
```

#### 4.2 Add subgateway property accessors

Add after existing subgateway properties:

```python
@property
@abstractmethod
def repo(self) -> GitRepoOps:
    """Access repository location operations subgateway."""
    ...

@property
@abstractmethod
def analysis(self) -> GitAnalysisOps:
    """Access branch analysis operations subgateway."""
    ...

@property
@abstractmethod
def config(self) -> GitConfigOps:
    """Access configuration operations subgateway."""
    ...
```

#### 4.3 Remove abstract methods

Delete these methods from Git ABC (they move to subgateways):

- `get_repository_root` (lines 167-170) → `git.repo.get_repository_root`
- `get_git_common_dir` (lines 125-128) → `git.repo.get_git_common_dir`
- `count_commits_ahead` (lines 162-165) → `git.analysis.count_commits_ahead`
- `get_merge_base` (lines 322-337) → `git.analysis.get_merge_base`
- `get_diff_to_branch` (lines 172-175) → `git.analysis.get_diff_to_branch`
- `config_set` (lines 222-235) → `git.config.config_set`
- `get_git_user_name` (lines 237-247) → `git.config.get_git_user_name`

---

### Step 5: Update RealGit

**File:** `packages/erk-shared/src/erk_shared/gateway/git/real.py`

#### 5.1 Add imports

```python
from erk_shared.gateway.git.analysis_ops.real import RealGitAnalysisOps
from erk_shared.gateway.git.config_ops.real import RealGitConfigOps
from erk_shared.gateway.git.repo_ops.real import RealGitRepoOps
```

#### 5.2 Initialize subgateways in `__init__`

```python
def __init__(self, time: Time | None = None) -> None:
    self._time = time if time is not None else RealTime()
    # ... existing subgateways ...
    self._repo = RealGitRepoOps()
    self._analysis = RealGitAnalysisOps()
    self._config = RealGitConfigOps()
```

#### 5.3 Add property accessors

```python
@property
def repo(self) -> GitRepoOps:
    """Access repository location operations subgateway."""
    return self._repo

@property
def analysis(self) -> GitAnalysisOps:
    """Access branch analysis operations subgateway."""
    return self._analysis

@property
def config(self) -> GitConfigOps:
    """Access configuration operations subgateway."""
    return self._config
```

#### 5.4 Remove method implementations

Delete the implementations of the 7 methods that moved to subgateways.

---

### Step 6: Update FakeGit

**File:** `packages/erk-shared/src/erk_shared/gateway/git/fake.py`

#### 6.1 Add imports

```python
from erk_shared.gateway.git.analysis_ops.fake import FakeGitAnalysisOps
from erk_shared.gateway.git.config_ops.fake import ConfigSetRecord, FakeGitConfigOps
from erk_shared.gateway.git.repo_ops.fake import FakeGitRepoOps
```

#### 6.2 Update `__init__` signature

Add new parameters for pre-configured state:

```python
def __init__(
    self,
    *,
    # ... existing params ...
    # RepoOps state
    repository_roots: dict[Path, Path] | None = None,
    git_common_dirs: dict[Path, Path | None] | None = None,
    # AnalysisOps state
    commits_ahead: dict[tuple[Path, str], int] | None = None,
    merge_bases: dict[tuple[Path, str, str], str | None] | None = None,
    diffs: dict[tuple[Path, str], str] | None = None,
    # ConfigOps state
    user_names: dict[Path, str | None] | None = None,
    config_values: dict[tuple[Path, str], str] | None = None,
) -> None:
```

#### 6.3 Initialize state and subgateways

```python
# RepoOps state
self._repository_roots = repository_roots if repository_roots is not None else {}
self._git_common_dirs = git_common_dirs if git_common_dirs is not None else {}

# AnalysisOps state
self._commits_ahead = commits_ahead if commits_ahead is not None else {}
self._merge_bases = merge_bases if merge_bases is not None else {}
self._diffs = diffs if diffs is not None else {}

# ConfigOps state and tracking
self._user_names = user_names if user_names is not None else {}
self._config_values = config_values if config_values is not None else {}
self._config_sets: list[ConfigSetRecord] = []

# Create subgateways
self._repo_gateway = FakeGitRepoOps()
self._repo_gateway.link_state(
    repository_roots=self._repository_roots,
    git_common_dirs=self._git_common_dirs,
)

self._analysis_gateway = FakeGitAnalysisOps()
self._analysis_gateway.link_state(
    commits_ahead=self._commits_ahead,
    merge_bases=self._merge_bases,
    diffs=self._diffs,
)

self._config_gateway = FakeGitConfigOps()
self._config_gateway.link_state(
    user_names=self._user_names,
    config_values=self._config_values,
)
self._config_gateway.link_mutation_tracking(
    config_sets=self._config_sets,
)
```

#### 6.4 Add property accessors

```python
@property
def repo(self) -> GitRepoOps:
    """Access repository location operations subgateway."""
    return self._repo_gateway

@property
def analysis(self) -> GitAnalysisOps:
    """Access branch analysis operations subgateway."""
    return self._analysis_gateway

@property
def config(self) -> GitConfigOps:
    """Access configuration operations subgateway."""
    return self._config_gateway

@property
def config_sets(self) -> list[ConfigSetRecord]:
    """Read-only access to config_set operations for test assertions."""
    return list(self._config_sets)
```

#### 6.5 Remove method implementations

Delete the implementations of the 7 methods that moved to subgateways.

---

### Step 7: Update DryRunGit

**File:** `packages/erk-shared/src/erk_shared/gateway/git/dry_run.py`

#### 7.1 Add imports

```python
from erk_shared.gateway.git.analysis_ops.abc import GitAnalysisOps
from erk_shared.gateway.git.analysis_ops.dry_run import DryRunGitAnalysisOps
from erk_shared.gateway.git.config_ops.abc import GitConfigOps
from erk_shared.gateway.git.config_ops.dry_run import DryRunGitConfigOps
from erk_shared.gateway.git.repo_ops.abc import GitRepoOps
from erk_shared.gateway.git.repo_ops.dry_run import DryRunGitRepoOps
```

#### 7.2 Add lazy properties

```python
@property
def repo(self) -> GitRepoOps:
    """Access repository location operations subgateway."""
    if self._repo is None:
        self._repo = DryRunGitRepoOps(self._wrapped.repo)
    return self._repo

@property
def analysis(self) -> GitAnalysisOps:
    """Access branch analysis operations subgateway."""
    if self._analysis is None:
        self._analysis = DryRunGitAnalysisOps(self._wrapped.analysis)
    return self._analysis

@property
def config(self) -> GitConfigOps:
    """Access configuration operations subgateway."""
    if self._config is None:
        self._config = DryRunGitConfigOps(self._wrapped.config)
    return self._config
```

#### 7.3 Initialize None in `__init__`

```python
self._repo: GitRepoOps | None = None
self._analysis: GitAnalysisOps | None = None
self._config: GitConfigOps | None = None
```

#### 7.4 Remove method implementations

Delete the wrapper implementations of the 7 methods.

---

### Step 8: Update PrintingGit

**File:** `packages/erk-shared/src/erk_shared/gateway/git/printing.py`

#### 8.1 Add imports

```python
from erk_shared.gateway.git.analysis_ops.abc import GitAnalysisOps
from erk_shared.gateway.git.analysis_ops.printing import PrintingGitAnalysisOps
from erk_shared.gateway.git.config_ops.abc import GitConfigOps
from erk_shared.gateway.git.config_ops.printing import PrintingGitConfigOps
from erk_shared.gateway.git.repo_ops.abc import GitRepoOps
from erk_shared.gateway.git.repo_ops.printing import PrintingGitRepoOps
```

#### 8.2 Add lazy properties

```python
@property
def repo(self) -> GitRepoOps:
    """Access repository location operations subgateway."""
    if self._repo is None:
        self._repo = PrintingGitRepoOps(self._wrapped.repo, emit=self._emit)
    return self._repo

@property
def analysis(self) -> GitAnalysisOps:
    """Access branch analysis operations subgateway."""
    if self._analysis is None:
        self._analysis = PrintingGitAnalysisOps(self._wrapped.analysis, emit=self._emit)
    return self._analysis

@property
def config(self) -> GitConfigOps:
    """Access configuration operations subgateway."""
    if self._config is None:
        self._config = PrintingGitConfigOps(self._wrapped.config, emit=self._emit)
    return self._config
```

#### 8.3 Initialize None in `__init__`

```python
self._repo: GitRepoOps | None = None
self._analysis: GitAnalysisOps | None = None
self._config: GitConfigOps | None = None
```

#### 8.4 Remove method implementations

Delete the wrapper implementations of the 7 methods.

---

### Step 9: Migrate Callsites

**Total migrations:** ~35 callsites across ~25 files

#### 9.1 RepoOps migrations (25 callsites)

Search and replace pattern:

- `git.get_repository_root(` → `git.repo.get_repository_root(`
- `git.get_git_common_dir(` → `git.repo.get_git_common_dir(`

**Files to update:**

```
src/erk/cli/cli.py
src/erk/cli/commands/pr/summarize_cmd.py
src/erk/cli/commands/pr/submit_cmd.py
src/erk/cli/commands/pr/check_cmd.py
src/erk/cli/commands/slot/common.py
src/erk/cli/commands/exec/scripts/land_execute.py
src/erk/cli/commands/stack/move_cmd.py
src/erk/core/health_checks.py
src/erk/core/repo_discovery.py
src/erk/core/command_log.py
packages/erk-shared/src/erk_shared/gateway/gt/real.py
packages/erk-shared/src/erk_shared/gateway/gt/operations/land_pr.py
packages/erk-shared/src/erk_shared/gateway/gt/operations/finalize.py
packages/erk-shared/src/erk_shared/gateway/gt/operations/pre_analysis.py
packages/erk-shared/src/erk_shared/gateway/gt/operations/preflight.py
packages/erk-shared/src/erk_shared/gateway/gt/operations/squash.py
packages/erk-shared/src/erk_shared/gateway/gt/operations/quick_submit.py
packages/erk-shared/src/erk_shared/gateway/pr/submit.py
packages/erk-shared/src/erk_shared/gateway/pr/graphite_enhance.py
packages/erk-shared/src/erk_shared/gateway/pr/diff_extraction.py
packages/erk-shared/src/erk_shared/gateway/graphite/real.py
packages/erk-statusline/src/erk_statusline/statusline.py
packages/erk-statusline/src/erk_statusline/context.py
```

#### 9.2 AnalysisOps migrations (8 callsites)

Search and replace pattern:

- `git.count_commits_ahead(` → `git.analysis.count_commits_ahead(`
- `git.get_merge_base(` → `git.analysis.get_merge_base(`
- `git.get_diff_to_branch(` → `git.analysis.get_diff_to_branch(`

**Files to update:**

```
src/erk/cli/commands/pr/summarize_cmd.py
src/erk/cli/commands/submit_helpers.py
src/erk/cli/commands/exec/scripts/generate_pr_address_summary.py
packages/erk-shared/src/erk_shared/gateway/gt/operations/pre_analysis.py
packages/erk-shared/src/erk_shared/gateway/gt/operations/squash.py
packages/erk-shared/src/erk_shared/gateway/pr/submit.py
packages/erk-shared/src/erk_shared/gateway/pr/diff_extraction.py
```

#### 9.3 ConfigOps migrations (1 callsite)

Search and replace pattern:

- `git.config_set(` → `git.config.config_set(`
- `git.get_git_user_name(` → `git.config.get_git_user_name(`

**Files to update:**

```
# config_set: check CLI command handlers
# get_git_user_name: may have no direct callsites
```

---

### Step 10: Update Tests

#### 10.1 Unit tests for new subgateways

Create tests in `tests/unit/gateways/git/`:

```
tests/unit/gateways/git/repo_ops/
├── __init__.py
└── test_fake_repo_ops.py

tests/unit/gateways/git/analysis_ops/
├── __init__.py
└── test_fake_analysis_ops.py

tests/unit/gateways/git/config_ops/
├── __init__.py
└── test_fake_config_ops.py
```

#### 10.2 Integration tests

Update existing tests in `tests/integration/test_real_git.py` to use new subgateway access patterns.

#### 10.3 Update FakeGit usage in tests

Search for tests using removed methods and update to subgateway access.

---

## Verification

### Run CI

```bash
make fast-ci  # Unit tests, lint, format, type check
make all-ci   # Full test suite including integration
```

### Manual verification checklist

1. [ ] All 7 methods removed from Git ABC
2. [ ] Git ABC has only `@property` accessors (pure facade)
3. [ ] All callsites migrated to `git.repo.*`, `git.analysis.*`, `git.config.*`
4. [ ] No regressions in existing tests
5. [ ] New subgateway tests pass
6. [ ] Type checker passes with new structure

---

## Files to Modify

### New files (18 files)

```
packages/erk-shared/src/erk_shared/gateway/git/repo_ops/__init__.py
packages/erk-shared/src/erk_shared/gateway/git/repo_ops/abc.py
packages/erk-shared/src/erk_shared/gateway/git/repo_ops/real.py
packages/erk-shared/src/erk_shared/gateway/git/repo_ops/fake.py
packages/erk-shared/src/erk_shared/gateway/git/repo_ops/dry_run.py
packages/erk-shared/src/erk_shared/gateway/git/repo_ops/printing.py

packages/erk-shared/src/erk_shared/gateway/git/analysis_ops/__init__.py
packages/erk-shared/src/erk_shared/gateway/git/analysis_ops/abc.py
packages/erk-shared/src/erk_shared/gateway/git/analysis_ops/real.py
packages/erk-shared/src/erk_shared/gateway/git/analysis_ops/fake.py
packages/erk-shared/src/erk_shared/gateway/git/analysis_ops/dry_run.py
packages/erk-shared/src/erk_shared/gateway/git/analysis_ops/printing.py

packages/erk-shared/src/erk_shared/gateway/git/config_ops/__init__.py
packages/erk-shared/src/erk_shared/gateway/git/config_ops/abc.py
packages/erk-shared/src/erk_shared/gateway/git/config_ops/real.py
packages/erk-shared/src/erk_shared/gateway/git/config_ops/fake.py
packages/erk-shared/src/erk_shared/gateway/git/config_ops/dry_run.py
packages/erk-shared/src/erk_shared/gateway/git/config_ops/printing.py
```

### Modified files (~30 files)

```
# Gateway core
packages/erk-shared/src/erk_shared/gateway/git/abc.py
packages/erk-shared/src/erk_shared/gateway/git/real.py
packages/erk-shared/src/erk_shared/gateway/git/fake.py
packages/erk-shared/src/erk_shared/gateway/git/dry_run.py
packages/erk-shared/src/erk_shared/gateway/git/printing.py

# Callsite migrations (~25 files - see Step 9)
```

---

## Related Documentation

**Skills to load:** `dignified-python`, `fake-driven-testing`

**Prior art:**

- Phase 3: #6171 (Remote Subgateway)
- Phase 4: #6180 (Commit Subgateway)
- Phase 5: #6179 (Status Subgateway)
