"""Tests for trunk synchronization in submit command."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import ERK_PLAN_LABEL, submit_cmd
from erk_shared.git.abc import WorktreeInfo
from tests.commands.submit.conftest import create_plan, setup_submit_context


def test_submit_fails_when_root_worktree_not_on_trunk(tmp_path: Path) -> None:
    """Test submit fails if root worktree is not on trunk branch."""
    plan = create_plan("123", "Test Plan", labels=[ERK_PLAN_LABEL])

    # Define repo_root before using it in git_kwargs
    repo_root = tmp_path / "repo"

    # Root worktree is on 'feature' branch, not 'master'
    worktree_info = WorktreeInfo(
        path=repo_root,
        branch="feature",
        is_root=True,
    )
    ctx, fake_git, fake_github, _, _, _ = setup_submit_context(
        tmp_path,
        plans={"123": plan},
        git_kwargs={
            "worktrees": {repo_root: [worktree_info]},
            "current_branches": {repo_root: "feature"},
            "trunk_branches": {repo_root: "master"},
        },
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 1
    assert "Root worktree is on 'feature', not 'master'" in result.output
    assert "erk plan submit requires the root worktree to have master checked out" in result.output


def test_submit_fails_when_root_worktree_has_uncommitted_changes(tmp_path: Path) -> None:
    """Test submit fails if root worktree has uncommitted changes."""
    plan = create_plan("123", "Test Plan", labels=[ERK_PLAN_LABEL])

    # Define repo_root before using it in git_kwargs
    repo_root = tmp_path / "repo"

    worktree_info = WorktreeInfo(
        path=repo_root,
        branch="master",
        is_root=True,
    )
    ctx, fake_git, fake_github, _, _, _ = setup_submit_context(
        tmp_path,
        plans={"123": plan},
        git_kwargs={
            "worktrees": {repo_root: [worktree_info]},
            "current_branches": {repo_root: "master"},
            "trunk_branches": {repo_root: "master"},
            # Uncommitted changes in root worktree
            "file_statuses": {repo_root: (["staged.txt"], [], [])},
        },
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 1
    assert "Root worktree has uncommitted changes" in result.output
    assert "Please commit or stash changes" in result.output


def test_submit_auto_syncs_trunk_when_behind_remote(tmp_path: Path) -> None:
    """Test submit auto-syncs trunk when local is behind remote."""
    plan = create_plan("123", "Test Plan", labels=[ERK_PLAN_LABEL])

    # Define repo_root before using it in git_kwargs
    repo_root = tmp_path / "repo"

    # SHA values representing local behind remote
    local_sha = "abc123"
    remote_sha = "def456"
    # merge_base == local_sha means local is ancestor of remote (can fast-forward)
    merge_base_sha = "abc123"

    worktree_info = WorktreeInfo(
        path=repo_root,
        branch="master",
        is_root=True,
    )
    ctx, fake_git, fake_github, _, _, _ = setup_submit_context(
        tmp_path,
        plans={"123": plan},
        git_kwargs={
            "worktrees": {repo_root: [worktree_info]},
            "current_branches": {repo_root: "master"},
            "trunk_branches": {repo_root: "master"},
            "branch_heads": {
                "master": local_sha,
                "origin/master": remote_sha,
            },
            "merge_bases": {
                ("master", "origin/master"): merge_base_sha,
            },
            # Remote branches configured for branch_exists_on_remote
            "remote_branches": {repo_root: ["origin/master"]},
        },
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    # Should have attempted to pull
    assert ("origin", "master", True) in fake_git.pulled_branches
    # Check output shows sync message
    assert "Syncing master with origin/master" in result.output


def test_submit_fails_when_local_trunk_ahead_of_remote(tmp_path: Path) -> None:
    """Test submit fails if local trunk has unpushed commits."""
    plan = create_plan("123", "Test Plan", labels=[ERK_PLAN_LABEL])

    # Define repo_root before using it in git_kwargs
    repo_root = tmp_path / "repo"

    # SHA values representing local ahead of remote
    local_sha = "def456"
    remote_sha = "abc123"
    # merge_base == remote_sha means local is ahead of remote
    merge_base_sha = "abc123"

    worktree_info = WorktreeInfo(
        path=repo_root,
        branch="master",
        is_root=True,
    )
    ctx, fake_git, fake_github, _, _, _ = setup_submit_context(
        tmp_path,
        plans={"123": plan},
        git_kwargs={
            "worktrees": {repo_root: [worktree_info]},
            "current_branches": {repo_root: "master"},
            "trunk_branches": {repo_root: "master"},
            "branch_heads": {
                "master": local_sha,
                "origin/master": remote_sha,
            },
            "merge_bases": {
                ("master", "origin/master"): merge_base_sha,
            },
        },
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 1
    assert "Local master has commits not pushed to origin/master" in result.output
    assert "git push origin master" in result.output


def test_submit_fails_when_trunk_diverged(tmp_path: Path) -> None:
    """Test submit fails if trunk has truly diverged from remote."""
    plan = create_plan("123", "Test Plan", labels=[ERK_PLAN_LABEL])

    # Define repo_root before using it in git_kwargs
    repo_root = tmp_path / "repo"

    # SHA values representing true divergence (merge base is neither)
    local_sha = "abc123"
    remote_sha = "def456"
    merge_base_sha = "old789"  # Neither local nor remote

    worktree_info = WorktreeInfo(
        path=repo_root,
        branch="master",
        is_root=True,
    )
    ctx, fake_git, fake_github, _, _, _ = setup_submit_context(
        tmp_path,
        plans={"123": plan},
        git_kwargs={
            "worktrees": {repo_root: [worktree_info]},
            "current_branches": {repo_root: "master"},
            "trunk_branches": {repo_root: "master"},
            "branch_heads": {
                "master": local_sha,
                "origin/master": remote_sha,
            },
            "merge_bases": {
                ("master", "origin/master"): merge_base_sha,
            },
        },
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 1
    assert "Local master has diverged from origin/master" in result.output
    assert "git fetch origin && git reset --hard origin/master" in result.output


def test_submit_succeeds_when_trunk_already_synced(tmp_path: Path) -> None:
    """Test submit proceeds when trunk is already synced with remote."""
    plan = create_plan("123", "Test Plan", labels=[ERK_PLAN_LABEL])

    # Define repo_root before using it in git_kwargs
    repo_root = tmp_path / "repo"

    # SHA values represent already synced state
    same_sha = "abc123"

    worktree_info = WorktreeInfo(
        path=repo_root,
        branch="master",
        is_root=True,
    )
    ctx, fake_git, fake_github, _, _, _ = setup_submit_context(
        tmp_path,
        plans={"123": plan},
        git_kwargs={
            "worktrees": {repo_root: [worktree_info]},
            "current_branches": {repo_root: "master"},
            "trunk_branches": {repo_root: "master"},
            "branch_heads": {
                "master": same_sha,
                "origin/master": same_sha,
            },
            # Remote branches configured for branch_exists_on_remote
            "remote_branches": {repo_root: ["origin/master"]},
        },
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    # Should not have attempted to pull (already synced)
    assert len(fake_git.pulled_branches) == 0
    # Should proceed past trunk sync (we don't check full success here since
    # there are other prerequisites like workflow triggering)
    assert "Root worktree is on" not in result.output
    assert "Root worktree has uncommitted changes" not in result.output
    assert "has diverged" not in result.output
    assert "has commits not pushed" not in result.output
