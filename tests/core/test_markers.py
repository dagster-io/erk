"""Tests for marker utilities."""

from pathlib import Path

from erk_shared.scratch.markers import (
    PENDING_EXTRACTION_MARKER,
    create_marker,
    delete_marker,
    get_marker_path,
    marker_exists,
)


def test_get_marker_path_returns_correct_path(tmp_path: Path) -> None:
    """Test that get_marker_path returns path in .erk/scratch/__erk_markers/ directory."""
    result = get_marker_path(tmp_path, "test-marker")

    assert result == tmp_path / ".erk" / "scratch" / "__erk_markers" / "test-marker"


def test_create_marker_creates_file_and_parent_directory(tmp_path: Path) -> None:
    """Test that create_marker creates the marker file and parent directories."""
    create_marker(tmp_path, PENDING_EXTRACTION_MARKER)

    marker_path = tmp_path / ".erk" / "scratch" / "__erk_markers" / PENDING_EXTRACTION_MARKER
    assert marker_path.exists()
    assert marker_path.is_file()


def test_create_marker_works_when_erk_directory_exists(tmp_path: Path) -> None:
    """Test that create_marker works when .erk directory already exists."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()

    create_marker(tmp_path, PENDING_EXTRACTION_MARKER)

    marker_path = erk_dir / "scratch" / "__erk_markers" / PENDING_EXTRACTION_MARKER
    assert marker_path.exists()


def test_marker_exists_returns_true_when_marker_exists(tmp_path: Path) -> None:
    """Test that marker_exists returns True when marker file exists."""
    create_marker(tmp_path, PENDING_EXTRACTION_MARKER)

    result = marker_exists(tmp_path, PENDING_EXTRACTION_MARKER)

    assert result is True


def test_marker_exists_returns_false_when_marker_missing(tmp_path: Path) -> None:
    """Test that marker_exists returns False when marker file doesn't exist."""
    result = marker_exists(tmp_path, PENDING_EXTRACTION_MARKER)

    assert result is False


def test_marker_exists_returns_false_when_erk_directory_missing(tmp_path: Path) -> None:
    """Test that marker_exists returns False when .erk directory doesn't exist."""
    result = marker_exists(tmp_path, "nonexistent-marker")

    assert result is False


def test_delete_marker_removes_existing_marker(tmp_path: Path) -> None:
    """Test that delete_marker removes an existing marker file."""
    create_marker(tmp_path, PENDING_EXTRACTION_MARKER)
    assert marker_exists(tmp_path, PENDING_EXTRACTION_MARKER)

    delete_marker(tmp_path, PENDING_EXTRACTION_MARKER)

    assert not marker_exists(tmp_path, PENDING_EXTRACTION_MARKER)


def test_delete_marker_is_noop_when_marker_missing(tmp_path: Path) -> None:
    """Test that delete_marker does nothing when marker doesn't exist."""
    # Should not raise any errors
    delete_marker(tmp_path, PENDING_EXTRACTION_MARKER)

    assert not marker_exists(tmp_path, PENDING_EXTRACTION_MARKER)


def test_delete_marker_is_noop_when_erk_directory_missing(tmp_path: Path) -> None:
    """Test that delete_marker does nothing when .erk directory doesn't exist."""
    # Should not raise any errors
    delete_marker(tmp_path, "nonexistent-marker")


def test_pending_extraction_marker_constant() -> None:
    """Test that the PENDING_EXTRACTION_MARKER constant has expected value."""
    assert PENDING_EXTRACTION_MARKER == "pending-extraction"
