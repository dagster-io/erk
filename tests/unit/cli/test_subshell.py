"""Tests for subshell utilities."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from erk.cli.subshell import (
    detect_user_shell,
    format_subshell_welcome_message,
    is_shell_integration_active,
    spawn_worktree_subshell,
)


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


def test_format_subshell_welcome_message_contains_worktree_path(tmp_path: Path) -> None:
    """Welcome message includes worktree path."""
    worktree_path = tmp_path / "slot-01"
    worktree_path.mkdir()

    result = format_subshell_welcome_message(worktree_path, branch="feature-branch")

    assert str(worktree_path) in result


def test_format_subshell_welcome_message_contains_branch(tmp_path: Path) -> None:
    """Welcome message includes branch name."""
    worktree_path = tmp_path / "slot-01"
    worktree_path.mkdir()

    result = format_subshell_welcome_message(worktree_path, branch="my-feature-branch")

    assert "my-feature-branch" in result


def test_format_subshell_welcome_message_contains_prompt_hint(tmp_path: Path) -> None:
    """Welcome message includes prompt customization hint."""
    worktree_path = tmp_path / "slot-01"
    worktree_path.mkdir()

    result = format_subshell_welcome_message(worktree_path, branch="feature")

    # Check for key prompt customization elements
    assert "ERK_SUBSHELL" in result
    assert "ERK_WORKTREE_NAME" in result
    assert "PS1" in result
    assert ".bashrc" in result or ".zshrc" in result


def test_format_subshell_welcome_message_contains_exit_instruction(tmp_path: Path) -> None:
    """Welcome message includes exit instruction."""
    worktree_path = tmp_path / "slot-01"
    worktree_path.mkdir()

    result = format_subshell_welcome_message(worktree_path, branch="feature")

    assert "exit" in result


# spawn_worktree_subshell tests


def test_spawn_worktree_subshell_sets_environment_variables(tmp_path: Path) -> None:
    """spawn_worktree_subshell sets ERK_SUBSHELL and ERK_WORKTREE_NAME in env."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("erk.cli.subshell.subprocess.run", return_value=mock_result) as mock_run:
        spawn_worktree_subshell(
            worktree_path=worktree_path,
            branch="feature-branch",
            claude_command="/erk:plan-implement",
            dangerous=False,
            model=None,
            shell="/bin/bash",
        )

        # Verify subprocess.run was called
        assert mock_run.call_count == 1
        call_kwargs = mock_run.call_args[1]

        # Verify environment variables
        assert call_kwargs["env"]["ERK_SUBSHELL"] == "1"
        assert call_kwargs["env"]["ERK_WORKTREE_NAME"] == "test-worktree"


def test_spawn_worktree_subshell_sets_cwd_to_worktree(tmp_path: Path) -> None:
    """spawn_worktree_subshell runs subprocess with cwd set to worktree path."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("erk.cli.subshell.subprocess.run", return_value=mock_result) as mock_run:
        spawn_worktree_subshell(
            worktree_path=worktree_path,
            branch="feature-branch",
            claude_command="/erk:plan-implement",
            dangerous=False,
            model=None,
            shell="/bin/bash",
        )

        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cwd"] == worktree_path


def test_spawn_worktree_subshell_returns_exit_code(tmp_path: Path) -> None:
    """spawn_worktree_subshell returns the subprocess exit code."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    mock_result = MagicMock()
    mock_result.returncode = 42

    with patch("erk.cli.subshell.subprocess.run", return_value=mock_result):
        exit_code = spawn_worktree_subshell(
            worktree_path=worktree_path,
            branch="feature-branch",
            claude_command="/erk:plan-implement",
            dangerous=False,
            model=None,
            shell="/bin/bash",
        )

        assert exit_code == 42


def test_spawn_worktree_subshell_includes_claude_command(tmp_path: Path) -> None:
    """spawn_worktree_subshell includes claude command in shell args."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("erk.cli.subshell.subprocess.run", return_value=mock_result) as mock_run:
        spawn_worktree_subshell(
            worktree_path=worktree_path,
            branch="feature-branch",
            claude_command="/erk:plan-implement",
            dangerous=False,
            model=None,
            shell="/bin/bash",
        )

        call_args = mock_run.call_args[0][0]
        # The shell command string should include the claude command
        shell_cmd_str = call_args[2]  # Third arg is the -c command string
        assert "/erk:plan-implement" in shell_cmd_str
        assert "--permission-mode" in shell_cmd_str
        assert "acceptEdits" in shell_cmd_str


def test_spawn_worktree_subshell_includes_dangerous_flag_when_set(tmp_path: Path) -> None:
    """spawn_worktree_subshell includes --dangerously-skip-permissions when dangerous=True."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("erk.cli.subshell.subprocess.run", return_value=mock_result) as mock_run:
        spawn_worktree_subshell(
            worktree_path=worktree_path,
            branch="feature-branch",
            claude_command="/erk:plan-implement",
            dangerous=True,
            model=None,
            shell="/bin/bash",
        )

        call_args = mock_run.call_args[0][0]
        shell_cmd_str = call_args[2]
        assert "--dangerously-skip-permissions" in shell_cmd_str


def test_spawn_worktree_subshell_includes_model_flag_when_set(tmp_path: Path) -> None:
    """spawn_worktree_subshell includes --model when model is specified."""
    worktree_path = tmp_path / "test-worktree"
    worktree_path.mkdir()

    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("erk.cli.subshell.subprocess.run", return_value=mock_result) as mock_run:
        spawn_worktree_subshell(
            worktree_path=worktree_path,
            branch="feature-branch",
            claude_command="/erk:plan-implement",
            dangerous=False,
            model="opus",
            shell="/bin/bash",
        )

        call_args = mock_run.call_args[0][0]
        shell_cmd_str = call_args[2]
        assert "--model" in shell_cmd_str
        assert "opus" in shell_cmd_str
