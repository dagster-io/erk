"""Tests for subshell utilities."""

import os
from pathlib import Path
from unittest.mock import patch

from erk.cli.subshell import (
    build_claude_command_string,
    build_prompt_setup_command,
    detect_user_shell,
    format_subshell_welcome_message,
    is_shell_integration_active,
    spawn_simple_subshell,
    spawn_worktree_subshell,
)
from erk_shared.gateway.shell import FakeShell


def test_is_shell_integration_active_when_erk_shell_set() -> None:
    """Shell integration is active when ERK_SHELL is set."""
    with patch.dict(os.environ, {"ERK_SHELL": "zsh"}):
        assert is_shell_integration_active() is True


def test_is_shell_integration_active_when_erk_shell_not_set() -> None:
    """Shell integration is not active when ERK_SHELL is not set."""
    # Ensure ERK_SHELL is not in environment
    env_copy = {k: v for k, v in os.environ.items() if k != "ERK_SHELL"}
    with patch.dict(os.environ, env_copy, clear=True):
        assert is_shell_integration_active() is False


def test_detect_user_shell_returns_shell_env_var() -> None:
    """detect_user_shell returns $SHELL when set."""
    with patch.dict(os.environ, {"SHELL": "/usr/local/bin/zsh"}):
        assert detect_user_shell() == "/usr/local/bin/zsh"


def test_detect_user_shell_returns_default_when_shell_not_set() -> None:
    """detect_user_shell returns /bin/sh when SHELL is not set."""
    env_copy = {k: v for k, v in os.environ.items() if k != "SHELL"}
    with patch.dict(os.environ, env_copy, clear=True):
        assert detect_user_shell() == "/bin/sh"


def test_format_subshell_welcome_message_contains_branch(tmp_path: Path) -> None:
    """Welcome message includes branch name."""
    worktree_path = tmp_path / "slot-01"
    worktree_path.mkdir()

    result = format_subshell_welcome_message(worktree_path, branch="my-feature-branch")

    assert "my-feature-branch" in result


def test_format_subshell_welcome_message_contains_exit_instruction(tmp_path: Path) -> None:
    """Welcome message includes exit instruction."""
    worktree_path = tmp_path / "slot-01"
    worktree_path.mkdir()

    result = format_subshell_welcome_message(worktree_path, branch="feature")

    assert "exit" in result


def test_format_subshell_welcome_message_is_concise(tmp_path: Path) -> None:
    """Welcome message is concise (no manual prompt configuration hints)."""
    worktree_path = tmp_path / "slot-01"
    worktree_path.mkdir()

    result = format_subshell_welcome_message(worktree_path, branch="feature")

    # Should NOT contain manual prompt configuration hints since we auto-modify prompt
    assert ".bashrc" not in result
    assert ".zshrc" not in result
    # Should say "worktree subshell" to indicate where we are
    assert "worktree subshell" in result


# build_claude_command_string tests


def test_build_claude_command_string_basic() -> None:
    """build_claude_command_string creates basic command."""
    result = build_claude_command_string(
        claude_command="/erk:plan-implement",
        dangerous=False,
        model=None,
    )

    assert "/erk:plan-implement" in result
    assert "--permission-mode" in result
    assert "acceptEdits" in result


def test_build_claude_command_string_with_dangerous() -> None:
    """build_claude_command_string includes dangerous flag."""
    result = build_claude_command_string(
        claude_command="/erk:plan-implement",
        dangerous=True,
        model=None,
    )

    assert "--dangerously-skip-permissions" in result


def test_build_claude_command_string_with_model() -> None:
    """build_claude_command_string includes model flag."""
    result = build_claude_command_string(
        claude_command="/erk:plan-implement",
        dangerous=False,
        model="opus",
    )

    assert "--model" in result
    assert "opus" in result


# build_prompt_setup_command tests


def test_build_prompt_setup_command_for_bash() -> None:
    """build_prompt_setup_command generates correct PS1 export for bash."""
    result = build_prompt_setup_command("/bin/bash")

    assert result == 'export PS1="(erk:$ERK_WORKTREE_NAME) $PS1"'


def test_build_prompt_setup_command_for_zsh() -> None:
    """build_prompt_setup_command generates correct PS1 export for zsh."""
    result = build_prompt_setup_command("/usr/local/bin/zsh")

    assert result == 'export PS1="(erk:$ERK_WORKTREE_NAME) $PS1"'


def test_build_prompt_setup_command_for_sh() -> None:
    """build_prompt_setup_command generates correct PS1 export for sh."""
    result = build_prompt_setup_command("/bin/sh")

    assert result == 'export PS1="(erk:$ERK_WORKTREE_NAME) $PS1"'


