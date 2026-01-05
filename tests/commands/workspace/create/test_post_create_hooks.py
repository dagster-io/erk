"""Tests for post-create hooks and environment setup in worktree creation."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.config import LoadedConfig
from erk.core.repo_discovery import RepoContext
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


def test_create_runs_post_create_commands() -> None:
    """Test that create runs post-create commands."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Pass local config directly with post_create commands
        local_config = LoadedConfig.test(post_create_commands=["echo hello > test.txt"])

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, local_config=local_config, repo=repo)

        result = runner.invoke(cli, ["wt", "create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Running post-create commands" in result.output


def test_create_sets_env_variables() -> None:
    """Test that create sets environment variables in .env file."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Pass local config directly with env vars
        local_config = LoadedConfig.test(env={"MY_VAR": "my_value"})

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(git=git_ops, local_config=local_config, repo=repo)

        result = runner.invoke(cli, ["wt", "create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        wt_path = repo_dir / "worktrees" / "test-feature"
        env_file = wt_path / ".env"
        env_content = env_file.read_text(encoding="utf-8")
        assert "MY_VAR" in env_content
        assert "WORKTREE_PATH" in env_content
        assert "REPO_ROOT" in env_content


def test_create_no_post_flag_skips_commands() -> None:
    """Test that --no-post flag skips post-create commands."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Create config with post_create commands
        config_toml = repo_dir / "config.toml"
        config_toml.write_text(
            '[post_create]\ncommands = ["echo hello"]\n',
            encoding="utf-8",
        )

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["wt", "create", "test-feature", "--no-post"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "Running post-create commands" not in result.output
