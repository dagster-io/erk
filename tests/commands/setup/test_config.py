"""Tests for the config command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.config import LoadedConfig
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


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
            pool_json_path=repo_dir / "pool.json",
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


def test_config_list_displays_repo_config() -> None:
    """Test that config list displays repository configuration."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Pass local config directly instead of creating files
        local_config = LoadedConfig.test(
            env={"FOO": "bar"},
            post_create_commands=["echo hello"],
            post_create_shell="/bin/bash",
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
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
            pool_json_path=repo_dir / "pool.json",
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
            pool_json_path=repo_dir / "pool.json",
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
            pool_json_path=repo_dir / "pool.json",
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


def test_config_get_env_key() -> None:
    """Test getting env.* config value."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Pass local config directly instead of creating files
        local_config = LoadedConfig.test(env={"MY_VAR": "my_value"})

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
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
        local_config = LoadedConfig.test(post_create_shell="/bin/zsh")

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
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
        local_config = LoadedConfig.test(post_create_commands=["echo hello", "echo world"])

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
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
        local_config = LoadedConfig.test()

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
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
            pool_json_path=repo_dir / "pool.json",
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
            pool_json_path=repo_dir / "pool.json",
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
            pool_json_path=repo_dir / "pool.json",
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
        local_config = LoadedConfig.test()

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
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
        local_config = LoadedConfig.test()

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
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
            pool_json_path=repo_dir / "pool.json",
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
            pool_json_path=repo_dir / "pool.json",
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
        saved_config = test_ctx.erk_installation.load_config()
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


def test_config_get_pool_max_slots_configured() -> None:
    """Test getting pool.max_slots when it's configured."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        local_config = LoadedConfig.test(pool_size=8)

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            local_config=local_config,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "pool.max_slots"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "8" in result.output.strip()


def test_config_get_pool_max_slots_default() -> None:
    """Test getting pool.max_slots when it's not configured (shows default)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        local_config = LoadedConfig.test()  # No pool_size set

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            local_config=local_config,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "get", "pool.max_slots"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "4 (default)" in result.output.strip()


def test_config_set_pool_max_slots() -> None:
    """Test setting pool.max_slots writes to config file."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "set", "pool.max_slots", "6"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Set pool.max_slots=6" in result.output

        # Verify config file was created
        config_path = env.cwd / ".erk" / "config.toml"
        assert config_path.exists()
        content = config_path.read_text(encoding="utf-8")
        assert "[pool]" in content
        assert "max_slots = 6" in content


def test_config_set_pool_max_slots_invalid_value() -> None:
    """Test that setting pool.max_slots with invalid value fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "set", "pool.max_slots", "invalid"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Invalid value" in result.output


def test_config_set_pool_max_slots_zero() -> None:
    """Test that setting pool.max_slots to zero fails."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "set", "pool.max_slots", "0"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Invalid value" in result.output


def test_config_list_shows_pool_max_slots() -> None:
    """Test that config list displays pool.max_slots when configured."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        local_config = LoadedConfig.test(pool_size=6)

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
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
        assert "pool.max_slots=6" in result.output


def test_config_list_shows_pool_max_slots_default() -> None:
    """Test that config list displays pool.max_slots default when not configured."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # No pool_size configured - should show default
        local_config = LoadedConfig.test()

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
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
        assert "pool.max_slots=4 (default)" in result.output


# --local flag tests


def test_config_set_local_writes_to_local_config() -> None:
    """Test that --local writes to config.local.toml, not config.toml."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(
            cli, ["config", "set", "--local", "pool.max_slots", "8"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        assert "Set pool.max_slots=8 (local)" in result.output

        # Verify config.local.toml was created
        local_config_path = env.cwd / ".erk" / "config.local.toml"
        assert local_config_path.exists()
        content = local_config_path.read_text(encoding="utf-8")
        assert "[pool]" in content
        assert "max_slots = 8" in content

        # Verify config.toml was NOT created
        config_path = env.cwd / ".erk" / "config.toml"
        assert not config_path.exists()


def test_config_set_local_short_flag() -> None:
    """Test that -l short flag works the same as --local."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "set", "-l", "pool.max_slots", "5"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Set pool.max_slots=5 (local)" in result.output

        # Verify config.local.toml was created
        local_config_path = env.cwd / ".erk" / "config.local.toml"
        assert local_config_path.exists()


def test_config_set_local_global_key_fails() -> None:
    """Test that --local with global key fails with error."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        test_ctx = env.build_context(
            git=git_ops,
        )

        result = runner.invoke(
            cli, ["config", "set", "--local", "use_graphite", "false"], obj=test_ctx
        )

        assert result.exit_code == 1
        assert "cannot be written to local or repo config" in result.output


def test_config_set_local_trunk_branch_fails() -> None:
    """Test that --local with trunk-branch fails with error."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(
            cli, ["config", "set", "--local", "trunk-branch", "main"], obj=test_ctx
        )

        assert result.exit_code == 1
        assert "trunk-branch lives in pyproject.toml" in result.output


