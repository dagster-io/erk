# Phase 7: Tag Subgateway Extraction

Extract 3 tag-related methods from the Git ABC into a new `GitTagOps` subgateway, following the 5-layer pattern established in Phases 3-4 (remote_ops, commit_ops).

## Overview

**Objective:** Transform `git.tag_exists()`, `git.create_tag()`, `git.push_tag()` into `git.tag.tag_exists()`, `git.tag.create_tag()`, `git.tag.push_tag()`.

**Methods to extract:**
1. `tag_exists(repo_root: Path, tag_name: str) -> bool` - Query operation
2. `create_tag(repo_root: Path, tag_name: str, message: str) -> None` - Mutation operation
3. `push_tag(repo_root: Path, remote: str, tag_name: str) -> None` - Mutation operation

**Callsites to migrate (4 total):**
- `packages/erk-dev/src/erk_dev/commands/release_tag/command.py:38` - `tag_exists`
- `packages/erk-dev/src/erk_dev/commands/release_tag/command.py:43` - `create_tag`
- `packages/erk-dev/src/erk_dev/commands/release_tag/command.py:47` - `push_tag`
- `packages/erk-dev/src/erk_dev/commands/release_info/command.py:26` - `tag_exists`

## Files to Create

### 1. `packages/erk-shared/src/erk_shared/gateway/git/tag_ops/__init__.py`

```python
"""Git tag operations sub-gateway.

This module provides a separate gateway for tag operations,
including checking tag existence, creating tags, and pushing tags.

Import from submodules:
- abc: GitTagOps
- real: RealGitTagOps
- fake: FakeGitTagOps
- dry_run: DryRunGitTagOps
- printing: PrintingGitTagOps
"""
```

### 2. `packages/erk-shared/src/erk_shared/gateway/git/tag_ops/abc.py`

```python
"""Abstract base class for Git tag operations.

This sub-gateway extracts tag operations from the main Git gateway,
including tag existence checks, creation, and pushing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class GitTagOps(ABC):
    """Abstract interface for Git tag operations.

    This interface contains both query and mutation operations for tags.
    All implementations (real, fake, dry-run, printing) must implement this interface.
    """

    # ============================================================================
    # Query Operations
    # ============================================================================

    @abstractmethod
    def tag_exists(self, repo_root: Path, tag_name: str) -> bool:
        """Check if a git tag exists.

        Args:
            repo_root: Path to the repository root
            tag_name: Tag name to check (e.g., 'v1.0.0')

        Returns:
            True if the tag exists, False otherwise
        """
        ...

    # ============================================================================
    # Mutation Operations
    # ============================================================================

    @abstractmethod
    def create_tag(self, repo_root: Path, tag_name: str, message: str) -> None:
        """Create an annotated git tag.

        Args:
            repo_root: Path to the repository root
            tag_name: Tag name to create (e.g., 'v1.0.0')
            message: Tag message

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...

    @abstractmethod
    def push_tag(self, repo_root: Path, remote: str, tag_name: str) -> None:
        """Push a tag to a remote.

        Args:
            repo_root: Path to the repository root
            remote: Remote name (e.g., 'origin')
            tag_name: Tag name to push

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        ...
```

### 3. `packages/erk-shared/src/erk_shared/gateway/git/tag_ops/real.py`

```python
"""Production Git tag operations using subprocess."""

import subprocess
from pathlib import Path

from erk_shared.gateway.git.tag_ops.abc import GitTagOps
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealGitTagOps(GitTagOps):
    """Production implementation of Git tag operations using subprocess."""

    # ============================================================================
    # Query Operations
    # ============================================================================

    def tag_exists(self, repo_root: Path, tag_name: str) -> bool:
        """Check if a git tag exists."""
        result = subprocess.run(
            ["git", "tag", "-l", tag_name],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        return tag_name in result.stdout.strip().split("\n")

    # ============================================================================
    # Mutation Operations
    # ============================================================================

    def create_tag(self, repo_root: Path, tag_name: str, message: str) -> None:
        """Create an annotated git tag."""
        run_subprocess_with_context(
            cmd=["git", "tag", "-a", tag_name, "-m", message],
            operation_context=f"create tag '{tag_name}'",
            cwd=repo_root,
        )

    def push_tag(self, repo_root: Path, remote: str, tag_name: str) -> None:
        """Push a tag to a remote."""
        run_subprocess_with_context(
            cmd=["git", "push", remote, tag_name],
            operation_context=f"push tag '{tag_name}' to remote '{remote}'",
            cwd=repo_root,
        )
```

