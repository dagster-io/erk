"""Tests for subshell spawning utilities."""

from pathlib import Path

import pytest

from erk.cli.subshell import (
    _build_shell_init_command,
    detect_user_shell,
    format_subshell_welcome_message,
    is_shell_integration_active,
)

# Tests for is_shell_integration_active


def test_is_shell_integration_active_returns_true_when_erk_shell_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns True when ERK_SHELL environment variable is set."""
    monkeypatch.setenv("ERK_SHELL", "zsh")
    assert is_shell_integration_active() is True


def test_is_shell_integration_active_returns_false_when_erk_shell_not_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns False when ERK_SHELL environment variable is not set."""
    monkeypatch.delenv("ERK_SHELL", raising=False)
    assert is_shell_integration_active() is False


def test_is_shell_integration_active_returns_true_for_empty_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns True even for empty string (env var is set)."""
    monkeypatch.setenv("ERK_SHELL", "")
    # An empty string still means the var is set
    assert is_shell_integration_active() is True


# Tests for detect_user_shell


def test_detect_user_shell_returns_shell_env_var(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns $SHELL when set."""
    monkeypatch.setenv("SHELL", "/bin/zsh")
    assert detect_user_shell() == "/bin/zsh"


def test_detect_user_shell_returns_default_when_shell_not_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns /bin/sh as default when $SHELL is not set."""
    monkeypatch.delenv("SHELL", raising=False)
    assert detect_user_shell() == "/bin/sh"


def test_detect_user_shell_returns_various_shells(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Returns various shell values from $SHELL."""
    test_shells = ["/bin/bash", "/usr/local/bin/fish", "/opt/homebrew/bin/zsh"]
    for shell in test_shells:
        monkeypatch.setenv("SHELL", shell)
        assert detect_user_shell() == shell


# Tests for format_subshell_welcome_message


def test_format_subshell_welcome_message_includes_path() -> None:
    """Welcome message includes the worktree path."""
    message = format_subshell_welcome_message(
        worktree_path=Path("/path/to/worktree"),
        branch="feature-branch",
    )
    assert "/path/to/worktree" in message


def test_format_subshell_welcome_message_includes_branch() -> None:
    """Welcome message includes the branch name."""
    message = format_subshell_welcome_message(
        worktree_path=Path("/path/to/worktree"),
        branch="feature-branch",
    )
    assert "feature-branch" in message


def test_format_subshell_welcome_message_includes_shell_integration_hint() -> None:
    """Welcome message includes shell integration installation hint."""
    message = format_subshell_welcome_message(
        worktree_path=Path("/path/to/worktree"),
        branch="feature-branch",
    )
    assert "erk init --shell" in message


def test_format_subshell_welcome_message_includes_prompt_customization() -> None:
    """Welcome message includes prompt customization hint."""
    message = format_subshell_welcome_message(
        worktree_path=Path("/path/to/worktree"),
        branch="feature-branch",
    )
    assert "ERK_SUBSHELL" in message
    assert "ERK_WORKTREE_NAME" in message
    assert "PS1=" in message


def test_format_subshell_welcome_message_includes_exit_hint() -> None:
    """Welcome message includes exit hint."""
    message = format_subshell_welcome_message(
        worktree_path=Path("/path/to/worktree"),
        branch="feature-branch",
    )
    assert "exit" in message


def test_format_subshell_welcome_message_has_borders() -> None:
    """Welcome message has decorative borders."""
    message = format_subshell_welcome_message(
        worktree_path=Path("/path/to/worktree"),
        branch="feature-branch",
    )
    # Check for Unicode box drawing character
    assert "━" in message


# Tests for _build_shell_init_command


def test_build_shell_init_command_basic() -> None:
    """Builds basic Claude command."""
    cmd = _build_shell_init_command(
        shell="/bin/bash",
        claude_command="/erk:plan-implement",
        dangerous=False,
        model=None,
    )
    assert "claude" in cmd
    assert "/erk:plan-implement" in cmd
    assert "--permission-mode" in cmd
    assert "acceptEdits" in cmd


def test_build_shell_init_command_with_dangerous() -> None:
    """Includes --dangerously-skip-permissions when dangerous=True."""
    cmd = _build_shell_init_command(
        shell="/bin/bash",
        claude_command="/erk:plan-implement",
        dangerous=True,
        model=None,
    )
    assert "--dangerously-skip-permissions" in cmd


def test_build_shell_init_command_with_model() -> None:
    """Includes --model when model is specified."""
    cmd = _build_shell_init_command(
        shell="/bin/bash",
        claude_command="/erk:plan-implement",
        dangerous=False,
        model="haiku",
    )
    assert "--model" in cmd
    assert "haiku" in cmd


def test_build_shell_init_command_with_all_options() -> None:
    """Includes all options when specified."""
    cmd = _build_shell_init_command(
        shell="/bin/bash",
        claude_command="/erk:plan-implement",
        dangerous=True,
        model="opus",
    )
    assert "--dangerously-skip-permissions" in cmd
    assert "--model" in cmd
    assert "opus" in cmd
