"""Unit tests for codespace connect command."""

from datetime import datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.context import context_for_test
from erk_shared.gateway.codespace.fake import FakeCodespace
from erk_shared.gateway.codespace_registry.abc import RegisteredCodespace
from erk_shared.gateway.codespace_registry.fake import FakeCodespaceRegistry


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


def test_connect_outputs_connecting_message_for_valid_codespace() -> None:
    """connect command outputs connecting message and calls codespace SSH with correct args."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc123", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    fake_codespace = FakeCodespace()
    ctx = context_for_test(codespace_registry=codespace_registry, codespace=fake_codespace)

    result = runner.invoke(cli, ["codespace", "connect"], obj=ctx)

    # FakeCodespace.exec_ssh_interactive raises SystemExit(0), which CliRunner catches
    assert result.exit_code == 0

    # Verify exec_ssh_interactive was called with correct arguments
    assert fake_codespace.exec_called
    assert fake_codespace.last_call is not None
    assert fake_codespace.last_call.gh_name == "user-mybox-abc123"
    assert fake_codespace.last_call.interactive is True
    # Verify the command includes Claude setup
    assert "claude" in fake_codespace.last_call.remote_command
    assert "git pull" in fake_codespace.last_call.remote_command


def test_connect_with_explicit_name() -> None:
    """connect command works with explicit codespace name."""
    runner = CliRunner()

    cs1 = RegisteredCodespace(
        name="box1", gh_name="user-box1-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    cs2 = RegisteredCodespace(
        name="box2", gh_name="user-box2-def", created_at=datetime(2026, 1, 20, 9, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs1, cs2], default_codespace="box1")
    fake_codespace = FakeCodespace()
    ctx = context_for_test(codespace_registry=codespace_registry, codespace=fake_codespace)

    # Connect to non-default codespace
    result = runner.invoke(cli, ["codespace", "connect", "box2"], obj=ctx)

    assert result.exit_code == 0

    # Verify SSH was called with box2's gh_name
    assert fake_codespace.exec_called
    assert fake_codespace.last_call is not None
    assert fake_codespace.last_call.gh_name == "user-box2-def"  # box2's gh_name, not box1's


def test_connect_with_shell_flag_drops_to_shell() -> None:
    """connect --shell drops into shell instead of launching Claude."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc123", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    fake_codespace = FakeCodespace()
    ctx = context_for_test(codespace_registry=codespace_registry, codespace=fake_codespace)

    result = runner.invoke(cli, ["codespace", "connect", "--shell"], obj=ctx)

    assert result.exit_code == 0
    assert fake_codespace.exec_called
    assert fake_codespace.last_call is not None

    # Should use simple login shell, not claude or setup commands
    remote_command = fake_codespace.last_call.remote_command
    assert remote_command == "bash -l"
    assert "claude" not in remote_command
    assert "git pull" not in remote_command
