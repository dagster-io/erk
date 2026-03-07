"""Unit tests for codespace setup command."""

from datetime import datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands.codespace.setup_cmd import DEFAULT_MACHINE_TYPE
from erk.core.context import context_for_test
from erk_shared.gateway.codespace.fake import FakeCodespace
from erk_shared.gateway.codespace_registry.abc import RegisteredCodespace
from erk_shared.gateway.codespace_registry.fake import FakeCodespaceRegistry
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
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


def test_setup_derives_name_from_repo_info(tmp_path: Path) -> None:
    """setup command derives codespace name from repo_info if not provided."""
    runner = CliRunner()

    fake_codespace = FakeCodespace()
    codespace_registry = FakeCodespaceRegistry()
    erk_installation = FakeErkInstallation(root_path=tmp_path / ".erk")
    ctx = context_for_test(
        codespace=fake_codespace,
        codespace_registry=codespace_registry,
        erk_installation=erk_installation,
        repo_info=TEST_REPO_INFO,
    )

    result = runner.invoke(cli, ["codespace", "setup"], obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert "Using codespace name: testrepo-codespace" in result.output
    assert "Setup complete!" in result.output


def test_setup_uses_default_name_without_repo_info(tmp_path: Path) -> None:
    """setup command uses default name when no repo_info available."""
    runner = CliRunner()

    fake_codespace = FakeCodespace()
    codespace_registry = FakeCodespaceRegistry()
    erk_installation = FakeErkInstallation(root_path=tmp_path / ".erk")
    ctx = context_for_test(
        codespace=fake_codespace,
        codespace_registry=codespace_registry,
        erk_installation=erk_installation,
        repo_info=None,
    )

    # No repo info → error at _resolve_owner_repo
    result = runner.invoke(cli, ["codespace", "setup"], obj=ctx, catch_exceptions=True)

    assert "Using codespace name: erk-codespace" in result.output
    assert result.exit_code == 1
    assert "No repository specified" in result.output


def test_setup_accepts_explicit_name(tmp_path: Path) -> None:
    """setup command accepts explicit name argument and creates codespace."""
    runner = CliRunner()

    fake_codespace = FakeCodespace(created_codespace_name="gh-custom-abc")
    codespace_registry = FakeCodespaceRegistry()
    erk_installation = FakeErkInstallation(root_path=tmp_path / ".erk")
    ctx = context_for_test(
        codespace=fake_codespace,
        codespace_registry=codespace_registry,
        erk_installation=erk_installation,
        repo_info=TEST_REPO_INFO,
    )

    result = runner.invoke(
        cli, ["codespace", "setup", "custom-name"], obj=ctx, catch_exceptions=False
    )

    assert result.exit_code == 0
    assert "Creating codespace 'custom-name'" in result.output
    assert "Setup complete!" in result.output


def test_setup_errors_without_repo_info_or_repo_flag() -> None:
    """setup command errors when no repo_info and no --repo flag provided."""
    runner = CliRunner()

    codespace_registry = FakeCodespaceRegistry()
    ctx = context_for_test(codespace_registry=codespace_registry, repo_info=None)

    result = runner.invoke(cli, ["codespace", "setup", "mybox"], obj=ctx, catch_exceptions=True)

    assert result.exit_code == 1
    assert "No repository specified" in result.output


def test_setup_repo_id_lookup_uses_repo_flag(tmp_path: Path) -> None:
    """setup command uses --repo flag for repo ID lookup."""
    runner = CliRunner()

    fake_codespace = FakeCodespace(repo_id=99999)
    codespace_registry = FakeCodespaceRegistry()
    erk_installation = FakeErkInstallation(root_path=tmp_path / ".erk")
    ctx = context_for_test(
        codespace=fake_codespace,
        codespace_registry=codespace_registry,
        erk_installation=erk_installation,
        repo_info=None,
    )

    result = runner.invoke(
        cli,
        ["codespace", "setup", "mybox", "--repo", "owner/repo"],
        obj=ctx,
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert fake_codespace.get_repo_id_calls == ["owner/repo"]


def test_setup_repo_id_lookup_uses_repo_info(tmp_path: Path) -> None:
    """setup command uses ctx.repo_info for repo ID lookup when --repo not provided."""
    runner = CliRunner()

    fake_codespace = FakeCodespace(repo_id=42)
    codespace_registry = FakeCodespaceRegistry()
    erk_installation = FakeErkInstallation(root_path=tmp_path / ".erk")
    ctx = context_for_test(
        codespace=fake_codespace,
        codespace_registry=codespace_registry,
        erk_installation=erk_installation,
        repo_info=TEST_REPO_INFO,
    )

    result = runner.invoke(cli, ["codespace", "setup", "mybox"], obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert fake_codespace.get_repo_id_calls == ["testorg/testrepo"]


def test_setup_default_machine_type_is_premium_linux() -> None:
    """Default machine type constant is premiumLinux."""
    assert DEFAULT_MACHINE_TYPE == "premiumLinux"


def test_setup_creates_codespace_with_correct_params(tmp_path: Path) -> None:
    """setup command passes correct parameters to create_codespace."""
    runner = CliRunner()

    fake_codespace = FakeCodespace(repo_id=12345, created_codespace_name="gh-mybox-abc")
    codespace_registry = FakeCodespaceRegistry()
    erk_installation = FakeErkInstallation(root_path=tmp_path / ".erk")
    ctx = context_for_test(
        codespace=fake_codespace,
        codespace_registry=codespace_registry,
        erk_installation=erk_installation,
        repo_info=TEST_REPO_INFO,
    )

    result = runner.invoke(
        cli,
        ["codespace", "setup", "mybox", "--branch", "main", "--machine", "basicLinux"],
        obj=ctx,
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert len(fake_codespace.create_codespace_calls) == 1
    call = fake_codespace.create_codespace_calls[0]
    assert call["repo_id"] == 12345
    assert call["machine"] == "basicLinux"
    assert call["display_name"] == "mybox"
    assert call["branch"] == "main"


def test_setup_calls_ssh_login(tmp_path: Path) -> None:
    """setup command runs SSH login command after creating codespace."""
    runner = CliRunner()

    fake_codespace = FakeCodespace(created_codespace_name="gh-mybox-abc")
    codespace_registry = FakeCodespaceRegistry()
    erk_installation = FakeErkInstallation(root_path=tmp_path / ".erk")
    ctx = context_for_test(
        codespace=fake_codespace,
        codespace_registry=codespace_registry,
        erk_installation=erk_installation,
        repo_info=TEST_REPO_INFO,
    )

    result = runner.invoke(cli, ["codespace", "setup", "mybox"], obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert len(fake_codespace.ssh_calls) == 1
    ssh_call = fake_codespace.ssh_calls[0]
    assert ssh_call.gh_name == "gh-mybox-abc"
    assert ssh_call.remote_command == "claude login"
    assert ssh_call.interactive is False


def test_setup_shows_retry_hint_on_login_failure(tmp_path: Path) -> None:
    """setup command shows retry hint when SSH login returns non-zero exit code."""
    runner = CliRunner()

    fake_codespace = FakeCodespace(
        run_exit_code=1,
        created_codespace_name="gh-mybox-abc",
    )
    codespace_registry = FakeCodespaceRegistry()
    erk_installation = FakeErkInstallation(root_path=tmp_path / ".erk")
    ctx = context_for_test(
        codespace=fake_codespace,
        codespace_registry=codespace_registry,
        erk_installation=erk_installation,
        repo_info=TEST_REPO_INFO,
    )

    result = runner.invoke(cli, ["codespace", "setup", "mybox"], obj=ctx, catch_exceptions=False)

    assert result.exit_code == 0
    assert "Claude login may have failed or was cancelled" in result.output
    assert "gh codespace ssh -c gh-mybox-abc" in result.output
