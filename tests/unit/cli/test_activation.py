"""Tests for activation script generation."""

import base64
from pathlib import Path

import pytest

from erk.cli.activation import (
    ActivationConfig,
    _render_logging_helper,
    activation_config_activate_only,
    activation_config_for_implement,
    build_activation_command,
    ensure_land_script,
    ensure_worktree_activate_script,
    print_activation_instructions,
    print_temp_script_instructions,
    render_activation_script,
    render_land_script,
    write_worktree_activate_script,
)

# ActivationConfig tests


def test_activation_config_frozen() -> None:
    """ActivationConfig is frozen and cannot be mutated."""
    config = ActivationConfig(implement=True, dangerous=False, docker=False, codespace=None)
    with pytest.raises(AttributeError):
        config.implement = False  # type: ignore[misc]


def test_activation_config_activate_only() -> None:
    """activation_config_activate_only creates config with implement=False."""
    config = activation_config_activate_only()
    assert config.implement is False
    assert config.dangerous is False
    assert config.docker is False
    assert config.codespace is None


def test_activation_config_for_implement_no_flags() -> None:
    """activation_config_for_implement with no flags creates basic implement config."""
    config = activation_config_for_implement(dangerous=False, docker=False, codespace=None)
    assert config.implement is True
    assert config.dangerous is False
    assert config.docker is False
    assert config.codespace is None


def test_activation_config_for_implement_dangerous() -> None:
    """activation_config_for_implement with dangerous=True sets dangerous flag."""
    config = activation_config_for_implement(dangerous=True, docker=False, codespace=None)
    assert config.implement is True
    assert config.dangerous is True
    assert config.docker is False
    assert config.codespace is None


def test_activation_config_for_implement_docker() -> None:
    """activation_config_for_implement with docker=True sets docker flag."""
    config = activation_config_for_implement(dangerous=False, docker=True, codespace=None)
    assert config.implement is True
    assert config.dangerous is False
    assert config.docker is True
    assert config.codespace is None


def test_activation_config_for_implement_both_flags() -> None:
    """activation_config_for_implement with both flags sets both."""
    config = activation_config_for_implement(dangerous=True, docker=True, codespace=None)
    assert config.implement is True
    assert config.dangerous is True
    assert config.docker is True
    assert config.codespace is None


def test_activation_config_for_implement_codespace_default() -> None:
    """activation_config_for_implement with codespace='' sets default codespace."""
    config = activation_config_for_implement(dangerous=False, docker=False, codespace="")
    assert config.implement is True
    assert config.dangerous is False
    assert config.docker is False
    assert config.codespace == ""


def test_activation_config_for_implement_codespace_named() -> None:
    """activation_config_for_implement with codespace='mybox' sets named codespace."""
    config = activation_config_for_implement(dangerous=False, docker=False, codespace="mybox")
    assert config.implement is True
    assert config.dangerous is False
    assert config.docker is False
    assert config.codespace == "mybox"


# build_activation_command tests


def test_build_activation_command_activate_only() -> None:
    """build_activation_command with activate_only config returns just source command."""
    config = activation_config_activate_only()
    result = build_activation_command(config, Path("/path/to/script.sh"))
    assert result == "source /path/to/script.sh"


def test_build_activation_command_implement() -> None:
    """build_activation_command with implement config includes erk implement."""
    config = activation_config_for_implement(dangerous=False, docker=False, codespace=None)
    result = build_activation_command(config, Path("/path/to/script.sh"))
    assert result == "source /path/to/script.sh && erk implement"


def test_build_activation_command_implement_dangerous() -> None:
    """build_activation_command with dangerous flag includes --dangerous."""
    config = activation_config_for_implement(dangerous=True, docker=False, codespace=None)
    result = build_activation_command(config, Path("/path/to/script.sh"))
    assert result == "source /path/to/script.sh && erk implement --dangerous"


def test_build_activation_command_implement_docker() -> None:
    """build_activation_command with docker flag includes --docker."""
    config = activation_config_for_implement(dangerous=False, docker=True, codespace=None)
    result = build_activation_command(config, Path("/path/to/script.sh"))
    assert result == "source /path/to/script.sh && erk implement --docker"