def test_build_prompt_setup_command_for_fish_returns_empty() -> None:
    """build_prompt_setup_command returns empty for fish (different syntax)."""
    result = build_prompt_setup_command("/usr/local/bin/fish")

    assert result == ""


def test_build_prompt_setup_command_for_unknown_shell_returns_empty() -> None:
    """build_prompt_setup_command returns empty for unknown shells."""
    result = build_prompt_setup_command("/usr/local/bin/exotic-shell")

    assert result == ""


def test_build_prompt_setup_command_returns_empty_when_opt_out_set() -> None:
    """build_prompt_setup_command respects ERK_NO_PROMPT_MODIFY."""
    with patch.dict(os.environ, {"ERK_NO_PROMPT_MODIFY": "1"}):
        result = build_prompt_setup_command("/bin/bash")

    assert result == ""


# spawn_worktree_subshell tests using FakeShell


def test_spawn_worktree_subshell_calls_gateway(tmp_path: Path) -> None:
    """spawn_worktree_subshell calls shell gateway spawn_subshell."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    exit_code = spawn_worktree_subshell(
        shell,
        worktree_path=worktree_path,
        branch="feature-branch",
        claude_command="/erk:plan-implement",
        dangerous=False,
        model=None,
        shell="/bin/bash",
    )

    assert exit_code == 0
    assert len(shell.subshell_calls) == 1


def test_spawn_worktree_subshell_sets_environment_variables(tmp_path: Path) -> None:
    """spawn_worktree_subshell sets ERK_SUBSHELL and ERK_WORKTREE_NAME in env."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    spawn_worktree_subshell(
        shell,
        worktree_path=worktree_path,
        branch="feature-branch",
        claude_command="/erk:plan-implement",
        dangerous=False,
        model=None,
        shell="/bin/bash",
    )

    assert len(shell.subshell_calls) == 1
    call = shell.subshell_calls[0]

    # Verify environment variables
    assert call.env["ERK_SUBSHELL"] == "1"
    assert call.env["ERK_WORKTREE_NAME"] == "test-worktree"


def test_spawn_worktree_subshell_sets_cwd_to_worktree(tmp_path: Path) -> None:
    """spawn_worktree_subshell passes cwd to shell gateway."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    spawn_worktree_subshell(
        shell,
        worktree_path=worktree_path,
        branch="feature-branch",
        claude_command="/erk:plan-implement",
        dangerous=False,
        model=None,
        shell="/bin/bash",
    )

    call = shell.subshell_calls[0]
    assert call.cwd == worktree_path


def test_spawn_worktree_subshell_returns_exit_code(tmp_path: Path) -> None:
    """spawn_worktree_subshell returns the gateway exit code."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=42)

    exit_code = spawn_worktree_subshell(
        shell,
        worktree_path=worktree_path,
        branch="feature-branch",
        claude_command="/erk:plan-implement",
        dangerous=False,
        model=None,
        shell="/bin/bash",
    )

    assert exit_code == 42


def test_spawn_worktree_subshell_includes_claude_command(tmp_path: Path) -> None:
    """spawn_worktree_subshell includes claude command in shell command."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    spawn_worktree_subshell(
        shell,
        worktree_path=worktree_path,
        branch="feature-branch",
        claude_command="/erk:plan-implement",
        dangerous=False,
        model=None,
        shell="/bin/bash",
    )

    call = shell.subshell_calls[0]
    assert "/erk:plan-implement" in call.command
    assert "--permission-mode" in call.command
    assert "acceptEdits" in call.command


def test_spawn_worktree_subshell_includes_dangerous_flag_when_set(tmp_path: Path) -> None:
    """spawn_worktree_subshell includes --dangerously-skip-permissions when dangerous=True."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    spawn_worktree_subshell(
        shell,
        worktree_path=worktree_path,
        branch="feature-branch",
        claude_command="/erk:plan-implement",
        dangerous=True,
        model=None,
        shell="/bin/bash",
    )

    call = shell.subshell_calls[0]
    assert "--dangerously-skip-permissions" in call.command


def test_spawn_worktree_subshell_includes_model_flag_when_set(tmp_path: Path) -> None:
    """spawn_worktree_subshell includes --model when model is specified."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    spawn_worktree_subshell(
        shell,
        worktree_path=worktree_path,
        branch="feature-branch",
        claude_command="/erk:plan-implement",
        dangerous=False,
        model="opus",
        shell="/bin/bash",
    )

    call = shell.subshell_calls[0]
    assert "--model" in call.command
    assert "opus" in call.command


def test_spawn_worktree_subshell_passes_shell_path(tmp_path: Path) -> None:
    """spawn_worktree_subshell passes correct shell path to gateway."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    spawn_worktree_subshell(
        shell,
        worktree_path=worktree_path,
        branch="feature-branch",
        claude_command="/erk:plan-implement",
        dangerous=False,
        model=None,
        shell="/bin/zsh",
    )

    call = shell.subshell_calls[0]
    assert call.shell_path == "/bin/zsh"


