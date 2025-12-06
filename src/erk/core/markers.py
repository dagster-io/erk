"""Marker utilities for worktree-scoped state tracking.

Markers are simple empty files in a worktree's .erk/ directory that signal
state conditions. They persist across sessions and provide friction before
destructive operations like worktree deletion.

Example:
    # Create a pending extraction marker after landing a PR
    create_marker(worktree_path, PENDING_EXTRACTION_MARKER)

    # Check if marker exists before deletion
    if marker_exists(worktree_path, PENDING_EXTRACTION_MARKER):
        # Block deletion or require --force

    # Delete marker after extraction completes
    delete_marker(worktree_path, PENDING_EXTRACTION_MARKER)
"""

from pathlib import Path

# Marker name constants
PENDING_EXTRACTION_MARKER = "pending-extraction"


def get_marker_path(worktree_path: Path, marker_name: str) -> Path:
    """Get path to a marker file in worktree's .erk/scratch/__erk_markers/ directory.

    Args:
        worktree_path: Path to the worktree directory
        marker_name: Name of the marker (without path separators)

    Returns:
        Path to the marker file (may not exist)
    """
    return worktree_path / ".erk" / "scratch" / "__erk_markers" / marker_name


def create_marker(worktree_path: Path, marker_name: str) -> None:
    """Create a marker file in the worktree.

    Creates the .erk/ directory if it doesn't exist.

    Args:
        worktree_path: Path to the worktree directory
        marker_name: Name of the marker to create
    """
    marker_path = get_marker_path(worktree_path, marker_name)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.touch()


def marker_exists(worktree_path: Path, marker_name: str) -> bool:
    """Check if a marker exists in the worktree.

    Args:
        worktree_path: Path to the worktree directory
        marker_name: Name of the marker to check

    Returns:
        True if the marker file exists, False otherwise
    """
    marker_path = get_marker_path(worktree_path, marker_name)
    return marker_path.exists()


def delete_marker(worktree_path: Path, marker_name: str) -> None:
    """Delete a marker if it exists.

    Args:
        worktree_path: Path to the worktree directory
        marker_name: Name of the marker to delete
    """
    marker_path = get_marker_path(worktree_path, marker_name)
    if marker_path.exists():
        marker_path.unlink()
