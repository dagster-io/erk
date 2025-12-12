"""Tests for erk rename command.

This file tests the rename command which renames a worktree workspace.
"""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.repo_discovery import RepoContext
from erk_shared.git.dry_run import DryRunGit
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.integrations.graphite.fake import FakeGraphite
from tests.fakes.shell import FakeShell
from tests.test_utils.env_helpers import erk_inmem_env


def test_rename_successful() -> None:
    """Test successful rename of a worktree."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Construct worktree paths
        work_dir = env.erk_root / "repos" / env.cwd.name / "worktrees"
        old_wt = work_dir / "old-name"
        work_dir / "new-name"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
        )
        test_ctx = env.build_context(
            git=git_ops,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(),
            repo=repo,
            dry_run=False,
            existing_paths={old_wt},
        )
        result = runner.invoke(cli, ["wt", "rename", "old-name", "new-name"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "new-name" in result.output


def test_rename_old_worktree_not_found() -> None:
    """Test rename fails when old worktree doesn't exist."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        test_ctx = env.build_context(
            git=git_ops,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(),
            dry_run=False,
        )
        result = runner.invoke(cli, ["wt", "rename", "nonexistent", "new-name"], obj=test_ctx)

        assert result.exit_code == 1
        assert "Worktree not found" in result.output


def test_rename_new_name_already_exists() -> None:
    """Test rename fails when new name already exists."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Construct worktree paths
        work_dir = env.erk_root / "repos" / env.cwd.name / "worktrees"
        old_wt = work_dir / "old-name"
        existing_wt = work_dir / "existing"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
        )
        test_ctx = env.build_context(
            git=git_ops,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(),
            repo=repo,
            dry_run=False,
            existing_paths={old_wt, existing_wt},
        )
        result = runner.invoke(cli, ["wt", "rename", "old-name", "existing"], obj=test_ctx)

        assert result.exit_code == 1
        assert "already exists" in result.output


def test_rename_with_graphite_enabled() -> None:
    """Test rename with Graphite integration enabled."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Construct worktree paths
        work_dir = env.erk_root / "repos" / env.cwd.name / "worktrees"
        old_wt = work_dir / "old-branch"

        # Enable Graphite
        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
        )
        test_ctx = env.build_context(
            use_graphite=True,
            git=git_ops,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(),
            repo=repo,
            dry_run=False,
            existing_paths={old_wt},
        )

        result = runner.invoke(cli, ["wt", "rename", "old-branch", "new-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        assert "new-branch" in result.output


def test_rename_dry_run() -> None:
    """Test rename in dry-run mode doesn't actually rename."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        # Construct worktree paths
        work_dir = env.erk_root / "repos" / env.cwd.name / "worktrees"
        old_wt = work_dir / "old-name"

        git_ops = FakeGit(git_common_dirs={env.cwd: env.git_dir})
        git_ops = DryRunGit(git_ops)
        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=work_dir,
            worktrees_dir=work_dir / "worktrees",
        )
        test_ctx = env.build_context(
            git=git_ops,
            github=FakeGitHub(),
            graphite=FakeGraphite(),
            shell=FakeShell(),
            repo=repo,
            dry_run=True,
            existing_paths={old_wt},
        )
        result = runner.invoke(cli, ["wt", "rename", "old-name", "new-name"], obj=test_ctx)

        assert result.exit_code == 0
        assert "Would rename" in result.output or "DRY RUN" in result.output
