"""Tests for LabelCache implementations.

Tests for both FakeLabelCache (in-memory) and RealLabelCache (disk-based) implementations.
"""

import json
from pathlib import Path

from erk_shared.github.issues.label_cache import (
    FakeLabelCache,
    RealLabelCache,
)

# =============================================================================
# FakeLabelCache Tests
# =============================================================================


def test_fake_label_cache_has_returns_false_for_empty_cache() -> None:
    """Test has() returns False when cache is empty."""
    cache = FakeLabelCache()

    assert cache.has("any-label") is False


def test_fake_label_cache_add_makes_has_return_true() -> None:
    """Test add() makes has() return True for the added label."""
    cache = FakeLabelCache()

    cache.add("erk-plan")

    assert cache.has("erk-plan") is True


def test_fake_label_cache_has_returns_true_for_preconfigured_labels() -> None:
    """Test has() returns True for labels provided at construction."""
    cache = FakeLabelCache(labels={"erk-plan", "docs-extracted"})

    assert cache.has("erk-plan") is True
    assert cache.has("docs-extracted") is True
    assert cache.has("other-label") is False


def test_fake_label_cache_add_is_idempotent() -> None:
    """Test add() can be called multiple times for the same label."""
    cache = FakeLabelCache()

    cache.add("erk-plan")
    cache.add("erk-plan")
    cache.add("erk-plan")

    assert cache.has("erk-plan") is True
    # Should only have one entry
    assert cache.labels == {"erk-plan"}


def test_fake_label_cache_labels_property_returns_copy() -> None:
    """Test labels property returns a copy, not the internal set."""
    cache = FakeLabelCache(labels={"erk-plan"})

    # Modify the returned set
    labels = cache.labels
    labels.add("modified")

    # Original should be unchanged
    assert "modified" not in cache.labels


def test_fake_label_cache_path_returns_configured_path() -> None:
    """Test path() returns the configured path."""
    custom_path = Path("/custom/path/labels.json")
    cache = FakeLabelCache(cache_path=custom_path)

    assert cache.path() == custom_path


def test_fake_label_cache_path_returns_default_path() -> None:
    """Test path() returns a default path when not configured."""
    cache = FakeLabelCache()

    assert cache.path() == Path("/fake/cache/labels.json")


# =============================================================================
# RealLabelCache Tests
# =============================================================================


def test_real_label_cache_has_returns_false_for_empty_cache(tmp_path: Path) -> None:
    """Test has() returns False when cache file doesn't exist."""
    cache = RealLabelCache(tmp_path)

    assert cache.has("any-label") is False


def test_real_label_cache_add_persists_to_disk(tmp_path: Path) -> None:
    """Test add() creates cache file and persists label."""
    cache = RealLabelCache(tmp_path)

    cache.add("erk-plan")

    # Verify file was created
    cache_file = tmp_path / ".git" / "erk" / "labels.json"
    assert cache_file.exists()

    # Verify content
    content = json.loads(cache_file.read_text(encoding="utf-8"))
    assert "erk-plan" in content["labels"]
    assert "cached_at" in content["labels"]["erk-plan"]


def test_real_label_cache_has_returns_true_after_add(tmp_path: Path) -> None:
    """Test has() returns True for label after add()."""
    cache = RealLabelCache(tmp_path)

    cache.add("erk-plan")

    assert cache.has("erk-plan") is True


def test_real_label_cache_loads_existing_file(tmp_path: Path) -> None:
    """Test cache loads labels from existing file."""
    # Create cache file manually
    cache_dir = tmp_path / ".git" / "erk"
    cache_dir.mkdir(parents=True)
    cache_file = cache_dir / "labels.json"
    cache_file.write_text(
        json.dumps(
            {
                "labels": {
                    "erk-plan": {"cached_at": "2025-12-03T12:00:00+00:00"},
                    "docs-extracted": {"cached_at": "2025-12-03T12:00:00+00:00"},
                }
            }
        ),
        encoding="utf-8",
    )

    # Load cache
    cache = RealLabelCache(tmp_path)

    assert cache.has("erk-plan") is True
    assert cache.has("docs-extracted") is True
    assert cache.has("other-label") is False


def test_real_label_cache_add_is_idempotent(tmp_path: Path) -> None:
    """Test add() can be called multiple times for the same label."""
    cache = RealLabelCache(tmp_path)

    cache.add("erk-plan")
    cache.add("erk-plan")
    cache.add("erk-plan")

    # Verify only one entry
    cache_file = tmp_path / ".git" / "erk" / "labels.json"
    content = json.loads(cache_file.read_text(encoding="utf-8"))
    assert len(content["labels"]) == 1


def test_real_label_cache_preserves_existing_labels_on_add(tmp_path: Path) -> None:
    """Test add() preserves existing labels when adding new ones."""
    cache = RealLabelCache(tmp_path)

    cache.add("erk-plan")
    cache.add("docs-extracted")

    # Verify both labels exist
    cache_file = tmp_path / ".git" / "erk" / "labels.json"
    content = json.loads(cache_file.read_text(encoding="utf-8"))
    assert "erk-plan" in content["labels"]
    assert "docs-extracted" in content["labels"]


def test_real_label_cache_path_returns_correct_path(tmp_path: Path) -> None:
    """Test path() returns the expected cache file path."""
    cache = RealLabelCache(tmp_path)

    expected = tmp_path / ".git" / "erk" / "labels.json"
    assert cache.path() == expected


def test_real_label_cache_survives_new_instance(tmp_path: Path) -> None:
    """Test cache persists across new RealLabelCache instances."""
    # First instance writes
    cache1 = RealLabelCache(tmp_path)
    cache1.add("erk-plan")

    # Second instance reads
    cache2 = RealLabelCache(tmp_path)
    assert cache2.has("erk-plan") is True


def test_real_label_cache_handles_empty_labels_in_file(tmp_path: Path) -> None:
    """Test cache handles existing file with empty labels object."""
    cache_dir = tmp_path / ".git" / "erk"
    cache_dir.mkdir(parents=True)
    cache_file = cache_dir / "labels.json"
    cache_file.write_text(json.dumps({"labels": {}}), encoding="utf-8")

    cache = RealLabelCache(tmp_path)

    assert cache.has("any-label") is False


def test_real_label_cache_creates_parent_directories(tmp_path: Path) -> None:
    """Test add() creates parent directories if they don't exist."""
    # Ensure .git/erk doesn't exist
    erk_dir = tmp_path / ".git" / "erk"
    assert not erk_dir.exists()

    cache = RealLabelCache(tmp_path)
    cache.add("erk-plan")

    # Directories should be created
    assert erk_dir.exists()
    assert (erk_dir / "labels.json").exists()
