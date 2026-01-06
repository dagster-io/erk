"""Tests for subshell utilities."""

import os
from pathlib import Path
from unittest.mock import patch

from erk.cli.subshell import (
    detect_user_shell,
    format_subshell_welcome_message,
    is_shell_integration_active,
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
