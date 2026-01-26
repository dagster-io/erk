"""Tests for Graphite parent fallback logic in worktree creation."""

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.config import LoadedConfig
from erk.core.repo_discovery import RepoContext
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from tests.test_utils.env_helpers import erk_inmem_env


def test_from_current_branch_with_main_in_use_prefers_graphite_parent() -> None:
    """Test that --from-current-branch prefers Graphite parent when main is in use.

    Scenario:
    - Current worktree is on feature-2 (with Graphite parent feature-1)
    - Root worktree has main checked out
    - feature-1 is available (not checked out)

    Expected: Should checkout feature-1 (the parent), not try to checkout main
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_root = env.cwd
        git_dir = env.git_dir

        current_worktree = env.cwd.parent / "wt-current"
        current_worktree.mkdir()

        repo_dir = env.setup_repo_structure()

        # Pass local config directly
        local_config = LoadedConfig.test()

        # Set up worktree stack: main -> feature-1 -> feature-2
        branch_metadata = {
            "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
            "feature-1": BranchMetadata.branch(
                "feature-1", "main", children=["feature-2"], commit_sha="def456"
            ),
            "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
        }

        git_ops = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=current_worktree, branch="feature-2"),
                ]
            },
            current_branches={
                repo_root: "main",
                current_worktree: "feature-2",
            },
            default_branches={repo_root: "main"},
            git_common_dirs={
                current_worktree: git_dir,
                repo_root: git_dir,
            },
        )
        graphite_ops = FakeGraphite(branches=branch_metadata)

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
            cwd=current_worktree,
        )

        result = runner.invoke(cli, ["wt", "create", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should checkout feature-1 (the Graphite parent), not main
        assert (current_worktree, "feature-1") in git_ops.checked_out_branches


def test_from_current_branch_with_parent_in_use_falls_back_to_detached_head() -> None:
    """Test that --from-current-branch uses detached HEAD when parent is also in use.

    Scenario:
    - Current worktree is on feature-2 (with Graphite parent feature-1)
    - Root worktree has main checked out
    - Another worktree has feature-1 checked out

    Expected: Should use detached HEAD as fallback since both main and parent are in use
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_root = env.cwd
        git_dir = env.git_dir

        current_worktree = env.cwd.parent / "wt-current"
        current_worktree.mkdir()

        other_worktree = env.cwd.parent / "wt-other"
        other_worktree.mkdir()

        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Set up worktree stack: main -> feature-1 -> feature-2
        {
            "main": BranchMetadata.trunk("main", children=["feature-1"], commit_sha="abc123"),
            "feature-1": BranchMetadata.branch(
                "feature-1", "main", children=["feature-2"], commit_sha="def456"
            ),
            "feature-2": BranchMetadata.branch("feature-2", "feature-1", commit_sha="ghi789"),
        }

        git_ops = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=current_worktree, branch="feature-2"),
                    WorktreeInfo(path=other_worktree, branch="feature-1"),
                ]
            },
            current_branches={
                repo_root: "main",
                current_worktree: "feature-2",
                other_worktree: "feature-1",
            },
            default_branches={repo_root: "main"},
            git_common_dirs={
                current_worktree: git_dir,
                repo_root: git_dir,
                other_worktree: git_dir,
            },
        )

        test_ctx = env.build_context(git=git_ops, cwd=current_worktree)

        result = runner.invoke(cli, ["wt", "create", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should use detached HEAD since both main and feature-1 are in use
        assert len(git_ops.detached_checkouts) == 1
        assert git_ops.detached_checkouts[0][0] == current_worktree
        assert git_ops.detached_checkouts[0][1] == "feature-2"


def test_from_current_branch_without_graphite_falls_back_to_main() -> None:
    """Test that --from-current-branch falls back to main when no Graphite parent exists.

    Scenario:
    - Current worktree is on standalone-feature (not in any worktree stack)
    - Root worktree has other-branch checked out (not main)
    - main is available

    Expected: Should checkout main as fallback
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_root = env.cwd
        git_dir = env.git_dir

        current_worktree = env.cwd.parent / "wt-current"
        current_worktree.mkdir()

        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Set up minimal worktree stack (standalone-feature not in it)
        {
            "main": BranchMetadata.trunk("main", commit_sha="abc123"),
        }

        git_ops = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="other-branch"),
                    WorktreeInfo(path=current_worktree, branch="standalone-feature"),
                ]
            },
            current_branches={
                repo_root: "other-branch",
                current_worktree: "standalone-feature",
            },
            default_branches={repo_root: "main"},
            git_common_dirs={
                current_worktree: git_dir,
                repo_root: git_dir,
            },
        )

        test_ctx = env.build_context(git=git_ops, cwd=current_worktree)

        result = runner.invoke(cli, ["wt", "create", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should checkout main since no Graphite parent exists
        assert (current_worktree, "main") in git_ops.checked_out_branches


def test_from_current_branch_no_graphite_main_in_use_uses_detached_head() -> None:
    """Test that --from-current-branch uses detached HEAD when no parent and main is in use.

    Scenario:
    - Current worktree is on standalone-feature (not in any worktree stack)
    - Root worktree has main checked out

    Expected: Should use detached HEAD since no parent exists and main is in use
    """
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        repo_root = env.cwd
        git_dir = env.git_dir

        current_worktree = env.cwd.parent / "wt-current"
        current_worktree.mkdir()

        repo_dir = env.setup_repo_structure()

        config_toml = repo_dir / "config.toml"
        config_toml.write_text("", encoding="utf-8")

        # Set up minimal worktree stack (standalone-feature not in it)
        {
            "main": BranchMetadata.trunk("main", commit_sha="abc123"),
        }

        git_ops = FakeGit(
            worktrees={
                repo_root: [
                    WorktreeInfo(path=repo_root, branch="main"),
                    WorktreeInfo(path=current_worktree, branch="standalone-feature"),
                ]
            },
            current_branches={
                repo_root: "main",
                current_worktree: "standalone-feature",
            },
            default_branches={repo_root: "main"},
            git_common_dirs={
                current_worktree: git_dir,
                repo_root: git_dir,
            },
        )

        test_ctx = env.build_context(git=git_ops, cwd=current_worktree)

        result = runner.invoke(cli, ["wt", "create", "--from-current-branch"], obj=test_ctx)

        assert result.exit_code == 0, result.output
        # Should use detached HEAD since no parent and main is in use
        assert len(git_ops.detached_checkouts) == 1
        assert git_ops.detached_checkouts[0][0] == current_worktree
        assert git_ops.detached_checkouts[0][1] == "standalone-feature"
