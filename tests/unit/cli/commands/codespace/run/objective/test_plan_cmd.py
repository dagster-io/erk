"""Unit tests for codespace run objective plan command."""

from datetime import datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.context import context_for_test
from erk_shared.gateway.codespace.fake import FakeCodespace
from erk_shared.gateway.codespace_registry.abc import RegisteredCodespace
from erk_shared.gateway.codespace_registry.fake import FakeCodespaceRegistry


def _make_codespace(name: str) -> RegisteredCodespace:
    return RegisteredCodespace(
        name=name,
        gh_name=f"user-{name}-abc123",
        created_at=datetime(2026, 1, 20, 8, 0, 0),
    )


def test_run_plan_starts_codespace_and_runs_command() -> None:
    """run objective plan starts the codespace and runs the command."""
    runner = CliRunner()

    cs = _make_codespace("mybox")
    fake_codespace = FakeCodespace()
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    ctx = context_for_test(codespace=fake_codespace, codespace_registry=codespace_registry)

    result = runner.invoke(
        cli,
        ["codespace", "run", "objective", "plan", "42"],
        obj=ctx,
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "Starting codespace 'mybox'" in result.output
    assert "Running 'erk objective plan 42' on 'mybox'" in result.output

    # Verify start_codespace was called
    assert fake_codespace.started_codespaces == ["user-mybox-abc123"]

    # Verify exec_ssh_interactive was called with correct remote command
    assert fake_codespace.exec_called is True
    assert len(fake_codespace.ssh_calls) == 1
    call = fake_codespace.ssh_calls[0]
    assert call.gh_name == "user-mybox-abc123"
    assert "erk objective plan 42" in call.remote_command
    assert call.interactive is True


def test_run_plan_with_explicit_codespace() -> None:
    """run objective plan -c box2 uses the specified codespace."""
    runner = CliRunner()

    cs1 = _make_codespace("box1")
    cs2 = _make_codespace("box2")
    fake_codespace = FakeCodespace()
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs1, cs2], default_codespace="box1")
    ctx = context_for_test(codespace=fake_codespace, codespace_registry=codespace_registry)

    result = runner.invoke(
        cli,
        ["codespace", "run", "objective", "plan", "42", "-c", "box2"],
        obj=ctx,
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert fake_codespace.started_codespaces == ["user-box2-abc123"]
    assert fake_codespace.ssh_calls[0].gh_name == "user-box2-abc123"


def test_run_plan_fails_when_no_codespace() -> None:
    """run objective plan fails when no codespace is configured."""
    runner = CliRunner()

    codespace_registry = FakeCodespaceRegistry()
    ctx = context_for_test(codespace_registry=codespace_registry)

    result = runner.invoke(
        cli,
        ["codespace", "run", "objective", "plan", "42"],
        obj=ctx,
        catch_exceptions=False,
    )

    assert result.exit_code == 1
    assert "No default codespace set" in result.output


def test_run_plan_with_dangerous_flag() -> None:
    """run objective plan -d includes -d flag in remote command."""
    runner = CliRunner()

    cs = _make_codespace("mybox")
    fake_codespace = FakeCodespace()
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    ctx = context_for_test(codespace=fake_codespace, codespace_registry=codespace_registry)

    result = runner.invoke(
        cli,
        ["codespace", "run", "objective", "plan", "-d", "42"],
        obj=ctx,
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "Running 'erk objective plan -d 42' on 'mybox'" in result.output

    # Verify the remote command includes -d flag
    assert len(fake_codespace.ssh_calls) == 1
    call = fake_codespace.ssh_calls[0]
    assert "erk objective plan -d 42" in call.remote_command


def test_run_plan_without_dangerous_flag() -> None:
    """run objective plan without -d does not include -d in remote command."""
    runner = CliRunner()

    cs = _make_codespace("mybox")
    fake_codespace = FakeCodespace()
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    ctx = context_for_test(codespace=fake_codespace, codespace_registry=codespace_registry)

    result = runner.invoke(
        cli,
        ["codespace", "run", "objective", "plan", "42"],
        obj=ctx,
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "Running 'erk objective plan 42' on 'mybox'" in result.output

    # Verify the remote command does not include -d flag
    assert len(fake_codespace.ssh_calls) == 1
    call = fake_codespace.ssh_calls[0]
    assert "erk objective plan 42" in call.remote_command
    assert "-d" not in call.remote_command