### 4. `packages/erk-shared/src/erk_shared/gateway/git/tag_ops/fake.py`

```python
"""Fake implementation of Git tag operations for testing."""

from __future__ import annotations

from pathlib import Path

from erk_shared.gateway.git.tag_ops.abc import GitTagOps


class FakeGitTagOps(GitTagOps):
    """In-memory fake implementation of Git tag operations.

    This fake accepts pre-configured state in its constructor and tracks
    mutations for test assertions.

    Constructor Injection:
    ---------------------
    - existing_tags: Set of tag names that exist in the repository

    Mutation Tracking:
    -----------------
    This fake tracks mutations for test assertions via read-only properties:
    - created_tags: List of (tag_name, message) tuples from create_tag()
    - pushed_tags: List of (remote, tag_name) tuples from push_tag()
    """

    def __init__(
        self,
        *,
        existing_tags: set[str] | None = None,
    ) -> None:
        """Create FakeGitTagOps with pre-configured state.

        Args:
            existing_tags: Set of tag names that exist in the repository
        """
        self._existing_tags: set[str] = existing_tags if existing_tags is not None else set()

        # Mutation tracking
        self._created_tags: list[tuple[str, str]] = []  # (tag_name, message)
        self._pushed_tags: list[tuple[str, str]] = []  # (remote, tag_name)

    # ============================================================================
    # Query Operations
    # ============================================================================

    def tag_exists(self, repo_root: Path, tag_name: str) -> bool:
        """Check if a git tag exists in the fake state."""
        return tag_name in self._existing_tags

    # ============================================================================
    # Mutation Operations
    # ============================================================================

    def create_tag(self, repo_root: Path, tag_name: str, message: str) -> None:
        """Create an annotated git tag (mutates internal state)."""
        self._existing_tags.add(tag_name)
        self._created_tags.append((tag_name, message))

    def push_tag(self, repo_root: Path, remote: str, tag_name: str) -> None:
        """Push a tag to a remote (tracks mutation)."""
        self._pushed_tags.append((remote, tag_name))

    # ============================================================================
    # Mutation Tracking Properties
    # ============================================================================

    @property
    def created_tags(self) -> list[tuple[str, str]]:
        """Get list of tags created during test.

        Returns list of (tag_name, message) tuples.
        This property is for test assertions only.
        """
        return self._created_tags.copy()

    @property
    def pushed_tags(self) -> list[tuple[str, str]]:
        """Get list of tags pushed during test.

        Returns list of (remote, tag_name) tuples.
        This property is for test assertions only.
        """
        return self._pushed_tags.copy()

    # ============================================================================
    # Link Mutation Tracking (for integration with FakeGit)
    # ============================================================================

    def link_mutation_tracking(
        self,
        *,
        existing_tags: set[str],
        created_tags: list[tuple[str, str]],
        pushed_tags: list[tuple[str, str]],
    ) -> None:
        """Link this fake's mutation tracking to FakeGit's tracking lists.

        This allows FakeGit to expose tag operations mutations through its
        own properties while delegating to this subgateway.

        Args:
            existing_tags: FakeGit's _existing_tags set
            created_tags: FakeGit's _created_tags list
            pushed_tags: FakeGit's _pushed_tags list
        """
        self._existing_tags = existing_tags
        self._created_tags = created_tags
        self._pushed_tags = pushed_tags
```

### 5. `packages/erk-shared/src/erk_shared/gateway/git/tag_ops/dry_run.py`

