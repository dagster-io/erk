"""Tests for activation script generation."""

from pathlib import Path

from erk.cli.activation import render_activation_script


def test_render_activation_script_without_subpath() -> None:
    """Basic activation script without target_subpath."""
    script = render_activation_script(worktree_path=Path("/path/to/worktree"))
    # shlex.quote doesn't add quotes for simple paths without special characters
    assert "cd /path/to/worktree" in script
    assert "# work activate-script" in script
    assert "uv sync" in script
    assert ".venv/bin/activate" in script
    # Should NOT have subpath logic
    assert "Try to preserve relative directory position" not in script


def test_render_activation_script_with_subpath() -> None:
    """Activation script with target_subpath includes fallback logic."""
    script = render_activation_script(
        worktree_path=Path("/path/to/worktree"),
        target_subpath=Path("src/lib"),
    )
    # Should cd to worktree first
    assert "cd /path/to/worktree" in script
    # Should have subpath logic
    assert "# Try to preserve relative directory position" in script
    assert "if [ -d src/lib ]" in script
    assert "cd src/lib" in script
    # Should have fallback warning
    assert "Warning: 'src/lib' doesn't exist in target" in script
    assert ">&2" in script  # Warning goes to stderr


def test_render_activation_script_with_deeply_nested_subpath() -> None:
    """Activation script handles deeply nested paths."""
    script = render_activation_script(
        worktree_path=Path("/repo"),
        target_subpath=Path("python_modules/dagster-open-platform/src"),
    )
    assert "if [ -d python_modules/dagster-open-platform/src ]" in script
    assert "cd python_modules/dagster-open-platform/src" in script


def test_render_activation_script_subpath_none_same_as_omitted() -> None:
    """Passing target_subpath=None produces same script as omitting it."""
    script_with_none = render_activation_script(
        worktree_path=Path("/path/to/worktree"),
        target_subpath=None,
    )
    script_omitted = render_activation_script(
        worktree_path=Path("/path/to/worktree"),
    )
    assert script_with_none == script_omitted


def test_render_activation_script_custom_final_message() -> None:
    """Custom final_message is included in script."""
    script = render_activation_script(
        worktree_path=Path("/repo"),
        final_message='echo "Custom message"',
    )
    assert 'echo "Custom message"' in script


def test_render_activation_script_custom_comment() -> None:
    """Custom comment is included at top of script."""
    script = render_activation_script(
        worktree_path=Path("/repo"),
        comment="my custom comment",
    )
    assert "# my custom comment" in script


def test_render_activation_script_quotes_paths_with_spaces() -> None:
    """Paths with spaces are properly quoted."""
    script = render_activation_script(
        worktree_path=Path("/path/with spaces/worktree"),
        target_subpath=Path("sub dir/nested"),
    )
    # shlex.quote adds single quotes for paths with spaces
    assert "'/path/with spaces/worktree'" in script
    assert "'sub dir/nested'" in script
