"""Unit tests for codespace connect command."""

from datetime import datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.codespace.registry_fake import FakeCodespaceRegistry
from erk.core.codespace.types import RegisteredCodespace
from erk.core.context import context_for_test


def test_connect_shows_error_when_no_codespaces() -> None:
    """connect command shows error when no codespaces are registered."""
    runner = CliRunner()

    codespace_registry = FakeCodespaceRegistry()
    ctx = context_for_test(codespace_registry=codespace_registry)

    result = runner.invoke(cli, ["codespace", "connect"], obj=ctx, catch_exceptions=False)

    assert result.exit_code == 1
    assert "No default codespace set" in result.output
    assert "erk codespace setup" in result.output


def test_connect_shows_error_when_named_codespace_not_found() -> None:
    """connect command shows error when specified codespace doesn't exist."""
    runner = CliRunner()

    codespace_registry = FakeCodespaceRegistry()
    ctx = context_for_test(codespace_registry=codespace_registry)

    result = runner.invoke(
        cli, ["codespace", "connect", "nonexistent"], obj=ctx, catch_exceptions=False
    )

    assert result.exit_code == 1
    assert "No codespace named 'nonexistent' found" in result.output
    assert "erk codespace setup" in result.output


def test_connect_shows_error_when_default_not_found() -> None:
    """connect command shows error when default codespace no longer exists."""
    runner = CliRunner()

    # Registry has a default set but that codespace doesn't exist
    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    # Now unregister to simulate stale default
    codespace_registry.unregister("mybox")
    # Re-set default to a non-existent name to simulate stale state
    codespace_registry._default_codespace = "mybox"

    ctx = context_for_test(codespace_registry=codespace_registry)

    result = runner.invoke(cli, ["codespace", "connect"], obj=ctx, catch_exceptions=False)

    assert result.exit_code == 1
    assert "Default codespace 'mybox' not found" in result.output


def test_connect_outputs_connecting_message_for_valid_codespace(monkeypatch) -> None:
    """connect command outputs connecting message and calls os.execvp with correct args."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc123", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    ctx = context_for_test(codespace_registry=codespace_registry)

    # Track execvp calls instead of actually replacing the process
    execvp_calls: list[tuple[str, list[str]]] = []

    def mock_execvp(file: str, args: list[str]) -> None:
        execvp_calls.append((file, args))

    monkeypatch.setattr("os.execvp", mock_execvp)

    result = runner.invoke(cli, ["codespace", "connect"], obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert "Connecting to codespace 'mybox'" in result.output

    # Verify execvp was called with correct arguments
    assert len(execvp_calls) == 1
    file, args = execvp_calls[0]
    assert file == "gh"
    assert "codespace" in args
    assert "ssh" in args
    assert "user-mybox-abc123" in args  # gh_name


def test_connect_with_explicit_name(monkeypatch) -> None:
    """connect command works with explicit codespace name."""
    runner = CliRunner()

    cs1 = RegisteredCodespace(
        name="box1", gh_name="user-box1-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    cs2 = RegisteredCodespace(
        name="box2", gh_name="user-box2-def", created_at=datetime(2026, 1, 20, 9, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs1, cs2], default_codespace="box1")
    ctx = context_for_test(codespace_registry=codespace_registry)

    # Track execvp calls
    execvp_calls: list[tuple[str, list[str]]] = []

    def mock_execvp(file: str, args: list[str]) -> None:
        execvp_calls.append((file, args))

    monkeypatch.setattr("os.execvp", mock_execvp)

    # Connect to non-default codespace
    result = runner.invoke(cli, ["codespace", "connect", "box2"], obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert "Connecting to codespace 'box2'" in result.output

    # Verify execvp was called with box2's gh_name
    assert len(execvp_calls) == 1
    _, args = execvp_calls[0]
    assert "user-box2-def" in args  # box2's gh_name, not box1's


def test_connect_with_shell_flag_drops_to_shell(monkeypatch) -> None:
    """connect --shell drops into shell instead of launching Claude."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc123", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    ctx = context_for_test(codespace_registry=codespace_registry)

    execvp_calls: list[tuple[str, list[str]]] = []

    def mock_execvp(file: str, args: list[str]) -> None:
        execvp_calls.append((file, args))

    monkeypatch.setattr("os.execvp", mock_execvp)

    result = runner.invoke(
        cli, ["codespace", "connect", "--shell"], obj=ctx, catch_exceptions=False
    )

    assert result.exit_code == 0
    assert len(execvp_calls) == 1
    _, args = execvp_calls[0]

    # Find the remote command argument (after -t)
    t_index = args.index("-t")
    remote_command = args[t_index + 1]

    # Should use simple login shell, not claude or setup commands
    assert remote_command == "bash -l"
    assert "claude" not in remote_command
    assert "git pull" not in remote_command
