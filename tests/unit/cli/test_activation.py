"""Tests for activation script generation."""

import base64
from pathlib import Path

import pytest

from erk.cli.activation import (
    _render_logging_helper,
    ensure_land_script,
    ensure_worktree_activate_script,
    print_activation_instructions,
    render_activation_script,
    render_land_script,
    write_worktree_activate_script,
)


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


def test_render_activation_script_includes_shell_completions() -> None:
    """Activation script loads erk shell completions."""
    script = render_activation_script(
        worktree_path=Path("/path/to/worktree"),
        target_subpath=None,
        post_cd_commands=None,
        final_message='echo "Activated worktree: $(pwd)"',
        comment="work activate-script",
    )
    # Should check if erk command exists
    assert "command -v erk &>/dev/null" in script
    # Should evaluate erk completion with shell name extracted from $SHELL
    assert 'erk completion "${SHELL##*/}"' in script
    # Should have a comment explaining the block
    assert "# Load erk shell completions" in script


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


# write_worktree_activate_script tests


def test_write_worktree_activate_script_creates_script(tmp_path: Path) -> None:
    """write_worktree_activate_script creates .erk/bin/activate.sh with correct content."""
    script_path = write_worktree_activate_script(
        worktree_path=tmp_path,
        post_create_commands=None,
    )

    assert script_path == tmp_path / ".erk" / "bin" / "activate.sh"
    assert script_path.exists()

    content = script_path.read_text(encoding="utf-8")
    assert f"cd {tmp_path}" in content
    assert "uv sync" in content
    assert ".venv/bin/activate" in content


def test_write_worktree_activate_script_creates_erk_directory(tmp_path: Path) -> None:
    """write_worktree_activate_script creates .erk/bin/ directory if needed."""
    assert not (tmp_path / ".erk").exists()

    write_worktree_activate_script(
        worktree_path=tmp_path,
        post_create_commands=None,
    )

    assert (tmp_path / ".erk" / "bin").is_dir()


def test_write_worktree_activate_script_overwrites_existing(tmp_path: Path) -> None:
    """write_worktree_activate_script overwrites existing script."""
    bin_dir = tmp_path / ".erk" / "bin"
    bin_dir.mkdir(parents=True)
    script_path = bin_dir / "activate.sh"
    script_path.write_text("old content", encoding="utf-8")

    write_worktree_activate_script(
        worktree_path=tmp_path,
        post_create_commands=None,
    )

    content = script_path.read_text(encoding="utf-8")
    assert "old content" not in content
    assert "uv sync" in content


# ensure_worktree_activate_script tests


def test_ensure_worktree_activate_script_creates_if_missing(tmp_path: Path) -> None:
    """ensure_worktree_activate_script creates script if it doesn't exist."""
    script_path = ensure_worktree_activate_script(
        worktree_path=tmp_path,
        post_create_commands=None,
    )

    assert script_path == tmp_path / ".erk" / "bin" / "activate.sh"
    assert script_path.exists()


def test_ensure_worktree_activate_script_returns_existing(tmp_path: Path) -> None:
    """ensure_worktree_activate_script returns existing script without modifying."""
    bin_dir = tmp_path / ".erk" / "bin"
    bin_dir.mkdir(parents=True)
    script_path = bin_dir / "activate.sh"
    script_path.write_text("existing content", encoding="utf-8")

    result = ensure_worktree_activate_script(
        worktree_path=tmp_path,
        post_create_commands=None,
    )

    assert result == script_path
    assert script_path.read_text(encoding="utf-8") == "existing content"


def test_write_worktree_activate_script_with_post_create_commands(
    tmp_path: Path,
) -> None:
    """write_worktree_activate_script embeds post_create_commands in script."""
    script_path = write_worktree_activate_script(
        worktree_path=tmp_path,
        post_create_commands=["uv run make dev_install", "echo 'Setup complete'"],
    )

    content = script_path.read_text(encoding="utf-8")
    assert "# Post-activation commands" in content
    assert "uv run make dev_install" in content
    assert "echo 'Setup complete'" in content


# print_activation_instructions tests


def test_print_activation_instructions_with_source_branch_and_force(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_activation_instructions with source_branch and force=True shows delete hint."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch="feature-branch",
        force=True,
        mode="activate_only",
        copy=True,
    )

    captured = capsys.readouterr()
    assert "To activate the worktree environment:" in captured.err
    assert f"source {script_path}" in captured.err
    assert "To activate and delete branch feature-branch:" in captured.err
    assert "erk br delete feature-branch" in captured.err


def test_print_activation_instructions_with_source_branch_no_force(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_activation_instructions with source_branch but force=False shows no delete hint."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch="feature-branch",
        force=False,
        mode="activate_only",
        copy=False,
    )

    captured = capsys.readouterr()
    assert "To activate the worktree environment:" in captured.err
    assert f"source {script_path}" in captured.err
    # Should NOT contain delete hint when force=False
    assert "delete branch" not in captured.err
    assert "erk br delete" not in captured.err


def test_print_activation_instructions_without_source_branch(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_activation_instructions without source_branch shows only basic activation."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch=None,
        force=False,
        mode="activate_only",
        copy=False,
    )

    captured = capsys.readouterr()
    assert "To activate the worktree environment:" in captured.err
    assert f"source {script_path}" in captured.err
    # Should NOT contain delete hint
    assert "delete branch" not in captured.err
    assert "erk br delete" not in captured.err