def test_build_activation_command_implement_docker_dangerous() -> None:
    """build_activation_command with both flags includes both in correct order."""
    config = activation_config_for_implement(dangerous=True, docker=True, codespace=None)
    result = build_activation_command(config, Path("/path/to/script.sh"))
    # docker comes before dangerous due to append order
    assert result == "source /path/to/script.sh && erk implement --docker --dangerous"


def test_build_activation_command_implement_codespace_default() -> None:
    """build_activation_command with codespace='' includes --codespace flag."""
    config = activation_config_for_implement(dangerous=False, docker=False, codespace="")
    result = build_activation_command(config, Path("/path/to/script.sh"))
    assert result == "source /path/to/script.sh && erk implement --codespace"


def test_build_activation_command_implement_codespace_named() -> None:
    """build_activation_command with named codespace includes --codespace name."""
    config = activation_config_for_implement(dangerous=False, docker=False, codespace="mybox")
    result = build_activation_command(config, Path("/path/to/script.sh"))
    assert result == "source /path/to/script.sh && erk implement --codespace mybox"


def test_build_activation_command_implement_codespace_dangerous() -> None:
    """build_activation_command with codespace and dangerous flags includes both."""
    config = activation_config_for_implement(dangerous=True, docker=False, codespace="mybox")
    result = build_activation_command(config, Path("/path/to/script.sh"))
    # codespace comes before dangerous due to append order
    assert result == "source /path/to/script.sh && erk implement --codespace mybox --dangerous"


# render_activation_script tests


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