def test_spawn_worktree_subshell_includes_prompt_setup(tmp_path: Path) -> None:
    """spawn_worktree_subshell includes prompt setup command for bash."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    # Ensure opt-out is NOT set
    env_copy = {k: v for k, v in os.environ.items() if k != "ERK_NO_PROMPT_MODIFY"}
    with patch.dict(os.environ, env_copy, clear=True):
        spawn_worktree_subshell(
            shell,
            worktree_path=worktree_path,
            branch="feature-branch",
            claude_command="/erk:plan-implement",
            dangerous=False,
            model=None,
            shell="/bin/bash",
        )

    call = shell.subshell_calls[0]
    # Command should start with prompt setup
    assert call.command.startswith('export PS1="(erk:$ERK_WORKTREE_NAME) $PS1"')
    # And still include the claude command
    assert "/erk:plan-implement" in call.command


def test_spawn_worktree_subshell_skips_prompt_setup_when_opt_out(tmp_path: Path) -> None:
    """spawn_worktree_subshell skips prompt setup when ERK_NO_PROMPT_MODIFY is set."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    with patch.dict(os.environ, {"ERK_NO_PROMPT_MODIFY": "1"}):
        spawn_worktree_subshell(
            shell,
            worktree_path=worktree_path,
            branch="feature-branch",
            claude_command="/erk:plan-implement",
            dangerous=False,
            model=None,
            shell="/bin/bash",
        )

    call = shell.subshell_calls[0]
    # Command should NOT contain prompt setup
    assert "export PS1" not in call.command
    # But still include the claude command
    assert "/erk:plan-implement" in call.command


def test_spawn_worktree_subshell_passes_opt_out_env_variable(tmp_path: Path) -> None:
    """spawn_worktree_subshell passes ERK_NO_PROMPT_MODIFY to subshell env."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    with patch.dict(os.environ, {"ERK_NO_PROMPT_MODIFY": "1"}):
        spawn_worktree_subshell(
            shell,
            worktree_path=worktree_path,
            branch="feature-branch",
            claude_command="/erk:plan-implement",
            dangerous=False,
            model=None,
            shell="/bin/bash",
        )

    call = shell.subshell_calls[0]
    # Verify ERK_NO_PROMPT_MODIFY is passed in environment
    assert call.env.get("ERK_NO_PROMPT_MODIFY") == "1"


def test_spawn_worktree_subshell_skips_prompt_setup_for_fish(tmp_path: Path) -> None:
    """spawn_worktree_subshell skips prompt setup for fish shell."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    # Ensure opt-out is NOT set
    env_copy = {k: v for k, v in os.environ.items() if k != "ERK_NO_PROMPT_MODIFY"}
    with patch.dict(os.environ, env_copy, clear=True):
        spawn_worktree_subshell(
            shell,
            worktree_path=worktree_path,
            branch="feature-branch",
            claude_command="/erk:plan-implement",
            dangerous=False,
            model=None,
            shell="/usr/local/bin/fish",
        )

    call = shell.subshell_calls[0]
    # Command should NOT contain prompt setup for fish
    assert "export PS1" not in call.command
    # But still include the claude command
    assert "/erk:plan-implement" in call.command


# spawn_simple_subshell tests using FakeShell


def test_spawn_simple_subshell_calls_gateway(tmp_path: Path) -> None:
    """spawn_simple_subshell calls shell gateway spawn_subshell."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    exit_code = spawn_simple_subshell(
        shell,
        worktree_path=worktree_path,
        branch="feature-branch",
        shell="/bin/bash",
    )

    assert exit_code == 0
    assert len(shell.subshell_calls) == 1


def test_spawn_simple_subshell_sets_environment_variables(tmp_path: Path) -> None:
    """spawn_simple_subshell sets ERK_SUBSHELL and ERK_WORKTREE_NAME in env."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    spawn_simple_subshell(
        shell,
        worktree_path=worktree_path,
        branch="feature-branch",
        shell="/bin/bash",
    )

    assert len(shell.subshell_calls) == 1
    call = shell.subshell_calls[0]

    # Verify environment variables
    assert call.env["ERK_SUBSHELL"] == "1"
    assert call.env["ERK_WORKTREE_NAME"] == "test-worktree"