def test_config_set_local_env_var() -> None:
    """Test setting env.<name> with --local flag."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(
            cli, ["config", "set", "--local", "env.MY_SECRET", "secret_value"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        assert "Set env.MY_SECRET=secret_value (local)" in result.output

        # Verify config.local.toml contains the env var
        local_config_path = env.cwd / ".erk" / "config.local.toml"
        content = local_config_path.read_text(encoding="utf-8")
        assert "[env]" in content
        assert 'MY_SECRET = "secret_value"' in content


def test_config_set_local_post_create_shell() -> None:
    """Test setting post_create.shell with --local flag."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(
            cli, ["config", "set", "--local", "post_create.shell", "/bin/zsh"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        assert "Set post_create.shell=/bin/zsh (local)" in result.output

        # Verify config.local.toml contains the setting
        local_config_path = env.cwd / ".erk" / "config.local.toml"
        content = local_config_path.read_text(encoding="utf-8")
        assert "[post_create]" in content
        assert 'shell = "/bin/zsh"' in content


def test_config_set_local_post_create_commands() -> None:
    """Test setting post_create.commands with --local flag."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(
            cli,
            ["config", "set", "--local", "post_create.commands", "echo hello, echo world"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, result.output
        assert "(local)" in result.output

        # Verify config.local.toml contains the commands
        local_config_path = env.cwd / ".erk" / "config.local.toml"
        content = local_config_path.read_text(encoding="utf-8")
        assert "[post_create]" in content
        assert "commands" in content


def test_config_set_local_plans_repo() -> None:
    """Test setting plans.repo with --local flag."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(
            cli, ["config", "set", "--local", "plans.repo", "myorg/plans"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        assert "Set plans.repo=myorg/plans (local)" in result.output

        # Verify config.local.toml contains the setting
        local_config_path = env.cwd / ".erk" / "config.local.toml"
        content = local_config_path.read_text(encoding="utf-8")
        assert "[plans]" in content
        assert 'repo = "myorg/plans"' in content


def test_config_set_without_local_writes_to_config_toml() -> None:
    """Test that without --local flag, writes go to config.toml."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(
            cli, ["config", "set", "env.PUBLIC_VAR", "public_value"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        # Should NOT have "(local)" suffix
        assert "(local)" not in result.output
        assert "Set env.PUBLIC_VAR=public_value" in result.output

        # Verify config.toml was created (not config.local.toml)
        config_path = env.cwd / ".erk" / "config.toml"
        assert config_path.exists()
        content = config_path.read_text(encoding="utf-8")
        assert "[env]" in content
        assert 'PUBLIC_VAR = "public_value"' in content

        # Verify config.local.toml was NOT created
        local_config_path = env.cwd / ".erk" / "config.local.toml"
        assert not local_config_path.exists()


def test_config_set_local_pool_checkout_shell() -> None:
    """Test setting pool.checkout.shell with --local flag."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(
            cli,
            ["config", "set", "--local", "pool.checkout.shell", "/bin/bash"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, result.output
        assert "Set pool.checkout.shell=/bin/bash (local)" in result.output

        # Verify config.local.toml contains the setting
        local_config_path = env.cwd / ".erk" / "config.local.toml"
        content = local_config_path.read_text(encoding="utf-8")
        assert "[pool.checkout]" in content or "[pool]\n" in content
        assert 'shell = "/bin/bash"' in content


def test_config_set_local_pool_checkout_commands() -> None:
    """Test setting pool.checkout.commands with --local flag."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(
            cli,
            ["config", "set", "--local", "pool.checkout.commands", "source .venv/bin/activate"],
            obj=test_ctx,
        )

        assert result.exit_code == 0, result.output
        assert "(local)" in result.output

        # Verify config.local.toml contains the commands
        local_config_path = env.cwd / ".erk" / "config.local.toml"
        content = local_config_path.read_text(encoding="utf-8")
        assert "commands" in content


# Three-level config override tests


def test_config_set_repo_flag_writes_to_config_toml() -> None:
    """Test that --repo flag writes to config.toml (repo level)."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(
            cli, ["config", "set", "--repo", "pool.max_slots", "10"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        assert "Set pool.max_slots=10 (repo)" in result.output

        # Verify config.toml was created (not config.local.toml)
        config_path = env.cwd / ".erk" / "config.toml"
        assert config_path.exists()
        content = config_path.read_text(encoding="utf-8")
        assert "max_slots = 10" in content

        # Verify config.local.toml was NOT created
        local_config_path = env.cwd / ".erk" / "config.local.toml"
        assert not local_config_path.exists()


def test_config_set_repo_flag_short_form() -> None:
    """Test that -r short flag works the same as --repo."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(cli, ["config", "set", "-r", "pool.max_slots", "5"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Set pool.max_slots=5 (repo)" in result.output


def test_config_set_local_and_repo_flags_mutually_exclusive() -> None:
    """Test that --local and --repo flags cannot be used together."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(
            cli, ["config", "set", "--local", "--repo", "pool.max_slots", "5"], obj=test_ctx
        )

        assert result.exit_code == 1
        assert "Cannot use both --local and --repo flags" in result.output


def test_config_set_overridable_global_key_with_local_flag() -> None:
    """Test setting an overridable global key with --local flag."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(
            cli, ["config", "set", "--local", "prompt_learn_on_land", "false"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        assert "Set prompt_learn_on_land=false (local)" in result.output

        # Verify config.local.toml contains the setting
        local_config_path = env.cwd / ".erk" / "config.local.toml"
        content = local_config_path.read_text(encoding="utf-8")
        assert "prompt_learn_on_land = false" in content


def test_config_set_overridable_global_key_with_repo_flag() -> None:
    """Test setting an overridable global key with --repo flag."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(
            cli, ["config", "set", "--repo", "prompt_learn_on_land", "true"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output
        assert "Set prompt_learn_on_land=true (repo)" in result.output

        # Verify config.toml contains the setting
        config_path = env.cwd / ".erk" / "config.toml"
        content = config_path.read_text(encoding="utf-8")
        assert "prompt_learn_on_land = true" in content


def test_config_set_non_overridable_global_key_with_local_flag_fails() -> None:
    """Test that non-overridable global keys cannot be set with --local flag."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        test_ctx = env.build_context(
            git=git_ops,
        )

        result = runner.invoke(
            cli, ["config", "set", "--local", "erk_root", "/some/path"], obj=test_ctx
        )

        assert result.exit_code == 1
        assert "cannot be written to local or repo config" in result.output


def test_config_set_non_overridable_global_key_with_repo_flag_fails() -> None:
    """Test that non-overridable global keys cannot be set with --repo flag."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        test_ctx = env.build_context(
            git=git_ops,
        )

        result = runner.invoke(
            cli, ["config", "set", "--repo", "use_graphite", "false"], obj=test_ctx
        )

        assert result.exit_code == 1
        assert "cannot be written to local or repo config" in result.output


def test_config_list_shows_source_annotation_for_local_override() -> None:
    """Test that config list shows (local) annotation for locally overridden keys."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create config.local.toml with prompt_learn_on_land
        local_config_dir = env.cwd / ".erk"
        local_config_dir.mkdir(parents=True, exist_ok=True)
        local_config_path = local_config_dir / "config.local.toml"
        local_config_path.write_text("prompt_learn_on_land = false\n", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Pass local config directly
        local_config = LoadedConfig.test(prompt_learn_on_land=False)

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
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
        assert "prompt_learn_on_land=false (local)" in result.output


def test_config_list_shows_source_annotation_for_repo_override() -> None:
    """Test that config list shows (repo) annotation for repo-level overridden keys."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create config.toml with prompt_learn_on_land (repo level)
        repo_config_dir = env.cwd / ".erk"
        repo_config_dir.mkdir(parents=True, exist_ok=True)
        repo_config_path = repo_config_dir / "config.toml"
        repo_config_path.write_text("prompt_learn_on_land = true\n", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        # Pass local config directly (this is the merged repo+local config)
        local_config = LoadedConfig.test(prompt_learn_on_land=True)

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
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
        assert "prompt_learn_on_land=true (repo)" in result.output


def test_config_list_shows_pool_source_annotation() -> None:
    """Test that config list shows (local) annotation for pool.max_slots."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create config.local.toml with pool.max_slots
        local_config_dir = env.cwd / ".erk"
        local_config_dir.mkdir(parents=True, exist_ok=True)
        local_config_path = local_config_dir / "config.local.toml"
        local_config_path.write_text("[pool]\nmax_slots = 12\n", encoding="utf-8")

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        local_config = LoadedConfig.test(pool_size=12)

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
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
        assert "pool.max_slots=12 (local)" in result.output


def test_config_set_trunk_branch_rejects_repo_flag() -> None:
    """Test that trunk-branch rejects --repo flag."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            repo=repo,
            script_writer=env.script_writer,
            cwd=env.cwd,
        )

        result = runner.invoke(
            cli, ["config", "set", "--repo", "trunk-branch", "main"], obj=test_ctx
        )

        assert result.exit_code == 1
        assert "trunk-branch lives in pyproject.toml" in result.output
