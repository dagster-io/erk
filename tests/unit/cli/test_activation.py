"""Tests for activation script generation."""

from pathlib import Path

from erk.cli.activation import _render_logging_helper, render_activation_script


def test_render_activation_script_without_subpath() -> None:
    """Basic activation script without target_subpath."""
    script = render_activation_script(
        worktree_path=Path("/path/to/worktree"),
        target_subpath=None,
        post_cd_commands=None,
        final_message='echo "Activated worktree: $(pwd)"',
        comment="work activate-script",
    )
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
        post_cd_commands=None,
        final_message='echo "Activated worktree: $(pwd)"',
        comment="work activate-script",
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
        post_cd_commands=None,
        final_message='echo "Activated worktree: $(pwd)"',
        comment="work activate-script",
    )
    assert "if [ -d python_modules/dagster-open-platform/src ]" in script
    assert "cd python_modules/dagster-open-platform/src" in script


def test_render_activation_script_subpath_none_no_subpath_logic() -> None:
    """Passing target_subpath=None produces script without subpath logic."""
    script = render_activation_script(
        worktree_path=Path("/path/to/worktree"),
        target_subpath=None,
        post_cd_commands=None,
        final_message='echo "Activated worktree: $(pwd)"',
        comment="work activate-script",
    )
    # Should NOT have subpath logic
    assert "Try to preserve relative directory position" not in script


def test_render_activation_script_custom_final_message() -> None:
    """Custom final_message is included in script."""
    script = render_activation_script(
        worktree_path=Path("/repo"),
        target_subpath=None,
        post_cd_commands=None,
        final_message='echo "Custom message"',
        comment="work activate-script",
    )
    assert 'echo "Custom message"' in script


def test_render_activation_script_custom_comment() -> None:
    """Custom comment is included at top of script."""
    script = render_activation_script(
        worktree_path=Path("/repo"),
        target_subpath=None,
        post_cd_commands=None,
        final_message='echo "Activated worktree: $(pwd)"',
        comment="my custom comment",
    )
    assert "# my custom comment" in script


def test_render_activation_script_quotes_paths_with_spaces() -> None:
    """Paths with spaces are properly quoted."""
    script = render_activation_script(
        worktree_path=Path("/path/with spaces/worktree"),
        target_subpath=Path("sub dir/nested"),
        post_cd_commands=None,
        final_message='echo "Activated worktree: $(pwd)"',
        comment="work activate-script",
    )
    # shlex.quote adds single quotes for paths with spaces
    assert "'/path/with spaces/worktree'" in script
    assert "'sub dir/nested'" in script


# Transparency logging tests


def test_render_logging_helper_contains_functions() -> None:
    """Logging helper includes __erk_log and __erk_log_verbose functions."""
    helper = _render_logging_helper()
    assert "__erk_log()" in helper
    assert "__erk_log_verbose()" in helper


def test_render_logging_helper_handles_quiet_mode() -> None:
    """Logging helper respects ERK_QUIET environment variable."""
    helper = _render_logging_helper()
    assert "ERK_QUIET" in helper
    assert '[ -n "$ERK_QUIET" ] && return' in helper


def test_render_logging_helper_handles_verbose_mode() -> None:
    """Logging helper respects ERK_VERBOSE environment variable."""
    helper = _render_logging_helper()
    assert "ERK_VERBOSE" in helper
    assert '[ -z "$ERK_VERBOSE" ] && return' in helper


def test_render_logging_helper_uses_tty_detection() -> None:
    """Logging helper checks for TTY before using colors."""
    helper = _render_logging_helper()
    assert "[ -t 2 ]" in helper
    # Should use ANSI colors for TTY
    assert "\\033[0;36m" in helper


def test_render_logging_helper_outputs_to_stderr() -> None:
    """Logging helper outputs to stderr."""
    helper = _render_logging_helper()
    assert ">&2" in helper


def test_render_activation_script_contains_logging_helper() -> None:
    """Activation script includes the logging helper functions."""
    script = render_activation_script(
        worktree_path=Path("/path/to/worktree"),
        target_subpath=None,
        post_cd_commands=None,
        final_message='echo "Activated worktree: $(pwd)"',
        comment="work activate-script",
    )
    assert "__erk_log()" in script
    assert "__erk_log_verbose()" in script


