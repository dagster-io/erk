"""Label cache for reducing GitHub API calls.

Caches known labels per-repository to avoid redundant API calls when ensuring labels exist.
Labels are permanent in GitHub, so cache invalidation is not a concern.
"""

import json
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


def _get_git_common_dir(repo_root: Path) -> Path:
    """Get the common git directory for a repository (handles worktrees).

    In a regular repository, returns repo_root/.git
    In a worktree, returns the main repository's .git directory.
    For non-git directories (e.g., tests), returns repo_root/.git as fallback.

    Args:
        repo_root: Repository or worktree root directory

    Returns:
        Path to the common .git directory (or fallback path for non-git dirs)
    """
    git_path = repo_root / ".git"

    # LBYL: Check if .git exists and what type it is
    if not git_path.exists():
        # Not a git repo (e.g., test environment) - return default path
        return git_path

    if git_path.is_dir():
        # Regular repository
        return git_path

    # Worktree: .git is a file, use git rev-parse to find common dir
    result = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


@dataclass(frozen=True)
class CachedLabel:
    """Metadata for a cached label."""

    cached_at: str  # ISO format timestamp


@dataclass(frozen=True)
class LabelCacheData:
    """Data structure for the label cache file."""

    labels: dict[str, CachedLabel]


class LabelCache(ABC):
    """Abstract interface for label caching."""

    @abstractmethod
    def has(self, label: str) -> bool:
        """Check if a label is known to exist.

        Args:
            label: Label name to check

        Returns:
            True if label is cached as existing
        """
        ...

    @abstractmethod
    def add(self, label: str) -> None:
        """Add a label to the cache (after confirming it exists).

        Args:
            label: Label name to cache
        """
        ...

    @abstractmethod
    def path(self) -> Path:
        """Get the cache file path.

        Returns:
            Path to the cache file
        """
        ...


class RealLabelCache(LabelCache):
    """Production implementation that persists to .git/erk/labels.json.

    Handles both regular repositories and worktrees by storing the cache
    in the common git directory (shared across all worktrees).

    If initialized with a non-existent path (e.g., test sentinel paths),
    operates as a no-op cache that never persists.
    """

    def __init__(self, repo_root: Path) -> None:
        """Initialize cache for a repository.

        Args:
            repo_root: Repository or worktree root directory
        """
        # LBYL: Check if repo_root exists before trying to access .git
        # This handles test sentinel paths gracefully
        if not repo_root.exists():
            self._cache_path: Path | None = None
        else:
            git_common_dir = _get_git_common_dir(repo_root)
            self._cache_path = git_common_dir / "erk" / "labels.json"
        self._data: LabelCacheData | None = None  # Lazy load

    def has(self, label: str) -> bool:
        """Check if label is in cache."""
        # No-op if cache path not set (test environment)
        if self._cache_path is None:
            return False
        self._ensure_loaded()
        if self._data is None:
            return False
        return label in self._data.labels

    def add(self, label: str) -> None:
        """Add label to cache and persist to disk."""
        # No-op if cache path not set (test environment)
        if self._cache_path is None:
            return
        self._ensure_loaded()
        if self._data is None:
            self._data = LabelCacheData(labels={})

        if label not in self._data.labels:
            # Update in-memory and persist
            new_labels = dict(self._data.labels)
            new_labels[label] = CachedLabel(cached_at=datetime.now(UTC).isoformat())
            self._data = LabelCacheData(labels=new_labels)
            self._save()

    def path(self) -> Path:
        """Get the cache file path."""
        if self._cache_path is None:
            return Path("/dev/null")  # Fallback for test environments
        return self._cache_path

    def _ensure_loaded(self) -> None:
        """Load cache from disk if not already loaded."""
        if self._data is not None:
            return
        if self._cache_path is None:
            self._data = LabelCacheData(labels={})
            return

        if not self._cache_path.exists():
            self._data = LabelCacheData(labels={})
            return

        # Load from disk
        raw = json.loads(self._cache_path.read_text(encoding="utf-8"))
        labels_dict: dict[str, CachedLabel] = {}
        for name, meta in raw.get("labels", {}).items():
            labels_dict[name] = CachedLabel(cached_at=meta.get("cached_at", ""))
        self._data = LabelCacheData(labels=labels_dict)

    def _save(self) -> None:
        """Save cache to disk."""
        if self._data is None or self._cache_path is None:
            return

        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        labels_data = {
            name: {"cached_at": meta.cached_at} for name, meta in self._data.labels.items()
        }
        data = {"labels": labels_data}
        self._cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class FakeLabelCache(LabelCache):
    """In-memory fake implementation for testing."""

    def __init__(self, labels: set[str] | None = None, cache_path: Path | None = None) -> None:
        """Initialize fake cache with optional pre-existing labels.

        Args:
            labels: Set of label names already in the cache
            cache_path: Path to report from path() method (for testing)
        """
        self._labels = labels.copy() if labels else set()
        self._cache_path = cache_path or Path("/fake/cache/labels.json")

    def has(self, label: str) -> bool:
        """Check if label is in fake cache."""
        return label in self._labels

    def add(self, label: str) -> None:
        """Add label to fake cache."""
        self._labels.add(label)

    def path(self) -> Path:
        """Get the fake cache file path."""
        return self._cache_path

    @property
    def labels(self) -> set[str]:
        """Read-only access to cached labels for test assertions."""
        return self._labels.copy()