```python
"""No-op Git tag operations wrapper for dry-run mode.

This module provides a wrapper that prevents execution of destructive
tag operations while delegating read-only operations to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.gateway.git.tag_ops.abc import GitTagOps
from erk_shared.output.output import user_output


class DryRunGitTagOps(GitTagOps):
    """No-op wrapper that prevents execution of destructive tag operations.

    This wrapper intercepts destructive git operations (create_tag, push_tag) and
    prints what would happen. Read-only operations (tag_exists) are
    delegated to the wrapped implementation.

    Usage:
        real_ops = RealGitTagOps()
        noop_ops = DryRunGitTagOps(real_ops)

        # Query operations work normally
        exists = noop_ops.tag_exists(repo_root, "v1.0.0")

        # Mutation operations print dry-run message
        noop_ops.create_tag(repo_root, "v1.0.0", "Release")
    """

    def __init__(self, wrapped: GitTagOps) -> None:
        """Create a dry-run wrapper around a GitTagOps implementation.

        Args:
            wrapped: The GitTagOps implementation to wrap (usually RealGitTagOps)
        """
        self._wrapped = wrapped

    # ============================================================================
    # Query Operations (delegate to wrapped implementation)
    # ============================================================================

    def tag_exists(self, repo_root: Path, tag_name: str) -> bool:
        """Check if tag exists (read-only, delegates to wrapped)."""
        return self._wrapped.tag_exists(repo_root, tag_name)

    # ============================================================================
    # Mutation Operations (print dry-run message)
    # ============================================================================

    def create_tag(self, repo_root: Path, tag_name: str, message: str) -> None:
        """Print dry-run message instead of creating tag."""
        user_output(f"[DRY RUN] Would run: git tag -a {tag_name} -m '{message}'")

    def push_tag(self, repo_root: Path, remote: str, tag_name: str) -> None:
        """Print dry-run message instead of pushing tag."""
        user_output(f"[DRY RUN] Would run: git push {remote} {tag_name}")
```

### 6. `packages/erk-shared/src/erk_shared/gateway/git/tag_ops/printing.py`

```python
"""Printing Git tag operations wrapper for verbose output.

This module provides a wrapper that prints styled output for tag operations
before delegating to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.gateway.git.tag_ops.abc import GitTagOps
from erk_shared.printing.base import PrintingBase


class PrintingGitTagOps(PrintingBase, GitTagOps):
    """Wrapper that prints tag operations before delegating to inner implementation.

    This wrapper prints styled output for operations, then delegates to the
    wrapped implementation (which could be Real or DryRun).

    Usage:
        # For production
        printing_ops = PrintingGitTagOps(real_ops, script_mode=False, dry_run=False)

        # For dry-run
        noop_inner = DryRunGitTagOps(real_ops)
        printing_ops = PrintingGitTagOps(noop_inner, script_mode=False, dry_run=True)
    """

    # Inherits __init__, _emit, and _format_command from PrintingBase

    # ============================================================================
    # Query Operations (delegate without printing)
    # ============================================================================

    def tag_exists(self, repo_root: Path, tag_name: str) -> bool:
        """Check if tag exists (read-only, no printing)."""
        return self._wrapped.tag_exists(repo_root, tag_name)

    # ============================================================================
    # Mutation Operations (print before delegating)
    # ============================================================================

    def create_tag(self, repo_root: Path, tag_name: str, message: str) -> None:
        """Create tag with printed output."""
        self._emit(self._format_command(f"git tag -a {tag_name} -m '{message}'"))
        self._wrapped.create_tag(repo_root, tag_name, message)

    def push_tag(self, repo_root: Path, remote: str, tag_name: str) -> None:
        """Push tag with printed output."""
        self._emit(self._format_command(f"git push {remote} {tag_name}"))
        self._wrapped.push_tag(repo_root, remote, tag_name)
```

## Files to Modify

### 1. `packages/erk-shared/src/erk_shared/gateway/git/abc.py`

**Add import in TYPE_CHECKING block (line ~23):**
```python
from erk_shared.gateway.git.tag_ops.abc import GitTagOps
```

**Add property after commit property (around line 124):**
```python
@property
@abstractmethod
def tag(self) -> GitTagOps:
    """Access tag operations subgateway."""
    ...
```

**Remove 3 abstract methods (lines 249-288):**
- `tag_exists` (lines 249-260)
- `create_tag` (lines 262-274)
- `push_tag` (lines 276-288)

### 2. `packages/erk-shared/src/erk_shared/gateway/git/real.py`

**Add imports (after line 18):**
```python
from erk_shared.gateway.git.tag_ops.abc import GitTagOps
from erk_shared.gateway.git.tag_ops.real import RealGitTagOps
```

**Add to `__init__` (after line 42):**
```python
self._tag = RealGitTagOps()
```

**Add property (after commit property, around line 63):**
```python
@property
def tag(self) -> GitTagOps:
    """Access tag operations subgateway."""
    return self._tag
```

