"""Unit tests for codespace_executor module."""

from datetime import datetime

import pytest

from erk.cli.commands.codespace_executor import (
    CodespaceNotFoundError,
    build_remote_command,
    resolve_codespace,
)
from erk.core.codespace.registry_fake import FakeCodespaceRegistry
from erk.core.codespace.types import RegisteredCodespace


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
        )

        # Should wrap in bash -l -c for login shell
        assert "bash -l -c" in result
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
        )

        assert "--model haiku" in result

    def test_without_model(self) -> None:
        """Test building remote command without model."""
        result = build_remote_command(
            interactive=True,
            model=None,
            command="/erk:plan-implement",
        )

        assert "--model" not in result

    def test_command_quoted(self) -> None:
        """Test that the command is properly quoted."""
        result = build_remote_command(
            interactive=True,
            model=None,
            command="/fast-ci",
        )

        assert '"/fast-ci"' in result