def test_spawn_simple_subshell_sets_cwd_to_worktree(tmp_path: Path) -> None:
    """spawn_simple_subshell passes cwd to shell gateway."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    spawn_simple_subshell(
        shell,
        worktree_path=worktree_path,
        branch="feature-branch",
        shell="/bin/bash",
    )

    call = shell.subshell_calls[0]
    assert call.cwd == worktree_path


def test_spawn_simple_subshell_returns_exit_code(tmp_path: Path) -> None:
    """spawn_simple_subshell returns the gateway exit code."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=42)

    exit_code = spawn_simple_subshell(
        shell,
        worktree_path=worktree_path,
        branch="feature-branch",
        shell="/bin/bash",
    )

    assert exit_code == 42


def test_spawn_simple_subshell_does_not_include_claude_command(tmp_path: Path) -> None:
    """spawn_simple_subshell does NOT include claude command (unlike spawn_worktree_subshell)."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    # Ensure opt-out is NOT set
    env_copy = {k: v for k, v in os.environ.items() if k != "ERK_NO_PROMPT_MODIFY"}
    with patch.dict(os.environ, env_copy, clear=True):
        spawn_simple_subshell(
            shell,
            worktree_path=worktree_path,
            branch="feature-branch",
            shell="/bin/bash",
        )

    call = shell.subshell_calls[0]
    # Command should NOT contain any claude command
    assert "claude" not in call.command if call.command else True
    assert "/erk:plan-implement" not in (call.command or "")


def test_spawn_simple_subshell_includes_prompt_setup(tmp_path: Path) -> None:
    """spawn_simple_subshell includes prompt setup command for bash."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    # Ensure opt-out is NOT set
    env_copy = {k: v for k, v in os.environ.items() if k != "ERK_NO_PROMPT_MODIFY"}
    with patch.dict(os.environ, env_copy, clear=True):
        spawn_simple_subshell(
            shell,
            worktree_path=worktree_path,
            branch="feature-branch",
            shell="/bin/bash",
        )

    call = shell.subshell_calls[0]
    # Command should contain only prompt setup (no claude command)
    assert call.command == 'export PS1="(erk:$ERK_WORKTREE_NAME) $PS1"'


def test_spawn_simple_subshell_passes_noop_command_when_opt_out(tmp_path: Path) -> None:
    """spawn_simple_subshell passes no-op command when ERK_NO_PROMPT_MODIFY is set."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    with patch.dict(os.environ, {"ERK_NO_PROMPT_MODIFY": "1"}):
        spawn_simple_subshell(
            shell,
            worktree_path=worktree_path,
            branch="feature-branch",
            shell="/bin/bash",
        )

    call = shell.subshell_calls[0]
    # Command should be ":" (no-op) when prompt setup is opted out
    assert call.command == ":"


def test_spawn_simple_subshell_passes_shell_path(tmp_path: Path) -> None:
    """spawn_simple_subshell passes correct shell path to gateway."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    spawn_simple_subshell(
        shell,
        worktree_path=worktree_path,
        branch="feature-branch",
        shell="/bin/zsh",
    )

    call = shell.subshell_calls[0]
    assert call.shell_path == "/bin/zsh"


def test_spawn_simple_subshell_passes_opt_out_env_variable(tmp_path: Path) -> None:
    """spawn_simple_subshell passes ERK_NO_PROMPT_MODIFY to subshell env."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    with patch.dict(os.environ, {"ERK_NO_PROMPT_MODIFY": "1"}):
        spawn_simple_subshell(
            shell,
            worktree_path=worktree_path,
            branch="feature-branch",
            shell="/bin/bash",
        )

    call = shell.subshell_calls[0]
    # Verify ERK_NO_PROMPT_MODIFY is passed in environment
    assert call.env.get("ERK_NO_PROMPT_MODIFY") == "1"


def test_spawn_simple_subshell_passes_noop_command_for_fish(tmp_path: Path) -> None:
    """spawn_simple_subshell passes no-op command for fish shell (no prompt setup)."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    shell = FakeShell(subshell_exit_code=0)

    # Ensure opt-out is NOT set
    env_copy = {k: v for k, v in os.environ.items() if k != "ERK_NO_PROMPT_MODIFY"}
    with patch.dict(os.environ, env_copy, clear=True):
        spawn_simple_subshell(
            shell,
            worktree_path=worktree_path,
            branch="feature-branch",
            shell="/usr/local/bin/fish",
        )

    call = shell.subshell_calls[0]
    # Command should be ":" (no-op) for fish (no prompt setup)
    assert call.command == ":"
