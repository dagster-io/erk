"""Tests for branch source selection in worktree creation."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from tests.test_utils.env_helpers import erk_inmem_env, erk_isolated_fs_env


def test_create_detects_default_branch() -> None:
    """Test that create detects the default branch when needed."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli, ["wt", "create", "new-feature", "--from-current-branch"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output


def test_create_from_current_branch_in_worktree() -> None:
    """Regression: ensure --from-current-branch works when executed from a worktree."""
    runner = CliRunner()
    with erk_isolated_fs_env(runner) as env:
        repo_root = env.root_worktree
        git_dir = env.git_dir

        current_worktree = env.root_worktree.parent / "wt-current"
        current_worktree.mkdir()

        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=current_worktree, branch="feature"),
                ]
            },
            current_branches={current_worktree: "feature"},
            default_branches={repo_root: "main"},
            git_common_dirs={
                current_worktree: git_dir,
                repo_root: git_dir,
            },
        )

        test_ctx = env.build_context(git=git_ops, cwd=current_worktree)

        result = runner.invoke(cli, ["wt", "create", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output

        expected_worktree = repo_dir / "worktrees" / "feature"
        assert (current_worktree, "main") in git_ops.checked_out_branches
        assert (repo_root, "main") not in git_ops.checked_out_branches
        assert (expected_worktree, "feature") in git_ops.added_worktrees


def test_create_from_current_branch() -> None:
    """Test creating worktree from current branch."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "feature-branch"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli, ["wt", "create", "feature", "--from-current-branch"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output


def test_create_from_branch() -> None:
    """Test creating worktree from an existing branch."""
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

        result = runner.invoke(
            cli, ["wt", "create", "feature", "--from-branch", "existing-branch"], obj=test_ctx
        )

        assert result.exit_code == 0, result.output


def test_create_from_current_branch_on_main_fails() -> None:
    """Test that --from-current-branch fails with helpful message when on main."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            current_branches={env.cwd: "main"},
        )
        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli, ["wt", "create", "feature", "--from-current-branch"], obj=test_ctx
        )

        assert result.exit_code == 1
        assert "Cannot use --from-current-branch when on 'main'" in result.output
        assert "Alternatives:" in result.output


def test_create_from_current_branch_on_master_fails() -> None:
    """Test that --from-current-branch fails when on master branch too."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        git_ops = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "master"},
            current_branches={env.cwd: "master"},
            trunk_branches={env.cwd: "master"},
        )

        test_ctx = env.build_context(git=git_ops)

        result = runner.invoke(
            cli, ["wt", "create", "feature", "--from-current-branch"], obj=test_ctx
        )

        assert result.exit_code == 1
        assert "Cannot use --from-current-branch when on 'master'" in result.output
