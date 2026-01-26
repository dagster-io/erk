"""Tests for branch conflict detection in worktree creation."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env


def test_create_detects_branch_already_checked_out() -> None:
    """Test that create detects when branch is already checked out."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Setup: feature-branch is already checked out in an existing worktree
        existing_wt_path = repo_dir / "worktrees" / "existing-feature"
        existing_wt_path.mkdir(parents=True)

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            worktrees={
                env.cwd: [
                    WorktreeInfo(path=env.cwd, branch="main"),
                    WorktreeInfo(path=existing_wt_path, branch="feature-branch"),
                ],
            },
        )
        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli, ["wt", "create", "new-feature", "--from-branch", "feature-branch"], obj=test_ctx
        )

        assert result.exit_code == 1
        assert "already checked out" in result.output
        assert "feature-branch" in result.output


def test_create_blocks_when_staged_changes_present_with_graphite_enabled() -> None:
    """Ensure the command fails fast when staged changes exist and graphite is enabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        from erk.cli.config import LoadedConfig
        from erk.core.repo_discovery import RepoContext

        repo_dir = env.setup_repo_structure()

        # Pass local config directly
        local_config = LoadedConfig.test()

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
            staged_repos={env.cwd},
        )

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
            local_config=local_config,
            repo=repo,
        )

        result = runner.invoke(cli, ["wt", "create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Staged changes detected." in result.output
        assert 'git commit -m "message"' in result.output
        # No need to verify subprocess wasn't called - the error happens before subprocess


def test_create_allows_staged_changes_when_graphite_disabled() -> None:
    """Graphite disabled path should ignore staged changes and continue."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()
        (repo_dir / "config.toml").write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            staged_repos={env.cwd},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(cli, ["wt", "create", "test-feature"], obj=test_ctx)

        assert result.exit_code == 0, result.output
