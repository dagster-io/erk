"""Unit tests for codespace list command."""

from datetime import datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.context import context_for_test
from erk_shared.gateway.codespace_registry.abc import RegisteredCodespace
from erk_shared.gateway.codespace_registry.fake import FakeCodespaceRegistry


def test_list_shows_empty_message_when_no_codespaces() -> None:
    """list command shows empty message when no codespaces are registered."""
    runner = CliRunner()

    codespace_registry = FakeCodespaceRegistry()
    ctx = context_for_test(codespace_registry=codespace_registry)

    result = runner.invoke(cli, ["codespace", "list"], obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert "No codespaces registered" in result.output
    assert "erk codespace setup" in result.output


def test_list_shows_codespaces_sorted_by_name() -> None:
    """list command shows codespaces sorted alphabetically by name."""
    runner = CliRunner()

    cs_zebra = RegisteredCodespace(
        name="zebra", gh_name="user-zebra-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    cs_alpha = RegisteredCodespace(
        name="alpha", gh_name="user-alpha-def", created_at=datetime(2026, 1, 20, 9, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs_zebra, cs_alpha])
    ctx = context_for_test(codespace_registry=codespace_registry)

    result = runner.invoke(cli, ["codespace", "list"], obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    # alpha should appear before zebra
    alpha_pos = result.output.find("alpha")
    zebra_pos = result.output.find("zebra")
    assert alpha_pos < zebra_pos


def test_list_marks_default_codespace() -> None:
    """list command marks the default codespace with indicator."""
    runner = CliRunner()

    cs1 = RegisteredCodespace(
        name="box1", gh_name="user-box1-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    cs2 = RegisteredCodespace(
        name="box2", gh_name="user-box2-def", created_at=datetime(2026, 1, 20, 9, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs1, cs2], default_codespace="box2")
    ctx = context_for_test(codespace_registry=codespace_registry)

    result = runner.invoke(cli, ["codespace", "list"], obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    # box2 should show default indicator
    assert "(default)" in result.output


def test_list_shows_created_at_formatted() -> None:
    """list command shows created_at date in readable format."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc", created_at=datetime(2026, 1, 20, 14, 30, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs])
    ctx = context_for_test(codespace_registry=codespace_registry)

    result = runner.invoke(cli, ["codespace", "list"], obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert "2026-01-20 14:30" in result.output


def test_list_shows_gh_name_column() -> None:
    """list command shows the GitHub codespace name."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc123xyz", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs])
    ctx = context_for_test(codespace_registry=codespace_registry)

    result = runner.invoke(cli, ["codespace", "list"], obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert "user-mybox-abc123xyz" in result.output