def test_render_activation_script_logs_switching_message() -> None:
    """Activation script logs the cd command with full worktree path."""
    script = render_activation_script(
        worktree_path=Path("/path/to/worktree"),
        target_subpath=None,
        post_cd_commands=None,
        final_message='echo "Activated worktree: $(pwd)"',
        comment="work activate-script",
    )
    assert '__erk_log "->" "cd /path/to/worktree"' in script


def test_render_activation_script_logs_venv_activation() -> None:
    """Activation script logs venv path with Python version when activating."""
    script = render_activation_script(
        worktree_path=Path("/path/to/worktree"),
        target_subpath=None,
        post_cd_commands=None,
        final_message='echo "Activated worktree: $(pwd)"',
        comment="work activate-script",
    )
    # Should show venv path with Python version in parentheses
    assert "/path/to/worktree/.venv" in script
    assert "sys.version_info" in script  # Dynamic version extraction


def test_render_activation_script_logs_env_loading() -> None:
    """Activation script logs when loading .env file."""
    script = render_activation_script(
        worktree_path=Path("/path/to/worktree"),
        target_subpath=None,
        post_cd_commands=None,
        final_message='echo "Activated worktree: $(pwd)"',
        comment="work activate-script",
    )
    assert '__erk_log "->" "Loading .env"' in script


def test_render_activation_script_shows_full_paths_in_normal_mode() -> None:
    """Activation script shows full paths in normal (non-verbose) mode."""
    script = render_activation_script(
        worktree_path=Path("/path/to/worktree"),
        target_subpath=None,
        post_cd_commands=None,
        final_message='echo "Activated worktree: $(pwd)"',
        comment="work activate-script",
    )
    # Normal log shows cd command with full path
    assert '__erk_log "->" "cd /path/to/worktree"' in script
    # Normal log shows full path for venv with Python version
    assert "Activating venv: /path/to/worktree/.venv" in script


def test_render_activation_script_with_subpath_logs_correctly() -> None:
    """Activation script with subpath still logs full worktree path."""
    script = render_activation_script(
        worktree_path=Path("/path/to/worktree"),
        target_subpath=Path("src/lib"),
        post_cd_commands=None,
        final_message='echo "Activated worktree: $(pwd)"',
        comment="work activate-script",
    )
    # Should log cd command with full worktree path
    assert '__erk_log "->" "cd /path/to/worktree"' in script


# post_cd_commands tests


def test_render_activation_script_with_post_cd_commands() -> None:
    """Activation script includes post_cd_commands after venv activation."""
    script = render_activation_script(
        worktree_path=Path("/path/to/worktree"),
        target_subpath=None,
        post_cd_commands=[
            '__erk_log "->" "git pull origin main"',
            'git pull --ff-only origin main || echo "Warning: git pull failed" >&2',
        ],
        final_message='echo "Activated worktree: $(pwd)"',
        comment="work activate-script",
    )
    # Should include post-activation commands section
    assert "# Post-activation commands" in script
    assert '__erk_log "->" "git pull origin main"' in script
    assert "git pull --ff-only origin main" in script
    # Commands should be after .env loading and before final message
    env_index = script.index("set +a")  # End of .env loading
    pull_index = script.index("git pull")
    final_index = script.index("Activated worktree")
    assert env_index < pull_index < final_index


def test_render_activation_script_without_post_cd_commands() -> None:
    """Activation script without post_cd_commands has no post-activation section."""
    script = render_activation_script(
        worktree_path=Path("/path/to/worktree"),
        target_subpath=None,
        post_cd_commands=None,
        final_message='echo "Activated worktree: $(pwd)"',
        comment="work activate-script",
    )
    assert "# Post-activation commands" not in script


def test_render_activation_script_post_cd_commands_none_no_post_section() -> None:
    """Passing post_cd_commands=None produces script without post-activation section."""
    script = render_activation_script(
        worktree_path=Path("/path/to/worktree"),
        target_subpath=None,
        post_cd_commands=None,
        final_message='echo "Activated worktree: $(pwd)"',
        comment="work activate-script",
    )
    assert "# Post-activation commands" not in script


def test_render_activation_script_post_cd_commands_empty_list_no_section() -> None:
    """Passing empty post_cd_commands list produces no post-activation section."""
    script = render_activation_script(
        worktree_path=Path("/path/to/worktree"),
        target_subpath=None,
        post_cd_commands=[],
        final_message='echo "Activated worktree: $(pwd)"',
        comment="work activate-script",
    )
    assert "# Post-activation commands" not in script
