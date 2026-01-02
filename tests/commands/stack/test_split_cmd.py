"""Tests for erk stack split command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason
from erk_shared.git.fake import FakeGit
from tests.test_utils.cli_helpers import assert_cli_error
from tests.test_utils.env_helpers import erk_inmem_env


def test_split_graphite_not_enabled() -> None:
    """Test stack split command requires Graphite to be enabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        # Graphite is NOT enabled - use GraphiteDisabled sentinel
        graphite_disabled = GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED)
        test_ctx = env.build_context(git=git_ops, graphite=graphite_disabled, repo=repo)

        result = runner.invoke(cli, ["stack", "split"], obj=test_ctx, catch_exceptions=False)

        assert_cli_error(
            result,
            1,
            "requires Graphite to be enabled",
            "erk config set use_graphite true",
        )


def test_split_graphite_not_installed() -> None:
    """Test stack split command shows appropriate error when Graphite CLI is not installed."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        git_ops = FakeGit(
            worktrees=env.build_worktrees("main"),
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        # Graphite not installed - use GraphiteDisabled with NOT_INSTALLED reason
        graphite_disabled = GraphiteDisabled(GraphiteDisabledReason.NOT_INSTALLED)
        test_ctx = env.build_context(git=git_ops, graphite=graphite_disabled, repo=repo)

        result = runner.invoke(cli, ["stack", "split"], obj=test_ctx, catch_exceptions=False)

        assert_cli_error(
            result,
            1,
            "requires Graphite to be installed",
            "npm install -g @withgraphite/graphite-cli",
        )
