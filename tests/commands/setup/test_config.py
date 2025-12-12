"""Tests for the config command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.config import LoadedConfig
from erk.core.config_store import GlobalConfig
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.integrations.graphite.fake import FakeGraphite
from tests.test_utils.env_helpers import erk_inmem_env


def test_config_list_displays_global_config() -> None:
    """Test that config list displays global configuration."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo_dir = env.setup_repo_structure()
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Global configuration:" in result.output
        assert "erk_root=" in result.output
        assert "use_graphite=true" in result.output
        assert "show_pr_info=true" in result.output


def test_config_list_displays_repo_config() -> None:
    """Test that config list displays repository configuration."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Pass local config directly instead of creating files
        local_config = LoadedConfig(
            env={"FOO": "bar"},
            post_create_commands=["echo hello"],
            post_create_shell="/bin/bash",
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops,
            local_config=local_config,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Repository configuration:" in result.output
        assert "env.FOO=bar" in result.output
        assert "post_create.shell=/bin/bash" in result.output
        assert "post_create.commands=" in result.output


def test_config_list_handles_missing_repo_config() -> None:
    """Test that config list handles missing repo config gracefully."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo_dir = env.setup_repo_structure()
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Repository configuration:" in result.output


def test_config_list_not_in_git_repo() -> None:
    """Test that config list handles not being in a git repo."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # No .git directory - empty FakeGit means no git repos
        git_ops = FakeGit()

        # Build context manually without env.build_context() to avoid auto-adding git_common_dirs
        global_config = GlobalConfig.test(
            Path("/fake/erks"), use_graphite=False, shell_setup_complete=False
        )

        test_ctx = context_for_test(
            git=git_ops,
            graphite=FakeGraphite(),
            github=FakeGitHub(),
            global_config=global_config,
            script_writer=env.script_writer,
            cwd=env.cwd,
            repo=None,
        )

        result = runner.invoke(cli, ["config", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "not in a git repository" in result.output


def test_config_get_erk_root() -> None:
    """Test getting erk_root config value."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo_dir = env.setup_repo_structure()
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
        )

        result = runner.invoke(cli, ["config", "get", "erk_root"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert str(env.erk_root) in result.output


def test_config_get_use_graphite() -> None:
    """Test getting use_graphite config value."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo_dir = env.setup_repo_structure()
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "use_graphite"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "true" in result.output.strip()


def test_config_get_show_pr_info() -> None:
    """Test getting show_pr_info config value."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        test_ctx = env.build_context(
            git=git_ops,
        )

        result = runner.invoke(cli, ["config", "get", "show_pr_info"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "true" in result.output.strip()


def test_config_get_env_key() -> None:
    """Test getting env.* config value."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Pass local config directly instead of creating files
        local_config = LoadedConfig(
            env={"MY_VAR": "my_value"},
            post_create_commands=[],
            post_create_shell=None,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops,
            local_config=local_config,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "env.MY_VAR"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "my_value" in result.output.strip()


def test_config_get_post_create_shell() -> None:
    """Test getting post_create.shell config value."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Pass local config directly instead of creating files
        local_config = LoadedConfig(
            env={},
            post_create_commands=[],
            post_create_shell="/bin/zsh",
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops,
            local_config=local_config,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "post_create.shell"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "/bin/zsh" in result.output.strip()


def test_config_get_post_create_commands() -> None:
    """Test getting post_create.commands config value."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Pass local config directly instead of creating files
        local_config = LoadedConfig(
            env={},
            post_create_commands=["echo hello", "echo world"],
            post_create_shell=None,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops,
            local_config=local_config,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "post_create.commands"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "echo hello" in result.output
        assert "echo world" in result.output


def test_config_get_env_key_not_found() -> None:
    """Test that getting non-existent env key fails."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Pass empty local config
        local_config = LoadedConfig(
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops,
            local_config=local_config,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "env.NONEXISTENT"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Key not found" in result.output


def test_config_get_invalid_key_format() -> None:
    """Test that invalid key format fails."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo_dir = env.setup_repo_structure()
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "env"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Invalid key" in result.output


def test_config_get_invalid_key() -> None:
    """Test that getting invalid key fails."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "invalid_key"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Invalid key" in result.output


def test_config_key_with_multiple_dots() -> None:
    """Test that keys with multiple dots are handled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "env.FOO.BAR"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Invalid key" in result.output


def test_config_get_post_create_shell_not_found() -> None:
    """Test that getting post_create.shell when not set fails with Ensure error."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Pass local config with no shell set
        local_config = LoadedConfig(
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops,
            local_config=local_config,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "post_create.shell"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "Key not found" in result.output


def test_config_get_post_create_invalid_subkey() -> None:
    """Test that getting invalid post_create subkey fails with Ensure error."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        local_config = LoadedConfig(
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops,
            local_config=local_config,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "post_create.invalid"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "Key not found" in result.output


def test_config_get_post_create_invalid_key_format() -> None:
    """Test that invalid post_create key format fails with Ensure error."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "post_create"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Error:" in result.output
        assert "Invalid key" in result.output


def test_config_list_displays_github_planning() -> None:
    """Test that config list displays github_planning value."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo_dir = env.setup_repo_structure()
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "list"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "github_planning=true" in result.output


def test_config_get_github_planning() -> None:
    """Test getting github_planning config value."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        test_ctx = env.build_context(
            git=git_ops,
        )

        result = runner.invoke(cli, ["config", "get", "github_planning"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "true" in result.output.strip()


def test_config_set_github_planning() -> None:
    """Test setting github_planning config value."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        test_ctx = env.build_context(
            git=git_ops,
        )

        # Set to false
        result = runner.invoke(cli, ["config", "set", "github_planning", "false"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Set github_planning=false" in result.output

        # Verify it was saved to the config store
        saved_config = test_ctx.config_store.load()
        assert saved_config.github_planning is False


def test_config_set_github_planning_invalid_value() -> None:
    """Test that setting github_planning with invalid value fails."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        test_ctx = env.build_context(
            git=git_ops,
        )

        result = runner.invoke(cli, ["config", "set", "github_planning", "invalid"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Invalid boolean value" in result.output