def test_render_activation_script_contains_completion_setup() -> None:
    """Activation script sets up shell completion for bash and zsh."""
    script = render_activation_script(
        worktree_path=Path("/path/to/worktree"),
        target_subpath=None,
        post_cd_commands=None,
        final_message='echo "Activated worktree: $(pwd)"',
        comment="work activate-script",
    )
    # Should contain shell completion section
    assert "# Shell completion" in script
    # Should detect bash and eval completion
    assert 'if [ -n "$BASH_VERSION" ]' in script
    assert 'eval "$(erk completion bash)"' in script
    # Should detect zsh and eval completion
    assert 'elif [ -n "$ZSH_VERSION" ]' in script
    assert 'eval "$(erk completion zsh)"' in script


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
    """print_activation_instructions with source_branch and force=True shows only delete command."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch="feature-branch",
        force=True,
        config=activation_config_activate_only(),
        copy=True,
    )

    captured = capsys.readouterr()
    # Should show only the delete instruction (not the basic activation message)
    assert "To activate and delete branch feature-branch:" in captured.err
    assert f"source {script_path} && erk br delete feature-branch" in captured.err
    # Should NOT show the separate activation message
    assert "To activate the worktree environment:" not in captured.err


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
        config=activation_config_activate_only(),
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
        config=activation_config_activate_only(),
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
        config=activation_config_activate_only(),
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
        config=activation_config_activate_only(),
        copy=True,
    )

    captured = capsys.readouterr()
    assert "(copied to clipboard)" in captured.err


def test_print_activation_instructions_implement_config_shows_implement_command(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_activation_instructions with implement config shows implement command."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch=None,
        force=False,
        config=activation_config_for_implement(dangerous=False, docker=False, codespace=None),
        copy=True,
    )

    captured = capsys.readouterr()
    assert "To activate and start implementation:" in captured.err
    assert f"source {script_path} && erk implement" in captured.err
    # Should NOT contain --dangerous
    assert "--dangerous" not in captured.err


def test_print_activation_instructions_implement_dangerous_config_shows_dangerous_flag(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_activation_instructions with dangerous config shows --dangerous flag."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch=None,
        force=False,
        config=activation_config_for_implement(dangerous=True, docker=False, codespace=None),
        copy=True,
    )

    captured = capsys.readouterr()
    assert "To activate and start implementation (skip permissions):" in captured.err
    assert f"source {script_path} && erk implement --dangerous" in captured.err


def test_print_activation_instructions_implement_dangerous_copies_dangerous_command(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_activation_instructions with dangerous config copies dangerous command."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch=None,
        force=False,
        config=activation_config_for_implement(dangerous=True, docker=False, codespace=None),
        copy=True,
    )

    captured = capsys.readouterr()

    # Extract and verify the OSC 52 clipboard content
    osc52_start = captured.err.index("\033]52;c;") + 7
    osc52_end = captured.err.index("\033\\", osc52_start)
    encoded_content = captured.err[osc52_start:osc52_end]
    decoded_content = base64.b64decode(encoded_content).decode("utf-8")
    assert decoded_content == f"source {script_path} && erk implement --dangerous"


def test_print_activation_instructions_implement_config_copies_implement_command(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_activation_instructions with implement config copies implement command to clipboard."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch=None,
        force=False,
        config=activation_config_for_implement(dangerous=False, docker=False, codespace=None),
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
        config=activation_config_activate_only(),
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
        config=activation_config_activate_only(),
        copy=True,
    )

    captured = capsys.readouterr()
    # Should contain OSC 52 escape sequence
    assert "\033]52;c;" in captured.err
    assert "(copied to clipboard)" in captured.err


def test_print_activation_instructions_docker_config_shows_docker_flag(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_activation_instructions with docker config shows --docker flag."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch=None,
        force=False,
        config=activation_config_for_implement(dangerous=False, docker=True, codespace=None),
        copy=True,
    )

    captured = capsys.readouterr()
    assert "To activate and start implementation (Docker isolation):" in captured.err
    assert f"source {script_path} && erk implement --docker" in captured.err


def test_print_activation_instructions_docker_dangerous_config_shows_both_flags(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_activation_instructions with docker+dangerous config shows both flags."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch=None,
        force=False,
        config=activation_config_for_implement(dangerous=True, docker=True, codespace=None),
        copy=True,
    )

    captured = capsys.readouterr()
    assert "To activate and start implementation (Docker isolation):" in captured.err
    # docker comes before dangerous
    assert f"source {script_path} && erk implement --docker --dangerous" in captured.err


def test_print_activation_instructions_codespace_config_shows_codespace_flag(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_activation_instructions with codespace config shows --codespace flag."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch=None,
        force=False,
        config=activation_config_for_implement(dangerous=False, docker=False, codespace=""),
        copy=True,
    )

    captured = capsys.readouterr()
    assert "To activate and start implementation (codespace isolation):" in captured.err
    assert f"source {script_path} && erk implement --codespace" in captured.err


def test_print_activation_instructions_codespace_named_shows_name(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_activation_instructions with named codespace shows --codespace name."""
    script_path = tmp_path / ".erk" / "bin" / "activate.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_activation_instructions(
        script_path,
        source_branch=None,
        force=False,
        config=activation_config_for_implement(dangerous=False, docker=False, codespace="mybox"),
        copy=True,
    )

    captured = capsys.readouterr()
    assert "To activate and start implementation (codespace isolation):" in captured.err
    assert f"source {script_path} && erk implement --codespace mybox" in captured.err


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


# print_temp_script_instructions tests


def test_print_temp_script_instructions_without_args(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_temp_script_instructions with args=None shows plain source command."""
    script_path = tmp_path / ".erk" / "bin" / "land.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_temp_script_instructions(
        script_path,
        instruction="To land the PR:",
        copy=False,
        args=None,
        extra_flags=None,
    )

    captured = capsys.readouterr()
    assert "To land the PR:" in captured.err
    assert f"source {script_path}" in captured.err
    # Should NOT have any extra arguments
    assert str(script_path) in captured.err


def test_print_temp_script_instructions_with_args(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_temp_script_instructions with args includes quoted arguments."""
    script_path = tmp_path / ".erk" / "bin" / "land.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_temp_script_instructions(
        script_path,
        instruction="To land the PR:",
        copy=False,
        args=[123, "feature-branch"],
        extra_flags=None,
    )

    captured = capsys.readouterr()
    assert "To land the PR:" in captured.err
    # Should include arguments in the source command
    assert f"source {script_path} 123 feature-branch" in captured.err