**Remove 3 method implementations (lines 258-283):**
- `tag_exists` (lines 258-267)
- `create_tag` (lines 269-275)
- `push_tag` (lines 277-283)

### 3. `packages/erk-shared/src/erk_shared/gateway/git/fake.py`

**Add imports (after line 22):**
```python
from erk_shared.gateway.git.tag_ops.abc import GitTagOps
from erk_shared.gateway.git.tag_ops.fake import FakeGitTagOps
```

**In `__init__`, after commit gateway creation (around line 339), add:**
```python
# Tag operations subgateway - linked to FakeGit's state
self._tag_gateway = FakeGitTagOps(
    existing_tags=self._existing_tags,
)
# Link mutation tracking so FakeGit properties see mutations from FakeGitTagOps
self._tag_gateway.link_mutation_tracking(
    existing_tags=self._existing_tags,
    created_tags=self._created_tags,
    pushed_tags=self._pushed_tags,
)
```

**Add property (after commit property, around line 360):**
```python
@property
def tag(self) -> GitTagOps:
    """Access tag operations subgateway."""
    return self._tag_gateway
```

**Remove 3 method implementations (lines 613-642):**
- `tag_exists` (lines 613-615)
- `create_tag` (lines 617-620)
- `push_tag` (lines 622-624)

**Keep the properties `created_tags` and `pushed_tags` (lines 626-642)** - these are for backward compatibility in tests that assert on FakeGit directly.

### 4. `packages/erk-shared/src/erk_shared/gateway/git/dry_run.py`

**Add imports (after line 14):**
```python
from erk_shared.gateway.git.tag_ops.abc import GitTagOps
from erk_shared.gateway.git.tag_ops.dry_run import DryRunGitTagOps
```

**Add property (after commit property, around line 70):**
```python
@property
def tag(self) -> GitTagOps:
    """Access tag operations subgateway (wrapped with DryRunGitTagOps)."""
    return DryRunGitTagOps(self._wrapped.tag)
```

**Remove 3 method implementations (lines 126-136):**
- `tag_exists` (lines 126-128)
- `create_tag` (lines 130-132)
- `push_tag` (lines 134-136)

### 5. `packages/erk-shared/src/erk_shared/gateway/git/printing.py`

**Add imports (after line 17):**
```python
from erk_shared.gateway.git.tag_ops.abc import GitTagOps
from erk_shared.gateway.git.tag_ops.printing import PrintingGitTagOps
```

**Add property (after commit property, around line 69):**
```python
@property
def tag(self) -> GitTagOps:
    """Access tag operations subgateway (wrapped with PrintingGitTagOps)."""
    return PrintingGitTagOps(
        self._wrapped.tag, script_mode=self._script_mode, dry_run=self._dry_run
    )
```

**Remove 3 method implementations (lines 182-194):**
- `tag_exists` (lines 182-184)
- `create_tag` (lines 186-189)
- `push_tag` (lines 191-194)

### 6. Migrate Callsites

#### `packages/erk-dev/src/erk_dev/commands/release_tag/command.py`

**Line 38:** Change `git.tag_exists(` to `git.tag.tag_exists(`
**Line 43:** Change `git.create_tag(` to `git.tag.create_tag(`
**Line 47:** Change `git.push_tag(` to `git.tag.push_tag(`

#### `packages/erk-dev/src/erk_dev/commands/release_info/command.py`

**Line 26:** Change `git.tag_exists(` to `git.tag.tag_exists(`

## Verification

1. **Run type checker:**
   ```bash
   make ty
   ```

2. **Run linter and formatter:**
   ```bash
   make lint && make format
   ```

3. **Run unit tests:**
   ```bash
   pytest tests/unit/fakes/test_fake_git.py -v
   pytest packages/erk-dev/tests/test_release_tag.py -v
   ```

4. **Run full test suite:**
   ```bash
   make test
   ```

5. **Verify tag subgateway accessible:**
   ```python
   from erk_shared.gateway.git.real import RealGit
   git = RealGit()
   # Should work via subgateway
   git.tag.tag_exists(Path("."), "v1.0.0")
   ```

## Related Documentation

- **Skills to load:** `dignified-python`, `fake-driven-testing`
- **Prior art:** Phase 4 PR #6180 (commit_ops extraction)