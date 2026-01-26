"""Unit tests for --no-delete flag behavior in land command."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk.cli.commands.land_cmd import _cleanup_and_navigate
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state, save_pool_state
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.github.types import GitHubRepoId


def _create_test_assignment(
    slot_name: str,
    branch_name: str,
    worktree_path: Path,
) -> SlotAssignment:
    """Create a test assignment with current timestamp."""
    return SlotAssignment(
        slot_name=slot_name,
        branch_name=branch_name,
        assigned_at=datetime.now(UTC).isoformat(),
        worktree_path=worktree_path,
    )


def test_cleanup_and_navigate_no_delete_preserves_branch_and_slot(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that --no-delete preserves the branch and slot assignment.

    When landing with --no-delete, the PR is merged but:
    1. The local branch is NOT deleted
    2. The slot assignment is NOT removed
    3. A confirmation message is displayed
    """
    # Create a slot worktree with assignment
    worktree_path = tmp_path / "worktrees" / "erk-slot-01"
    worktree_path.mkdir(parents=True)
    main_repo_root = tmp_path / "main-repo"
    main_repo_root.mkdir(parents=True)
    (main_repo_root / ".git").mkdir()
    pool_json_path = main_repo_root / "pool.json"

    # Create pool state with assignment
    assignment = _create_test_assignment(
        slot_name="erk-slot-01",
        branch_name="feature-branch",
        worktree_path=worktree_path,
    )
    initial_state = PoolState.test(assignments=(assignment,))
    save_pool_state(pool_json_path, initial_state)

    fake_git = FakeGit(
        worktrees={main_repo_root: [WorktreeInfo(path=worktree_path, branch="feature-branch")]},
        git_common_dirs={main_repo_root: main_repo_root / ".git"},
        default_branches={main_repo_root: "main"},
        local_branches={main_repo_root: ["main", "feature-branch"]},
        existing_paths={
            worktree_path,
            main_repo_root,
            main_repo_root / ".git",
            pool_json_path,
        },
    )

    fake_graphite = FakeGraphite(
        branches={
            "feature-branch": BranchMetadata(
                name="feature-branch",
                parent="main",
                children=[],
                is_trunk=False,
                commit_sha=None,
            ),
        },
    )

    ctx = context_for_test(
        git=fake_git,
        graphite=fake_graphite,
        cwd=worktree_path,
    )

    repo = RepoContext(
        root=main_repo_root,
        repo_name="test-repo",
        repo_dir=main_repo_root,
        worktrees_dir=tmp_path / "worktrees",
        pool_json_path=pool_json_path,
        github=GitHubRepoId(owner="owner", repo="repo"),
    )

    # Call _cleanup_and_navigate with no_delete=True
    try:
        _cleanup_and_navigate(
            ctx=ctx,
            repo=repo,
            branch="feature-branch",
            worktree_path=worktree_path,
            script=False,
            pull_flag=False,
            force=True,
            is_current_branch=False,
            target_child_branch=None,
            objective_number=None,
            no_delete=True,
            skip_activation_output=False,
            cleanup_confirmed=True,
        )
    except SystemExit:
        pass  # Expected - function raises SystemExit(0) at end

    # Verify branch was NOT deleted
    deleted_branches = [branch for _path, branch in fake_graphite.delete_branch_calls]
    assert "feature-branch" not in deleted_branches
    assert "feature-branch" not in fake_git.deleted_branches

    # Verify slot assignment was NOT removed
    reloaded_state = load_pool_state(pool_json_path)
    assert reloaded_state is not None
    matching_assignments = [
        a for a in reloaded_state.assignments if a.branch_name == "feature-branch"
    ]
    assert len(matching_assignments) == 1, "Slot assignment should be preserved"

    # Verify confirmation message was displayed
    captured = capsys.readouterr()
    assert "preserved" in captured.err
    assert "--no-delete" in captured.err


