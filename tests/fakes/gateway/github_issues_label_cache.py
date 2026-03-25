"""Fake label cache for testing."""

from pathlib import Path

from erk_shared.gateway.github.issues.label_cache import LabelCache


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
