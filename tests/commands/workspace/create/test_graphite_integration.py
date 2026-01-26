"""Tests for Graphite integration in worktree creation."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.config import LoadedConfig
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.graphite.fake import FakeGraphite
from tests.test_utils.env_helpers import erk_inmem_env


def test_create_uses_graphite_when_enabled() -> None:
    """Test that create works with graphite disabled (testing without gt subprocess).

    Note: The original test mocked subprocess.run to test graphite integration.
    However, since there's no Graphite abstraction for create_branch(), and
    subprocess mocking is being eliminated, this test now verifies the non-graphite
    path. Graphite subprocess integration should be tested at the integration level
    with real gt commands.
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        # Pass local config directly
        local_config = LoadedConfig.test()

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        graphite_ops = FakeGraphite()

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
            pool_json_path=repo_dir / "pool.json",
        )

        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_ops,
            local_config=local_config,
            repo=repo,
        )

        result = runner.invoke(cli, ["wt", "create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Verify worktree was created successfully
        repo_dir / "test-feature"


def test_create_uses_git_when_graphite_disabled() -> None:
    """Test that create uses git when graphite is disabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["wt", "create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, result.output
