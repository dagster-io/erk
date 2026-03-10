"""Unit tests for codespace connect command."""

from datetime import datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk_shared.context.types import LoadedConfig
from erk_shared.gateway.codespace_registry.abc import RegisteredCodespace
from tests.fakes.gateway.codespace import FakeCodespace
from tests.fakes.gateway.codespace_registry import FakeCodespaceRegistry
from tests.fakes.gateway.git import FakeGit
from tests.test_utils.test_context import context_for_test


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
    fake_codespace = FakeCodespace(
        run_exit_code=0, repo_id=12345, created_codespace_name="fake-gh-name"
    )
    ctx = context_for_test(codespace_registry=codespace_registry, codespace=fake_codespace)

    result = runner.invoke(cli, ["codespace", "connect"], obj=ctx)

    # FakeCodespace.exec_ssh_interactive raises SystemExit(0), which CliRunner catches
    assert result.exit_code == 0

    # Verify exec_ssh_interactive was called with correct arguments
    assert fake_codespace.exec_called
    assert fake_codespace.last_call is not None
    assert fake_codespace.last_call.gh_name == "user-mybox-abc123"
    assert fake_codespace.last_call.interactive is True
    # Verify the command includes Claude setup (no tmux by default)
    assert "claude" in fake_codespace.last_call.remote_command
    assert "git pull" in fake_codespace.last_call.remote_command
    assert "tmux" not in fake_codespace.last_call.remote_command


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
    fake_codespace = FakeCodespace(
        run_exit_code=0, repo_id=12345, created_codespace_name="fake-gh-name"
    )
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
    fake_codespace = FakeCodespace(
        run_exit_code=0, repo_id=12345, created_codespace_name="fake-gh-name"
    )
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
    assert "tmux" not in remote_command


def test_connect_with_env_injects_export() -> None:
    """connect --env KEY=VALUE injects export into the remote command."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc123", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    fake_codespace = FakeCodespace(
        run_exit_code=0, repo_id=12345, created_codespace_name="fake-gh-name"
    )
    ctx = context_for_test(codespace_registry=codespace_registry, codespace=fake_codespace)

    result = runner.invoke(
        cli, ["codespace", "connect", "--env", "ERK_PLAN_BACKEND=draft_pr"], obj=ctx
    )

    assert result.exit_code == 0
    assert fake_codespace.last_call is not None
    assert "export ERK_PLAN_BACKEND=draft_pr" in fake_codespace.last_call.remote_command
    assert "git pull" in fake_codespace.last_call.remote_command


def test_connect_with_multiple_env_vars() -> None:
    """connect with multiple --env flags injects all exports."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc123", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    fake_codespace = FakeCodespace(
        run_exit_code=0, repo_id=12345, created_codespace_name="fake-gh-name"
    )
    ctx = context_for_test(codespace_registry=codespace_registry, codespace=fake_codespace)

    result = runner.invoke(
        cli,
        ["codespace", "connect", "--env", "FOO=bar", "--env", "BAZ=qux"],
        obj=ctx,
    )

    assert result.exit_code == 0
    assert fake_codespace.last_call is not None
    remote_command = fake_codespace.last_call.remote_command
    assert "export FOO=bar BAZ=qux &&" in remote_command


def test_connect_env_with_shell_flag() -> None:
    """connect --env with --shell injects env vars into shell command."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc123", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    fake_codespace = FakeCodespace(
        run_exit_code=0, repo_id=12345, created_codespace_name="fake-gh-name"
    )
    ctx = context_for_test(codespace_registry=codespace_registry, codespace=fake_codespace)

    result = runner.invoke(cli, ["codespace", "connect", "--shell", "--env", "FOO=bar"], obj=ctx)

    assert result.exit_code == 0
    assert fake_codespace.last_call is not None
    remote_command = fake_codespace.last_call.remote_command
    assert "export FOO=bar" in remote_command
    assert "exec bash -l" in remote_command


def test_connect_env_invalid_format_errors() -> None:
    """connect --env with invalid format (no =) shows error."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc123", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    fake_codespace = FakeCodespace(
        run_exit_code=0, repo_id=12345, created_codespace_name="fake-gh-name"
    )
    ctx = context_for_test(codespace_registry=codespace_registry, codespace=fake_codespace)

    result = runner.invoke(cli, ["codespace", "connect", "--env", "INVALID"], obj=ctx)

    assert result.exit_code == 1
    assert "Invalid --env format" in result.output


