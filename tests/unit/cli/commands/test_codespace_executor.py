"""Unit tests for codespace_executor module."""

from datetime import datetime

import pytest

from erk.cli.commands.codespace_executor import (
    CodespaceNotFoundError,
    build_remote_command,
    resolve_codespace,
)
from erk_shared.gateway.codespace_registry.abc import RegisteredCodespace
from erk_shared.gateway.codespace_registry.fake import FakeCodespaceRegistry


class TestResolveCodespace:
    """Tests for resolve_codespace function."""

    def test_resolve_by_name_succeeds(self) -> None:
        """Test resolving a codespace by name."""
        codespace = RegisteredCodespace(
            name="mybox",
            gh_name="user-mybox-abc123",
            created_at=datetime(2025, 1, 1, 12, 0),
        )
        registry = FakeCodespaceRegistry(codespaces=[codespace])

        result = resolve_codespace(registry, name="mybox")

        assert result == codespace

    def test_resolve_by_name_not_found(self) -> None:
        """Test error when named codespace not found."""
        registry = FakeCodespaceRegistry()

        with pytest.raises(CodespaceNotFoundError) as exc_info:
            resolve_codespace(registry, name="nonexistent")

        assert "No codespace named 'nonexistent' found" in str(exc_info.value)

    def test_resolve_default_succeeds(self) -> None:
        """Test resolving the default codespace."""
        codespace = RegisteredCodespace(
            name="default-box",
            gh_name="user-default-abc123",
            created_at=datetime(2025, 1, 1, 12, 0),
        )
        registry = FakeCodespaceRegistry(
            codespaces=[codespace],
            default_codespace="default-box",
        )

        result = resolve_codespace(registry, name=None)

        assert result == codespace

    def test_resolve_default_no_default_set(self) -> None:
        """Test error when no default codespace is set."""
        registry = FakeCodespaceRegistry()

        with pytest.raises(CodespaceNotFoundError) as exc_info:
            resolve_codespace(registry, name=None)

        assert "No default codespace set" in str(exc_info.value)

    def test_resolve_default_not_found(self) -> None:
        """Test error when default codespace name doesn't exist."""
        # Registry with default name but no actual codespace
        registry = FakeCodespaceRegistry(default_codespace="deleted-box")

        with pytest.raises(CodespaceNotFoundError) as exc_info:
            resolve_codespace(registry, name=None)

        assert "Default codespace 'deleted-box' not found" in str(exc_info.value)


class TestBuildRemoteCommand:
    """Tests for build_remote_command function."""

    def test_interactive_mode(self) -> None:
        """Test building remote command for interactive mode."""
        result = build_remote_command(
            interactive=True,
            model=None,
            command="/erk:plan-implement",
            command_arg=None,
        )

        # Should wrap in bash -l -c for login shell
        assert "bash -l -c" in result
        # Should include git pull before venv activation
        assert "git pull" in result
        # Should include venv activation
        assert "source .venv/bin/activate" in result
        # Should include dangerous skip permissions
        assert "--dangerously-skip-permissions" in result
        # Should include the command (quoted)
        assert '"/erk:plan-implement"' in result
        # Should NOT include print mode for interactive
        assert "--print" not in result

    def test_non_interactive_mode(self) -> None:
        """Test building remote command for non-interactive mode."""
        result = build_remote_command(
            interactive=False,
            model=None,
            command="/erk:plan-implement",
            command_arg=None,
        )

        # Should include print mode and output format for non-interactive
        assert "--print" in result
        assert "--verbose" in result
        assert "--output-format stream-json" in result
        # Should include dangerous skip permissions
        assert "--dangerously-skip-permissions" in result

    def test_with_model(self) -> None:
        """Test building remote command with model specified."""
        result = build_remote_command(
            interactive=True,
            model="haiku",
            command="/erk:plan-implement",
            command_arg=None,
        )

        assert "--model haiku" in result

    def test_without_model(self) -> None:
        """Test building remote command without model."""
        result = build_remote_command(
            interactive=True,
            model=None,
            command="/erk:plan-implement",
            command_arg=None,
        )

        assert "--model" not in result

    def test_command_quoted(self) -> None:
        """Test that the command is properly quoted."""
        result = build_remote_command(
            interactive=True,
            model=None,
            command="/fast-ci",
            command_arg=None,
        )

        assert '"/fast-ci"' in result

    def test_command_with_arg(self) -> None:
        """Test that command_arg is appended to command."""
        result = build_remote_command(
            interactive=True,
            model=None,
            command="/erk:plan-implement",
            command_arg="5394",
        )

        # Should include the command with argument (quoted)
        assert '"/erk:plan-implement 5394"' in result

    def test_command_with_file_path_arg(self) -> None:
        """Test that file path command_arg is appended to command."""
        result = build_remote_command(
            interactive=True,
            model=None,
            command="/erk:plan-implement",
            command_arg="./my-plan.md",
        )

        # Should include the command with file path argument (quoted)
        assert '"/erk:plan-implement ./my-plan.md"' in result

    def test_without_command_arg(self) -> None:
        """Test building remote command without command_arg has no argument."""
        result = build_remote_command(
            interactive=True,
            model=None,
            command="/erk:plan-implement",
            command_arg=None,
        )

        # Should include just the command without trailing argument
        assert '"/erk:plan-implement"' in result
        # Make sure we don't have a space after (no trailing argument)
        assert '"/erk:plan-implement "' not in result

    def test_git_pull_included_in_setup(self) -> None:
        """Test that git pull is included in setup commands."""
        result = build_remote_command(
            interactive=True,
            model=None,
            command="/erk:plan-implement",
            command_arg=None,
        )

        # Should include git pull before source .venv
        assert "git pull && source .venv/bin/activate" in result