def test_print_activation_instructions_emits_osc52_clipboard_sequence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_activation_instructions emits OSC 52 sequence to copy command to clipboard."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch=None,
        force=False,
        mode="activate_only",
        copy=True,
    )

    captured = capsys.readouterr()

    # Should contain OSC 52 escape sequence for clipboard
    assert "\033]52;c;" in captured.err, "Expected OSC 52 clipboard sequence"
    assert "\033\\" in captured.err, "Expected OSC 52 terminator"

    # Verify the base64-encoded content is the source command
    # OSC 52 format: ESC ] 52 ; c ; <base64> ESC \
    osc52_start = captured.err.index("\033]52;c;") + 7
    osc52_end = captured.err.index("\033\\", osc52_start)
    encoded_content = captured.err[osc52_start:osc52_end]
    decoded_content = base64.b64decode(encoded_content).decode("utf-8")
    assert decoded_content == f"source {script_path}"


def test_print_activation_instructions_shows_clipboard_hint(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_activation_instructions shows '(copied to clipboard)' hint."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch=None,
        force=False,
        mode="activate_only",
        copy=True,
    )

    captured = capsys.readouterr()
    assert "(copied to clipboard)" in captured.err


def test_print_activation_instructions_implement_mode_shows_implement_command(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_activation_instructions with mode='implement' shows implement command."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch=None,
        force=False,
        mode="implement",
        copy=True,
    )

    captured = capsys.readouterr()
    assert "To activate and start implementation:" in captured.err
    assert f"source {script_path} && erk implement" in captured.err
    # Should NOT contain --dangerous
    assert "--dangerous" not in captured.err


def test_print_activation_instructions_implement_dangerous_mode_shows_dangerous_flag(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_activation_instructions with mode='implement_dangerous' shows --dangerous flag."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch=None,
        force=False,
        mode="implement_dangerous",
        copy=True,
    )

    captured = capsys.readouterr()
    assert "To activate and start implementation (skip permissions):" in captured.err
    assert f"source {script_path} && erk implement --dangerous" in captured.err


def test_print_activation_instructions_implement_dangerous_copies_dangerous_command(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_activation_instructions with mode='implement_dangerous' copies dangerous command."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch=None,
        force=False,
        mode="implement_dangerous",
        copy=True,
    )

    captured = capsys.readouterr()

    # Extract and verify the OSC 52 clipboard content
    osc52_start = captured.err.index("\033]52;c;") + 7
    osc52_end = captured.err.index("\033\\", osc52_start)
    encoded_content = captured.err[osc52_start:osc52_end]
    decoded_content = base64.b64decode(encoded_content).decode("utf-8")
    assert decoded_content == f"source {script_path} && erk implement --dangerous"


def test_print_activation_instructions_implement_mode_copies_implement_command(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_activation_instructions with mode='implement' copies implement command to clipboard."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch=None,
        force=False,
        mode="implement",
        copy=True,
    )

    captured = capsys.readouterr()

    # Extract and verify the OSC 52 clipboard content
    osc52_start = captured.err.index("\033]52;c;") + 7
    osc52_end = captured.err.index("\033\\", osc52_start)
    encoded_content = captured.err[osc52_start:osc52_end]
    decoded_content = base64.b64decode(encoded_content).decode("utf-8")
    assert decoded_content == f"source {script_path} && erk implement"


def test_print_activation_instructions_copy_false_no_osc52(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_activation_instructions with copy=False does NOT emit OSC 52."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch=None,
        force=False,
        mode="activate_only",
        copy=False,
    )

    captured = capsys.readouterr()
    # Should NOT contain OSC 52 escape sequence
    assert "\033]52;c;" not in captured.err
    # Should NOT show clipboard hint
    assert "(copied to clipboard)" not in captured.err
    # Should still show the command
    assert f"source {script_path}" in captured.err


def test_print_activation_instructions_copy_true_emits_osc52(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_activation_instructions with copy=True emits OSC 52."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch=None,
        force=False,
        mode="activate_only",
        copy=True,
    )

    captured = capsys.readouterr()
    # Should contain OSC 52 escape sequence
    assert "\033]52;c;" in captured.err
    assert "(copied to clipboard)" in captured.err


# land.sh script tests


def test_render_land_script_content() -> None:
    """render_land_script returns correct shell script content."""
    script = render_land_script()
    assert "#!/usr/bin/env bash" in script
    # Uses process substitution with cat to avoid race conditions with temp files
    assert 'source <(cat "$(erk land --script "$@")")' in script
    assert "source this script" in script


def test_ensure_land_script_creates_if_missing(tmp_path: Path) -> None:
    """ensure_land_script creates land.sh if it doesn't exist."""
    script_path = ensure_land_script(tmp_path)

    assert script_path == tmp_path / ".erk" / "bin" / "land.sh"
    assert script_path.exists()
    content = script_path.read_text(encoding="utf-8")
    # Uses process substitution with cat to avoid race conditions with temp files
    assert 'source <(cat "$(erk land --script "$@")")' in content


def test_ensure_land_script_creates_bin_directory(tmp_path: Path) -> None:
    """ensure_land_script creates .erk/bin/ directory if needed."""
    assert not (tmp_path / ".erk").exists()

    ensure_land_script(tmp_path)

    assert (tmp_path / ".erk" / "bin").is_dir()


def test_ensure_land_script_returns_existing(tmp_path: Path) -> None:
    """ensure_land_script returns existing script without modifying."""
    bin_dir = tmp_path / ".erk" / "bin"
    bin_dir.mkdir(parents=True)
    script_path = bin_dir / "land.sh"
    script_path.write_text("existing land script", encoding="utf-8")

    result = ensure_land_script(tmp_path)

    assert result == script_path
    assert script_path.read_text(encoding="utf-8") == "existing land script"
