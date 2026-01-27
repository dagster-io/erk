"""Unit tests for codespace setup command."""

from datetime import datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.context import context_for_test
from erk_shared.gateway.codespace_registry.abc import RegisteredCodespace
from erk_shared.gateway.codespace_registry.fake import FakeCodespaceRegistry


def test_setup_shows_error_when_name_exists() -> None:
    """setup command shows error if codespace with same name exists."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs])
    ctx = context_for_test(codespace_registry=codespace_registry)

    result = runner.invoke(cli, ["codespace", "setup", "mybox"], obj=ctx, catch_exceptions=False)

    assert result.exit_code == 1
    assert "A codespace named 'mybox' already exists" in result.output
    assert "erk codespace [name]" in result.output


def test_setup_derives_name_from_repo_info() -> None:
    """setup command derives codespace name from repo_info if not provided.

    This test is limited because the actual gh codespace create subprocess
    call will fail, but we can verify the derived name is used.
    """
    runner = CliRunner()

    codespace_registry = FakeCodespaceRegistry()
    from erk_shared.gateway.github.types import RepoInfo

    ctx = context_for_test(
        codespace_registry=codespace_registry,
        repo_info=RepoInfo(owner="myorg", name="myproject"),
    )

    # Will fail at subprocess but should output the derived name
    result = runner.invoke(cli, ["codespace", "setup"], obj=ctx, catch_exceptions=True)

    # The derived name should be "{repo_name}-codespace"
    assert "Using codespace name: myproject-codespace" in result.output


def test_setup_uses_default_name_without_repo_info() -> None:
    """setup command uses default name when no repo_info available."""
    runner = CliRunner()

    codespace_registry = FakeCodespaceRegistry()
    ctx = context_for_test(codespace_registry=codespace_registry, repo_info=None)

    result = runner.invoke(cli, ["codespace", "setup"], obj=ctx, catch_exceptions=True)

    # Should fall back to "erk-codespace"
    assert "Using codespace name: erk-codespace" in result.output


def test_setup_accepts_explicit_name() -> None:
    """setup command accepts explicit name argument."""
    runner = CliRunner()

    codespace_registry = FakeCodespaceRegistry()
    ctx = context_for_test(codespace_registry=codespace_registry)

    # Will fail at subprocess but should use the explicit name
    result = runner.invoke(
        cli, ["codespace", "setup", "custom-name"], obj=ctx, catch_exceptions=True
    )

    # Should output the creating message with explicit name (not the derived one)
    assert "Creating codespace 'custom-name'" in result.output


def test_setup_passes_repo_option_to_gh_command() -> None:
    """setup command passes --repo option to gh codespace create."""
    runner = CliRunner()

    codespace_registry = FakeCodespaceRegistry()
    ctx = context_for_test(codespace_registry=codespace_registry)

    result = runner.invoke(
        cli,
        ["codespace", "setup", "mybox", "--repo", "owner/repo"],
        obj=ctx,
        catch_exceptions=True,
    )

    # Should output the command with --repo flag
    assert "--repo" in result.output
    assert "owner/repo" in result.output


def test_setup_passes_branch_option_to_gh_command() -> None:
    """setup command passes --branch option to gh codespace create."""
    runner = CliRunner()

    codespace_registry = FakeCodespaceRegistry()
    ctx = context_for_test(codespace_registry=codespace_registry)

    result = runner.invoke(
        cli,
        ["codespace", "setup", "mybox", "--branch", "feature-branch"],
        obj=ctx,
        catch_exceptions=True,
    )

    # Should output the command with --branch flag
    assert "--branch" in result.output
    assert "feature-branch" in result.output
