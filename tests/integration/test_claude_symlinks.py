"""Integration test to verify all symlinks in .claude/ directory are valid.

This test ensures that symlinks in .claude/commands/, .claude/skills/, etc. point to
files that actually exist. This prevents broken symlinks after file renames or removals.
"""

from pathlib import Path

import pytest


def get_project_root() -> Path:
    """Get the erk project root directory."""
    return Path(__file__).parent.parent.parent


def find_broken_symlinks(directory: Path) -> list[tuple[Path, Path]]:
    """Find all broken symlinks in a directory recursively.

    Args:
        directory: Directory to search

    Returns:
        List of (symlink_path, target_path) tuples for broken symlinks
    """
    broken = []

    if not directory.exists():
        return broken

    for path in directory.rglob("*"):
        if path.is_symlink() and not path.exists():
            # Symlink exists but target doesn't
            target = path.readlink()
            broken.append((path, target))

    return broken


def test_no_broken_symlinks_in_claude_directory():
    """Verify all symlinks in .claude/ directory are valid.

    Broken symlinks can occur when:
    - Source files are renamed but symlinks aren't updated
    - Source files are deleted but symlinks remain
    - Kit reinstallation doesn't clean up old symlinks
    """
    project_root = get_project_root()
    claude_dir = project_root / ".claude"

    if not claude_dir.exists():
        pytest.skip(".claude directory not found")

    broken_symlinks = find_broken_symlinks(claude_dir)

    if broken_symlinks:
        error_lines = ["Broken symlinks found in .claude/ directory:\n"]
        for symlink, target in broken_symlinks:
            relative_symlink = symlink.relative_to(project_root)
            error_lines.append(f"  • {relative_symlink}")
            error_lines.append(f"    → {target} (target does not exist)")
            error_lines.append("")

        error_lines.append("Fix: Remove broken symlinks and recreate if needed:")
        for symlink, _target in broken_symlinks:
            relative_symlink = symlink.relative_to(project_root)
            error_lines.append(f"  rm {relative_symlink}")

        pytest.fail("\n".join(error_lines))


def test_no_broken_symlinks_in_commands():
    """Verify all symlinks in .claude/commands/ are valid.

    This is a more specific test that focuses on command symlinks,
    which are commonly created when installing kits.
    """
    project_root = get_project_root()
    commands_dir = project_root / ".claude" / "commands"

    if not commands_dir.exists():
        pytest.skip(".claude/commands directory not found")

    broken_symlinks = find_broken_symlinks(commands_dir)

    if broken_symlinks:
        error_lines = ["Broken symlinks found in .claude/commands/ directory:\n"]
        for symlink, target in broken_symlinks:
            relative_symlink = symlink.relative_to(project_root)
            error_lines.append(f"  • {relative_symlink}")
            error_lines.append(f"    → {target}")
            error_lines.append("")

        pytest.fail("\n".join(error_lines))
