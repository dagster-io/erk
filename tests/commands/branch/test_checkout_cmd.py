"""Tests for erk br co (branch checkout) command."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env


def test_checkout_succeeds_when_graphite_not_enabled() -> None:
    """Test branch checkout works when Graphite is not enabled (graceful degradation)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_wt = repo_dir / "worktrees" / "feature-branch"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-branch", is_root=False),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_wt: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        # Graphite is NOT enabled - use GraphiteDisabled sentinel
        graphite_disabled = GraphiteDisabled(GraphiteDisabledReason.CONFIG_DISABLED)
        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_disabled,
            repo=repo,
            existing_paths={feature_wt},
        )

        result = runner.invoke(
            cli, ["br", "co", "feature-branch", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Should succeed with graceful degradation (no Graphite tracking prompt)
        assert result.exit_code == 0, f"Expected success, got: {result.output}"
        # Should not show Graphite error
        assert "requires Graphite" not in result.output


def test_checkout_succeeds_when_graphite_not_installed() -> None:
    """Test branch checkout works when Graphite CLI is not installed (graceful degradation)."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        feature_wt = repo_dir / "worktrees" / "feature-branch"

        git_ops = FakeGit(
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main", is_root=True),
                    WorktreeInfo(path=feature_wt, branch="feature-branch", is_root=False),
                ]
            },
            current_branches={env.cwd: "main"},
            git_common_dirs={env.cwd: env.git_dir, feature_wt: env.git_dir},
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=repo_dir,
            worktrees_dir=repo_dir / "worktrees",
        )

        # Graphite not installed - use GraphiteDisabled with NOT_INSTALLED reason
        graphite_disabled = GraphiteDisabled(GraphiteDisabledReason.NOT_INSTALLED)
        test_ctx = env.build_context(
            git=git_ops,
            graphite=graphite_disabled,
            repo=repo,
            existing_paths={feature_wt},
        )

        result = runner.invoke(
            cli, ["br", "co", "feature-branch", "--script"], obj=test_ctx, catch_exceptions=False
        )

        # Should succeed with graceful degradation (no Graphite tracking prompt)
        assert result.exit_code == 0, f"Expected success, got: {result.output}"
        # Should not show Graphite error
        assert "requires Graphite" not in result.output