def test_connect_uses_config_codespace_name() -> None:
    """connect uses repo config codespace name when no CLI name provided."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="config-box", gh_name="user-configbox-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs])
    fake_codespace = FakeCodespace(
        run_exit_code=0, repo_id=12345, created_codespace_name="fake-gh-name"
    )
    local_config = LoadedConfig.test(codespace_name="config-box")
    ctx = context_for_test(
        codespace_registry=codespace_registry,
        codespace=fake_codespace,
        local_config=local_config,
    )

    result = runner.invoke(cli, ["codespace", "connect"], obj=ctx)

    assert result.exit_code == 0
    assert fake_codespace.exec_called
    assert fake_codespace.last_call is not None
    assert fake_codespace.last_call.gh_name == "user-configbox-abc"


def test_connect_with_working_directory_prepends_cd() -> None:
    """connect prepends cd to remote command when working_directory is set."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc123", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    fake_codespace = FakeCodespace(
        run_exit_code=0, repo_id=12345, created_codespace_name="fake-gh-name"
    )
    local_config = LoadedConfig.test(codespace_working_directory="/workspaces/dagster-compass")
    ctx = context_for_test(
        codespace_registry=codespace_registry,
        codespace=fake_codespace,
        local_config=local_config,
    )

    result = runner.invoke(cli, ["codespace", "connect"], obj=ctx)

    assert result.exit_code == 0
    assert fake_codespace.last_call is not None
    assert "cd /workspaces/dagster-compass" in fake_codespace.last_call.remote_command
    assert "git pull" in fake_codespace.last_call.remote_command