def test_cleanup_and_navigate_no_delete_preserves_non_slot_branch(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that --no-delete preserves a non-slot worktree branch.

    When landing with --no-delete from a non-slot worktree:
    1. The local branch is NOT deleted
    2. The worktree is NOT detached
    3. A confirmation message is displayed
    """
    # Create a non-slot worktree
    worktree_path = tmp_path / "worktrees" / "my-feature"
    worktree_path.mkdir(parents=True)
    main_repo_root = tmp_path / "main-repo"
    main_repo_root.mkdir(parents=True)
    (main_repo_root / ".git").mkdir()
    pool_json_path = main_repo_root / "pool.json"

    # Create empty pool state (no slot assignments)
    empty_state = PoolState.test(assignments=())
    save_pool_state(pool_json_path, empty_state)

    fake_git = FakeGit(
        worktrees={main_repo_root: [WorktreeInfo(path=worktree_path, branch="feature-branch")]},
        git_common_dirs={main_repo_root: main_repo_root / ".git"},
        default_branches={main_repo_root: "main"},
        local_branches={main_repo_root: ["main", "feature-branch"]},
        existing_paths={
            worktree_path,
            main_repo_root,
            main_repo_root / ".git",
            pool_json_path,
        },
    )

    fake_graphite = FakeGraphite()

    ctx = context_for_test(
        git=fake_git,
        graphite=fake_graphite,
        cwd=worktree_path,
    )

    repo = RepoContext(
        root=main_repo_root,
        repo_name="test-repo",
        repo_dir=main_repo_root,
        worktrees_dir=tmp_path / "worktrees",
        pool_json_path=pool_json_path,
        github=GitHubRepoId(owner="owner", repo="repo"),
    )

    # Call _cleanup_and_navigate with no_delete=True
    try:
        _cleanup_and_navigate(
            ctx=ctx,
            repo=repo,
            branch="feature-branch",
            worktree_path=worktree_path,
            script=False,
            pull_flag=False,
            force=True,
            is_current_branch=False,
            target_child_branch=None,
            objective_number=None,
            no_delete=True,
            skip_activation_output=False,
            cleanup_confirmed=True,
        )
    except SystemExit:
        pass  # Expected - function raises SystemExit(0) at end

    # Verify branch was NOT deleted
    deleted_branches = [branch for _path, branch in fake_graphite.delete_branch_calls]
    assert "feature-branch" not in deleted_branches
    assert "feature-branch" not in fake_git.deleted_branches

    # Verify worktree was NOT detached (no checkout operations)
    assert len(fake_git.detached_checkouts) == 0
    assert len(fake_git.checked_out_branches) == 0

    # Verify confirmation message was displayed
    captured = capsys.readouterr()
    assert "preserved" in captured.err
    assert "--no-delete" in captured.err


def test_cleanup_and_navigate_no_delete_with_up_flag(tmp_path: Path) -> None:
    """Test that --no-delete works with --up flag navigation.

    When landing with --no-delete and is_current_branch=True, the function
    should still navigate to the target child branch (for --up behavior).
    """
    # Create worktrees for current and child branches
    current_worktree = tmp_path / "worktrees" / "erk-slot-01"
    current_worktree.mkdir(parents=True)
    child_worktree = tmp_path / "worktrees" / "erk-slot-02"
    child_worktree.mkdir(parents=True)
    main_repo_root = tmp_path / "main-repo"
    main_repo_root.mkdir(parents=True)
    (main_repo_root / ".git").mkdir()
    pool_json_path = main_repo_root / "pool.json"

    # Create pool state with assignments
    assignment = _create_test_assignment(
        slot_name="erk-slot-01",
        branch_name="feature-branch",
        worktree_path=current_worktree,
    )
    child_assignment = _create_test_assignment(
        slot_name="erk-slot-02",
        branch_name="child-branch",
        worktree_path=child_worktree,
    )
    initial_state = PoolState.test(assignments=(assignment, child_assignment))
    save_pool_state(pool_json_path, initial_state)

    fake_git = FakeGit(
        worktrees={
            main_repo_root: [
                WorktreeInfo(path=current_worktree, branch="feature-branch"),
                WorktreeInfo(path=child_worktree, branch="child-branch"),
            ]
        },
        git_common_dirs={main_repo_root: main_repo_root / ".git"},
        default_branches={main_repo_root: "main"},
        local_branches={main_repo_root: ["main", "feature-branch", "child-branch"]},
        existing_paths={
            current_worktree,
            child_worktree,
            main_repo_root,
            main_repo_root / ".git",
            pool_json_path,
        },
    )

    fake_graphite = FakeGraphite(
        branches={
            "feature-branch": BranchMetadata(
                name="feature-branch",
                parent="main",
                children=["child-branch"],
                is_trunk=False,
                commit_sha=None,
            ),
            "child-branch": BranchMetadata(
                name="child-branch",
                parent="feature-branch",
                children=[],
                is_trunk=False,
                commit_sha=None,
            ),
        },
    )

    ctx = context_for_test(
        git=fake_git,
        graphite=fake_graphite,
        cwd=current_worktree,
    )

    repo = RepoContext(
        root=main_repo_root,
        repo_name="test-repo",
        repo_dir=main_repo_root,
        worktrees_dir=tmp_path / "worktrees",
        pool_json_path=pool_json_path,
        github=GitHubRepoId(owner="owner", repo="repo"),
    )

    # Call _cleanup_and_navigate with no_delete=True and target_child_branch
    # is_current_branch=True triggers navigation after cleanup
    try:
        _cleanup_and_navigate(
            ctx=ctx,
            repo=repo,
            branch="feature-branch",
            worktree_path=current_worktree,
            script=True,  # Use script mode to avoid activation script issues
            pull_flag=False,
            force=True,
            is_current_branch=True,  # We are in the current branch's worktree
            target_child_branch="child-branch",  # Navigate to child (--up behavior)
            objective_number=None,
            no_delete=True,
            skip_activation_output=False,
            cleanup_confirmed=True,
        )
    except SystemExit:
        pass  # Expected - function raises SystemExit(0) at end

    # Verify branch was NOT deleted (--no-delete)
    deleted_branches = [branch for _path, branch in fake_graphite.delete_branch_calls]
    assert "feature-branch" not in deleted_branches
    assert "feature-branch" not in fake_git.deleted_branches

    # Verify slot assignments were preserved
    reloaded_state = load_pool_state(pool_json_path)
    assert reloaded_state is not None
    assert len(reloaded_state.assignments) == 2  # Both assignments preserved