def test_print_temp_script_instructions_with_args_quotes_special_chars(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_temp_script_instructions properly quotes arguments with special characters."""
    script_path = tmp_path / ".erk" / "bin" / "land.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_temp_script_instructions(
        script_path,
        instruction="To land the PR:",
        copy=False,
        args=[456, "branch with spaces"],
        extra_flags=None,
    )

    captured = capsys.readouterr()
    # shlex.quote wraps strings with spaces in quotes
    assert "456" in captured.err
    assert "'branch with spaces'" in captured.err


def test_print_temp_script_instructions_with_args_copies_full_command(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_temp_script_instructions with copy=True and args copies full command."""
    script_path = tmp_path / ".erk" / "bin" / "land.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_temp_script_instructions(
        script_path,
        instruction="To land the PR:",
        copy=True,
        args=[789, "my-branch"],
        extra_flags=None,
    )

    captured = capsys.readouterr()

    # Should contain OSC 52 escape sequence for clipboard
    assert "\033]52;c;" in captured.err, "Expected OSC 52 clipboard sequence"
    assert "\033\\" in captured.err, "Expected OSC 52 terminator"

    # Verify the base64-encoded content includes the arguments
    osc52_start = captured.err.index("\033]52;c;") + 7
    osc52_end = captured.err.index("\033\\", osc52_start)
    encoded_content = captured.err[osc52_start:osc52_end]
    decoded_content = base64.b64decode(encoded_content).decode("utf-8")
    assert decoded_content == f"source {script_path} 789 my-branch"


def test_print_temp_script_instructions_shows_clipboard_hint_with_args(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_temp_script_instructions shows '(copied to clipboard)' hint with args."""
    script_path = tmp_path / ".erk" / "bin" / "land.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_temp_script_instructions(
        script_path,
        instruction="To land the PR:",
        copy=True,
        args=[123, "feature"],
        extra_flags=None,
    )

    captured = capsys.readouterr()
    assert "(copied to clipboard)" in captured.err


def test_print_temp_script_instructions_with_extra_flags(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_temp_script_instructions includes extra_flags in the command."""
    script_path = tmp_path / ".erk" / "bin" / "land.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_temp_script_instructions(
        script_path,
        instruction="To land the PR:",
        copy=False,
        args=[123, "feature-branch"],
        extra_flags=["-f", "--up"],
    )

    captured = capsys.readouterr()
    assert "To land the PR:" in captured.err
    # Should include arguments and extra flags in the source command
    assert f"source {script_path} 123 feature-branch -f --up" in captured.err


def test_print_temp_script_instructions_with_extra_flags_no_args(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_temp_script_instructions appends extra_flags even without args."""
    script_path = tmp_path / ".erk" / "bin" / "land.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_temp_script_instructions(
        script_path,
        instruction="To land the PR:",
        copy=False,
        args=None,
        extra_flags=["--no-pull", "--no-delete"],
    )

    captured = capsys.readouterr()
    assert f"source {script_path} --no-pull --no-delete" in captured.err


def test_print_temp_script_instructions_copies_command_with_extra_flags(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """print_temp_script_instructions with copy=True includes extra_flags in clipboard."""
    script_path = tmp_path / ".erk" / "bin" / "land.sh"
    script_path.parent.mkdir(parents=True)
    script_path.touch()

    print_temp_script_instructions(
        script_path,
        instruction="To land the PR:",
        copy=True,
        args=[789, "my-branch"],
        extra_flags=["-f", "--up"],
    )

    captured = capsys.readouterr()

    # Verify the base64-encoded content includes args and extra_flags
    osc52_start = captured.err.index("\033]52;c;") + 7
    osc52_end = captured.err.index("\033\\", osc52_start)
    encoded_content = captured.err[osc52_start:osc52_end]
    decoded_content = base64.b64decode(encoded_content).decode("utf-8")
    assert decoded_content == f"source {script_path} 789 my-branch -f --up"