def test_connect_with_working_directory_and_shell_flag() -> None:
    """connect --shell with working_directory prepends cd to shell command."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc123", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    fake_codespace = FakeCodespace(
        run_exit_code=0, repo_id=12345, created_codespace_name="fake-gh-name"
    )
    local_config = LoadedConfig.test(codespace_working_directory="/workspaces/repo")
    ctx = context_for_test(
        codespace_registry=codespace_registry,
        codespace=fake_codespace,
        local_config=local_config,
    )

    result = runner.invoke(cli, ["codespace", "connect", "--shell"], obj=ctx)

    assert result.exit_code == 0
    assert fake_codespace.last_call is not None
    remote_command = fake_codespace.last_call.remote_command
    assert "cd /workspaces/repo" in remote_command
    assert "exec bash -l" in remote_command


def _make_repo_context(root: Path) -> RepoContext:
    """Create a minimal RepoContext for testing."""
    repo_dir = root / ".erk"
    return RepoContext(
        root=root,
        repo_name=root.name,
        repo_dir=repo_dir,
        worktrees_dir=repo_dir / "worktrees",
        pool_json_path=repo_dir / "pool.json",
    )


def test_connect_checks_out_local_branch() -> None:
    """connect injects git fetch + checkout for the local branch into the remote command."""
    runner = CliRunner()
    repo_root = Path("/test/repo")

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc123", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    fake_codespace = FakeCodespace(
        run_exit_code=0, repo_id=12345, created_codespace_name="fake-gh-name"
    )
    git = FakeGit(current_branches={repo_root: "feature-x"})
    repo = _make_repo_context(repo_root)
    ctx = context_for_test(
        codespace_registry=codespace_registry,
        codespace=fake_codespace,
        git=git,
        repo=repo,
    )

    result = runner.invoke(cli, ["codespace", "connect"], obj=ctx)

    assert result.exit_code == 0
    assert fake_codespace.last_call is not None
    remote_command = fake_codespace.last_call.remote_command
    assert "git fetch origin feature-x && git checkout feature-x" in remote_command
    assert "git pull" in remote_command


def test_connect_skips_checkout_when_detached_head() -> None:
    """connect skips branch checkout when local HEAD is detached."""
    runner = CliRunner()
    repo_root = Path("/test/repo")

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc123", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    fake_codespace = FakeCodespace(
        run_exit_code=0, repo_id=12345, created_codespace_name="fake-gh-name"
    )
    git = FakeGit(current_branches={repo_root: None})
    repo = _make_repo_context(repo_root)
    ctx = context_for_test(
        codespace_registry=codespace_registry,
        codespace=fake_codespace,
        git=git,
        repo=repo,
    )

    result = runner.invoke(cli, ["codespace", "connect"], obj=ctx)

    assert result.exit_code == 0
    assert fake_codespace.last_call is not None
    remote_command = fake_codespace.last_call.remote_command
    assert "git fetch" not in remote_command
    assert "git checkout" not in remote_command
    assert "git pull" in remote_command


def test_connect_shell_checks_out_local_branch() -> None:
    """connect --shell injects branch checkout before dropping into shell."""
    runner = CliRunner()
    repo_root = Path("/test/repo")

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc123", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    fake_codespace = FakeCodespace(
        run_exit_code=0, repo_id=12345, created_codespace_name="fake-gh-name"
    )
    git = FakeGit(current_branches={repo_root: "feature-x"})
    repo = _make_repo_context(repo_root)
    ctx = context_for_test(
        codespace_registry=codespace_registry,
        codespace=fake_codespace,
        git=git,
        repo=repo,
    )

    result = runner.invoke(cli, ["codespace", "connect", "--shell"], obj=ctx)

    assert result.exit_code == 0
    assert fake_codespace.last_call is not None
    remote_command = fake_codespace.last_call.remote_command
    assert "git fetch origin feature-x && git checkout feature-x" in remote_command
    assert "exec bash -l" in remote_command


def test_connect_with_branch_option_overrides_local_branch() -> None:
    """connect --branch master uses the specified branch instead of the local branch."""
    runner = CliRunner()
    repo_root = Path("/test/repo")

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc123", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    fake_codespace = FakeCodespace(
        run_exit_code=0, repo_id=12345, created_codespace_name="fake-gh-name"
    )
    git = FakeGit(current_branches={repo_root: "feature-x"})
    repo = _make_repo_context(repo_root)
    ctx = context_for_test(
        codespace_registry=codespace_registry,
        codespace=fake_codespace,
        git=git,
        repo=repo,
    )

    result = runner.invoke(cli, ["codespace", "connect", "--branch", "master"], obj=ctx)

    assert result.exit_code == 0
    assert fake_codespace.last_call is not None
    remote_command = fake_codespace.last_call.remote_command
    # Should use master, not the local branch feature-x
    assert "git fetch origin master && git checkout master" in remote_command
    assert "feature-x" not in remote_command


def test_connect_with_branch_option_and_shell() -> None:
    """connect --branch with --shell uses the specified branch in shell mode."""
    runner = CliRunner()
    repo_root = Path("/test/repo")

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc123", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    fake_codespace = FakeCodespace(
        run_exit_code=0, repo_id=12345, created_codespace_name="fake-gh-name"
    )
    git = FakeGit(current_branches={repo_root: "feature-x"})
    repo = _make_repo_context(repo_root)
    ctx = context_for_test(
        codespace_registry=codespace_registry,
        codespace=fake_codespace,
        git=git,
        repo=repo,
    )

    result = runner.invoke(cli, ["codespace", "connect", "--shell", "--branch", "master"], obj=ctx)

    assert result.exit_code == 0
    assert fake_codespace.last_call is not None
    remote_command = fake_codespace.last_call.remote_command
    assert "git fetch origin master && git checkout master" in remote_command
    assert "exec bash -l" in remote_command
    assert "feature-x" not in remote_command


def test_connect_with_branch_option_no_repo() -> None:
    """connect --branch works even when not in a git repo."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc123", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")
    fake_codespace = FakeCodespace(
        run_exit_code=0, repo_id=12345, created_codespace_name="fake-gh-name"
    )
    ctx = context_for_test(
        codespace_registry=codespace_registry,
        codespace=fake_codespace,
    )

    result = runner.invoke(cli, ["codespace", "connect", "--branch", "master"], obj=ctx)

    assert result.exit_code == 0
    assert fake_codespace.last_call is not None
    remote_command = fake_codespace.last_call.remote_command
    assert "git fetch origin master && git checkout master" in remote_command
