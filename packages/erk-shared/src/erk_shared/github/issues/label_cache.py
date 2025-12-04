"""Label cache for reducing GitHub API calls.

Caches known labels per-repository to avoid redundant API calls when ensuring labels exist.
Labels are permanent in GitHub, so cache invalidation is not a concern.
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


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
    """Production implementation that persists to .git/erk/labels.json."""

    def __init__(self, repo_root: Path) -> None:
        """Initialize cache for a repository.

        Args:
            repo_root: Repository root directory (must contain .git folder)
        """
        self._cache_path = repo_root / ".git" / "erk" / "labels.json"
        self._data: LabelCacheData | None = None  # Lazy load

    def has(self, label: str) -> bool:
        """Check if label is in cache."""
        self._ensure_loaded()
        if self._data is None:
            return False
        return label in self._data.labels

    def add(self, label: str) -> None:
        """Add label to cache and persist to disk."""
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
        return self._cache_path

    def _ensure_loaded(self) -> None:
        """Load cache from disk if not already loaded."""
        if self._data is not None:
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
        if self._data is None:
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
