"""Unit tests for codespace setup command."""

from datetime import datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands.codespace.setup_cmd import DEFAULT_MACHINE_TYPE
from erk.core.context import context_for_test
from erk_shared.gateway.codespace_registry.abc import RegisteredCodespace
from erk_shared.gateway.codespace_registry.fake import FakeCodespaceRegistry
from erk_shared.gateway.github.types import RepoInfo

TEST_REPO_INFO = RepoInfo(owner="testorg", name="testrepo")


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

    This test is limited because the actual gh api subprocess call will fail,
    but we can verify the derived name is used before the subprocess step.
    """
    runner = CliRunner()

    codespace_registry = FakeCodespaceRegistry()
    ctx = context_for_test(
        codespace_registry=codespace_registry,
        repo_info=TEST_REPO_INFO,
    )

    # Will fail at subprocess but should output the derived name
    result = runner.invoke(cli, ["codespace", "setup"], obj=ctx, catch_exceptions=True)

    # The derived name should be "{repo_name}-codespace"
    assert "Using codespace name: testrepo-codespace" in result.output


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
    ctx = context_for_test(codespace_registry=codespace_registry, repo_info=TEST_REPO_INFO)

    # Will fail at subprocess but should use the explicit name
    result = runner.invoke(
        cli, ["codespace", "setup", "custom-name"], obj=ctx, catch_exceptions=True
    )

    # Should output the creating message with explicit name (not the derived one)
    assert "Creating codespace 'custom-name'" in result.output


def test_setup_errors_without_repo_info_or_repo_flag() -> None:
    """setup command errors when no repo_info and no --repo flag provided."""
    runner = CliRunner()

    codespace_registry = FakeCodespaceRegistry()
    ctx = context_for_test(codespace_registry=codespace_registry, repo_info=None)

    result = runner.invoke(cli, ["codespace", "setup", "mybox"], obj=ctx, catch_exceptions=True)

    assert result.exit_code == 1
    assert "No repository specified" in result.output


def test_setup_repo_id_lookup_uses_repo_flag() -> None:
    """setup command uses --repo to look up repo ID when provided.

    The gh api call will fail in tests, but we can verify the error output
    includes the repo flag value, confirming it was used for the API call.
    """
    runner = CliRunner()

    codespace_registry = FakeCodespaceRegistry()
    ctx = context_for_test(codespace_registry=codespace_registry, repo_info=None)

    result = runner.invoke(
        cli,
        ["codespace", "setup", "mybox", "--repo", "owner/repo"],
        obj=ctx,
        catch_exceptions=True,
    )

    # The error from run_with_error_reporting includes the command that failed
    # which should contain the repo path
    assert "repos/owner/repo" in result.output


def test_setup_repo_id_lookup_uses_repo_info() -> None:
    """setup command uses ctx.repo_info to look up repo ID when --repo not provided.

    The gh api call will fail in tests, but we can verify the error output
    includes the repo info, confirming it was used for the API call.
    """
    runner = CliRunner()

    codespace_registry = FakeCodespaceRegistry()
    ctx = context_for_test(codespace_registry=codespace_registry, repo_info=TEST_REPO_INFO)

    result = runner.invoke(cli, ["codespace", "setup", "mybox"], obj=ctx, catch_exceptions=True)

    # The error from run_with_error_reporting includes the command that failed
    # which should contain the derived owner/repo path
    assert "repos/testorg/testrepo" in result.output


def test_setup_default_machine_type_is_premium_linux() -> None:
    """Default machine type constant is premiumLinux."""
    assert DEFAULT_MACHINE_TYPE == "premiumLinux"
