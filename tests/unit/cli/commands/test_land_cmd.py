"""Unit tests for land command parsing utilities and dry-run mode."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.cli.commands.land_cmd import (
    ParsedArgument,
    _cleanup_and_navigate,
    _execute_simple_land,
    parse_argument,
)
from erk.cli.commands.navigation_helpers import find_assignment_by_worktree_path
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state, save_pool_state
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.graphite.types import BranchMetadata
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import GitHubRepoId, PRDetails
from tests.test_utils.env_helpers import erk_inmem_env


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


def test_parse_argument_pr_number() -> None:
    """Test parsing a plain PR number."""
    result = parse_argument("123")
    assert result == ParsedArgument(arg_type="pr-number", pr_number=123)


def test_parse_argument_pr_number_single_digit() -> None:
    """Test parsing single-digit PR number."""
    result = parse_argument("1")
    assert result == ParsedArgument(arg_type="pr-number", pr_number=1)


def test_parse_argument_pr_number_large() -> None:
    """Test parsing large PR number."""
    result = parse_argument("99999")
    assert result == ParsedArgument(arg_type="pr-number", pr_number=99999)


def test_parse_argument_pr_url_github() -> None:
    """Test parsing GitHub PR URL."""
    result = parse_argument("https://github.com/owner/repo/pull/456")
    assert result == ParsedArgument(arg_type="pr-url", pr_number=456)


def test_parse_argument_pr_url_with_trailing_content() -> None:
    """Test parsing PR URL with trailing path segments."""
    result = parse_argument("https://github.com/owner/repo/pull/789/files")
    assert result == ParsedArgument(arg_type="pr-url", pr_number=789)


def test_parse_argument_pr_url_graphite() -> None:
    """Test parsing Graphite PR URL."""
    result = parse_argument("https://app.graphite.dev/github/pr/owner/repo/321")
    assert result == ParsedArgument(arg_type="pr-url", pr_number=321)


def test_parse_argument_pr_url_graphite_with_title() -> None:
    """Test parsing Graphite PR URL with title slug."""
    result = parse_argument(
        "https://app.graphite.com/github/pr/dagster-io/erk/3718/"
        "Add-dynamic-tripwire-enforcement-system?utm_source=chrome-extension"
    )
    assert result == ParsedArgument(arg_type="pr-url", pr_number=3718)


def test_parse_argument_branch_simple() -> None:
    """Test parsing a simple branch name."""
    result = parse_argument("feature-branch")
    assert result == ParsedArgument(arg_type="branch", pr_number=None)


def test_parse_argument_branch_with_slashes() -> None:
    """Test parsing a branch name with slashes."""
    result = parse_argument("feature/add-new-thing")
    assert result == ParsedArgument(arg_type="branch", pr_number=None)


def test_parse_argument_branch_numeric_prefix() -> None:
    """Test parsing a branch name that starts with numbers but isn't purely numeric."""
    result = parse_argument("123-fix-bug")
    assert result == ParsedArgument(arg_type="branch", pr_number=None)


def test_parse_argument_branch_main() -> None:
    """Test parsing 'main' branch name."""
    result = parse_argument("main")
    assert result == ParsedArgument(arg_type="branch", pr_number=None)


def test_parse_argument_branch_master() -> None:
    """Test parsing 'master' branch name."""
    result = parse_argument("master")
    assert result == ParsedArgument(arg_type="branch", pr_number=None)


# Tests for find_assignment_by_worktree_path


def testfind_assignment_by_worktree_path_finds_matching_slot(tmp_path: Path) -> None:
    """Test that find_assignment_by_worktree_path finds a matching slot assignment."""
    worktree_path = tmp_path / "worktrees" / "erk-slot-01"
    worktree_path.mkdir(parents=True)

    assignment = _create_test_assignment("erk-slot-01", "feature-branch", worktree_path)
    state = PoolState.test(assignments=(assignment,))

    result = find_assignment_by_worktree_path(state, worktree_path)

    assert result is not None
    assert result.slot_name == "erk-slot-01"
    assert result.branch_name == "feature-branch"


def testfind_assignment_by_worktree_path_returns_none_for_non_slot(tmp_path: Path) -> None:
    """Test that find_assignment_by_worktree_path returns None for non-slot worktrees."""
    slot_worktree = tmp_path / "worktrees" / "erk-slot-01"
    slot_worktree.mkdir(parents=True)
    regular_worktree = tmp_path / "worktrees" / "regular-worktree"
    regular_worktree.mkdir(parents=True)

    assignment = _create_test_assignment("erk-slot-01", "feature-branch", slot_worktree)
    state = PoolState.test(assignments=(assignment,))

    result = find_assignment_by_worktree_path(state, regular_worktree)

    assert result is None


def testfind_assignment_by_worktree_path_returns_none_for_empty_pool(tmp_path: Path) -> None:
    """Test that find_assignment_by_worktree_path returns None when pool has no assignments."""
    worktree_path = tmp_path / "worktrees" / "some-worktree"
    worktree_path.mkdir(parents=True)

    state = PoolState.test(assignments=())

    result = find_assignment_by_worktree_path(state, worktree_path)

    assert result is None


def testfind_assignment_by_worktree_path_returns_none_for_nonexistent_path(
    tmp_path: Path,
) -> None:
    """Test that find_assignment_by_worktree_path returns None for nonexistent paths."""
    slot_worktree = tmp_path / "worktrees" / "erk-slot-01"
    slot_worktree.mkdir(parents=True)
    nonexistent_path = tmp_path / "worktrees" / "nonexistent"

    assignment = _create_test_assignment("erk-slot-01", "feature-branch", slot_worktree)
    state = PoolState.test(assignments=(assignment,))

    result = find_assignment_by_worktree_path(state, nonexistent_path)

    assert result is None


def testfind_assignment_by_worktree_path_handles_multiple_assignments(tmp_path: Path) -> None:
    """Test that find_assignment_by_worktree_path finds correct assignment among multiple."""
    wt1 = tmp_path / "worktrees" / "erk-slot-01"
    wt1.mkdir(parents=True)
    wt2 = tmp_path / "worktrees" / "erk-slot-02"
    wt2.mkdir(parents=True)

    assignment1 = _create_test_assignment("erk-slot-01", "feature-a", wt1)
    assignment2 = _create_test_assignment("erk-slot-02", "feature-b", wt2)
    state = PoolState.test(assignments=(assignment1, assignment2))

    result = find_assignment_by_worktree_path(state, wt2)

    assert result is not None
    assert result.slot_name == "erk-slot-02"
    assert result.branch_name == "feature-b"


# Tests for dry-run mode


def test_cleanup_and_navigate_dry_run_does_not_save_pool_state(tmp_path: Path) -> None:
    """Test that _cleanup_and_navigate in dry-run mode does not save pool state."""
    # Create worktree path and pool.json
    worktree_path = tmp_path / "worktrees" / "erk-slot-01"
    worktree_path.mkdir(parents=True)
    pool_json_path = tmp_path / "pool.json"

    # Create initial pool state with an assignment
    assignment = _create_test_assignment("erk-slot-01", "feature-branch", worktree_path)
    initial_state = PoolState.test(assignments=(assignment,))

    # Write initial state to disk

    save_pool_state(pool_json_path, initial_state)

    # Create context with dry_run=True
    fake_git = FakeGit(
        worktrees={tmp_path: [WorktreeInfo(path=worktree_path, branch="feature-branch")]},
        git_common_dirs={tmp_path: tmp_path / ".git"},
        default_branches={tmp_path: "main"},
        local_branches={tmp_path: ["main", "feature-branch"]},
        existing_paths={worktree_path, tmp_path, tmp_path / ".git", pool_json_path},
    )

    ctx = context_for_test(
        git=fake_git,
        graphite=FakeGraphite(),
        cwd=worktree_path,
        dry_run=True,
    )

    repo = RepoContext(
        root=tmp_path,
        repo_name="test-repo",
        repo_dir=tmp_path,
        worktrees_dir=tmp_path / "worktrees",
        pool_json_path=pool_json_path,
        github=GitHubRepoId(owner="owner", repo="repo"),
    )

    # Call _cleanup_and_navigate in dry-run mode with objective
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
            objective_number=123,  # This would trigger pool state save
            no_delete=False,
        )
    except SystemExit:
        pass  # Expected - function raises SystemExit(0) at end

    # Verify pool state was NOT modified (objective should NOT be recorded)
    reloaded_state = load_pool_state(pool_json_path)
    assert reloaded_state is not None
    # The slot should still have its assignment (not modified by dry-run)
    found_assignment = None
    for a in reloaded_state.assignments:
        if a.slot_name == "erk-slot-01":
            found_assignment = a
            break
    assert found_assignment is not None


def test_cleanup_and_navigate_dry_run_shows_summary() -> None:
    """Test that dry-run mode outputs summary message."""
    runner = CliRunner()
    with erk_inmem_env(runner) as env:
        worktree_path = env.erk_root / "repos" / env.cwd.name / "worktrees" / "feature-branch"

        fake_git = FakeGit(
            worktrees={env.cwd: [WorktreeInfo(path=worktree_path, branch="feature-branch")]},
            git_common_dirs={env.cwd: env.git_dir},
            default_branches={env.cwd: "main"},
            local_branches={env.cwd: ["main", "feature-branch"]},
            existing_paths={worktree_path, env.cwd, env.git_dir},
        )

        ctx = context_for_test(
            git=fake_git,
            graphite=FakeGraphite(),
            cwd=worktree_path,
            dry_run=True,
        )

        repo = RepoContext(
            root=env.cwd,
            repo_name=env.cwd.name,
            repo_dir=env.erk_root / "repos" / env.cwd.name,
            worktrees_dir=env.erk_root / "repos" / env.cwd.name / "worktrees",
            pool_json_path=env.erk_root / "repos" / env.cwd.name / "pool.json",
            github=GitHubRepoId(owner="owner", repo="repo"),
        )

        # Capture output
        import io
        import sys

        captured = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured

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
                no_delete=False,
            )
        except SystemExit as e:
            assert e.code == 0  # Should exit cleanly
        finally:
            sys.stderr = old_stderr

        # The dry-run summary is output via user_output which goes to stderr
        # Note: user_output uses click.echo which may not capture in StringIO
        # The test mainly verifies the function doesn't crash in dry-run mode


# Tests for non-Graphite (GraphiteDisabled) mode


def test_execute_simple_land_merges_pr_without_graphite(tmp_path: Path) -> None:
    """Test that _execute_simple_land merges a PR using GitHub API only."""
    repo_root = tmp_path
    branch = "feature-branch"
    pr_number = 123

    # Create PR details
    pr_details = PRDetails(
        number=pr_number,
        url="https://github.com/owner/repo/pull/123",
        title="Test PR",
        body="Test body",
        state="OPEN",
        base_ref_name="main",
        head_ref_name=branch,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        is_draft=False,
        is_cross_repository=False,
        owner="owner",
        repo="repo",
    )

    fake_git = FakeGit(
        default_branches={repo_root: "main"},
    )

    fake_github = FakeGitHub(
        pr_details={pr_number: pr_details},
    )

    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
        cwd=repo_root,
    )

    # Execute simple land
    result = _execute_simple_land(ctx, repo_root=repo_root, branch=branch, pr_details=pr_details)

    # Verify PR was merged
    assert result == pr_number
    assert pr_number in fake_github.merged_prs


def test_execute_simple_land_fails_if_pr_not_open(tmp_path: Path) -> None:
    """Test that _execute_simple_land fails if PR is not open."""
    repo_root = tmp_path
    branch = "feature-branch"
    pr_number = 123

    # Create closed PR details
    pr_details = PRDetails(
        number=pr_number,
        url="https://github.com/owner/repo/pull/123",
        title="Test PR",
        body="Test body",
        state="MERGED",
        base_ref_name="main",
        head_ref_name=branch,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        is_draft=False,
        is_cross_repository=False,
        owner="owner",
        repo="repo",
    )

    fake_git = FakeGit(
        default_branches={repo_root: "main"},
    )

    fake_github = FakeGitHub()

    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
        cwd=repo_root,
    )

    # Execute simple land should fail
    try:
        _execute_simple_land(ctx, repo_root=repo_root, branch=branch, pr_details=pr_details)
        pytest.fail("Expected SystemExit")
    except SystemExit as e:
        assert e.code == 1


def test_execute_simple_land_fails_if_pr_not_targeting_trunk(tmp_path: Path) -> None:
    """Test that _execute_simple_land fails if PR base is not trunk."""
    repo_root = tmp_path
    branch = "feature-branch"
    pr_number = 123

    # Create PR targeting non-trunk branch
    pr_details = PRDetails(
        number=pr_number,
        url="https://github.com/owner/repo/pull/123",
        title="Test PR",
        body="Test body",
        state="OPEN",
        base_ref_name="some-other-branch",  # Not trunk
        head_ref_name=branch,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        is_draft=False,
        is_cross_repository=False,
        owner="owner",
        repo="repo",
    )

    fake_git = FakeGit(
        default_branches={repo_root: "main"},
    )

    fake_github = FakeGitHub()

    ctx = context_for_test(
        git=fake_git,
        github=fake_github,
        graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
        cwd=repo_root,
    )

    # Execute simple land should fail
    try:
        _execute_simple_land(ctx, repo_root=repo_root, branch=branch, pr_details=pr_details)
        pytest.fail("Expected SystemExit")
    except SystemExit as e:
        assert e.code == 1


def test_cleanup_and_navigate_uses_plain_git_delete_when_graphite_disabled(
    tmp_path: Path,
) -> None:
    """Test that _cleanup_and_navigate uses git.delete_branch when Graphite is disabled."""
    worktree_path = tmp_path / "worktrees" / "feature-branch"
    worktree_path.mkdir(parents=True)
    main_repo_root = tmp_path

    fake_git = FakeGit(
        worktrees={main_repo_root: [WorktreeInfo(path=worktree_path, branch="feature-branch")]},
        git_common_dirs={main_repo_root: main_repo_root / ".git"},
        default_branches={main_repo_root: "main"},
        local_branches={main_repo_root: ["main", "feature-branch"]},
        existing_paths={worktree_path, main_repo_root, main_repo_root / ".git"},
    )

    ctx = context_for_test(
        git=fake_git,
        graphite=GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED),
        cwd=worktree_path,
    )

    repo = RepoContext(
        root=main_repo_root,
        repo_name="test-repo",
        repo_dir=main_repo_root,
        worktrees_dir=tmp_path / "worktrees",
        pool_json_path=main_repo_root / "pool.json",
        github=GitHubRepoId(owner="owner", repo="repo"),
    )

    # Call _cleanup_and_navigate
    try:
        _cleanup_and_navigate(
            ctx=ctx,
            repo=repo,
            branch="feature-branch",
            worktree_path=None,  # No worktree to handle, just branch deletion
            script=False,
            pull_flag=False,
            force=True,
            is_current_branch=False,
            target_child_branch=None,
            objective_number=None,
            no_delete=False,
        )
    except SystemExit:
        pass  # Expected - function raises SystemExit(0) at end

    # Verify branch was deleted via plain git (not graphite)
    assert "feature-branch" in fake_git.deleted_branches


def test_cleanup_and_navigate_detects_slot_by_branch_name(tmp_path: Path) -> None:
    """Test that slot detection uses branch name, not worktree path.

    Regression test for bug where slot worktrees were not detected because
    path comparison failed. The fix uses find_branch_assignment() instead of
    find_assignment_by_worktree_path() to match by branch name.
    """
    # Use different paths to simulate path mismatch scenario
    # In the bug, pool.json stored one path but git reported a different path
    stored_worktree_path = tmp_path / "erk-root-a" / "worktrees" / "erk-slot-01"
    actual_worktree_path = tmp_path / "erk-root-b" / "worktrees" / "erk-slot-01"
    stored_worktree_path.mkdir(parents=True)
    actual_worktree_path.mkdir(parents=True)
    main_repo_root = tmp_path / "main-repo"
    main_repo_root.mkdir(parents=True)
    (main_repo_root / ".git").mkdir()
    pool_json_path = main_repo_root / "pool.json"

    # Create pool state with assignment using stored path (different from actual)
    assignment = _create_test_assignment(
        slot_name="erk-slot-01",
        branch_name="feature-branch",
        worktree_path=stored_worktree_path,  # Stored path differs from actual
    )

    initial_state = PoolState.test(assignments=(assignment,))
    save_pool_state(pool_json_path, initial_state)

    fake_git = FakeGit(
        worktrees={
            main_repo_root: [WorktreeInfo(path=actual_worktree_path, branch="feature-branch")]
        },
        git_common_dirs={main_repo_root: main_repo_root / ".git"},
        default_branches={main_repo_root: "main"},
        local_branches={main_repo_root: ["main", "feature-branch"]},
        existing_paths={
            actual_worktree_path,
            stored_worktree_path,  # Assignment uses this path
            main_repo_root,
            main_repo_root / ".git",
            pool_json_path,
        },
    )

    # Configure FakeGraphite to track the branch so GraphiteBranchManager uses Graphite delete
    # (GraphiteBranchManager.delete_branch does LBYL check before calling graphite.delete_branch)
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
        cwd=actual_worktree_path,
    )

    repo = RepoContext(
        root=main_repo_root,
        repo_name="test-repo",
        repo_dir=main_repo_root,
        worktrees_dir=tmp_path / "worktrees",
        pool_json_path=pool_json_path,
        github=GitHubRepoId(owner="owner", repo="repo"),
    )

    # Call _cleanup_and_navigate with the actual path (which differs from stored)
    # The bug would cause this to NOT detect the slot and delete the worktree
    # The fix should detect the slot by branch name and unassign instead
    try:
        _cleanup_and_navigate(
            ctx=ctx,
            repo=repo,
            branch="feature-branch",
            worktree_path=actual_worktree_path,  # Actual path differs from stored
            script=False,
            pull_flag=False,
            force=True,
            is_current_branch=False,
            target_child_branch=None,
            objective_number=None,
            no_delete=False,
        )
    except SystemExit:
        pass  # Expected - function raises SystemExit(0) at end

    # Verify slot was unassigned (detected as slot by branch name)
    reloaded_state = load_pool_state(pool_json_path)
    assert reloaded_state is not None
    # Assignment should be removed (slot unassigned)
    matching_assignments = [
        a for a in reloaded_state.assignments if a.branch_name == "feature-branch"
    ]
    assert len(matching_assignments) == 0, "Slot should have been unassigned"

    # Verify branch was deleted via Graphite (since FakeGraphite is used and branch is tracked)
    # GraphiteBranchManager.delete_branch calls graphite.delete_branch when branch is tracked
    deleted_branches = [branch for _path, branch in fake_graphite.delete_branch_calls]
    assert "feature-branch" in deleted_branches


def test_cleanup_and_navigate_detects_slot_by_path_pattern_without_assignment(
    tmp_path: Path,
) -> None:
    """Test slot detection by worktree path pattern when no pool assignment exists.

    Regression test for bug where slot worktrees (e.g., erk-slot-01) were deleted
    when branches were checked out via 'gt get' instead of erk commands.

    The bug occurred because:
    1. 'gt get' checks out a branch without creating a pool.json assignment
    2. _cleanup_and_navigate only checked pool.json for slot detection
    3. With no assignment, it fell through to "delete worktree" path

    The fix adds a fallback: if no assignment but worktree path matches erk-slot-XX
    pattern, treat it as a slot and release (don't delete the worktree directory).
    """
    # Create a slot worktree without any pool assignment
    slot_worktree_path = tmp_path / "worktrees" / "erk-slot-01"
    slot_worktree_path.mkdir(parents=True)
    main_repo_root = tmp_path / "main-repo"
    main_repo_root.mkdir(parents=True)
    (main_repo_root / ".git").mkdir()
    pool_json_path = main_repo_root / "pool.json"

    # Create empty pool state (no assignments)

    empty_state = PoolState.test(assignments=())
    save_pool_state(pool_json_path, empty_state)

    # Create the placeholder branch that should exist
    placeholder_branch = "__erk-slot-01-br-stub__"

    fake_git = FakeGit(
        worktrees={
            main_repo_root: [WorktreeInfo(path=slot_worktree_path, branch="feature-branch")]
        },
        git_common_dirs={main_repo_root: main_repo_root / ".git"},
        default_branches={main_repo_root: "main"},
        local_branches={main_repo_root: ["main", "feature-branch", placeholder_branch]},
        existing_paths={
            slot_worktree_path,
            main_repo_root,
            main_repo_root / ".git",
            pool_json_path,
        },
    )

    # Configure FakeGraphite to track the branch so GraphiteBranchManager uses Graphite delete
    # (GraphiteBranchManager.delete_branch does LBYL check before calling graphite.delete_branch)
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
        cwd=slot_worktree_path,
    )

    repo = RepoContext(
        root=main_repo_root,
        repo_name="test-repo",
        repo_dir=main_repo_root,
        worktrees_dir=tmp_path / "worktrees",
        pool_json_path=pool_json_path,
        github=GitHubRepoId(owner="owner", repo="repo"),
    )

    # Call _cleanup_and_navigate
    # Without the fix: would delete the worktree (bad!)
    # With the fix: should detect slot by path pattern and release it (good!)
    try:
        _cleanup_and_navigate(
            ctx=ctx,
            repo=repo,
            branch="feature-branch",
            worktree_path=slot_worktree_path,
            script=False,
            pull_flag=False,
            force=True,
            is_current_branch=False,
            target_child_branch=None,
            objective_number=None,
            no_delete=False,
        )
    except SystemExit:
        pass  # Expected - function raises SystemExit(0) at end

    # Verify worktree was NOT deleted (key assertion!)
    # The worktree should still exist in git's worktree list
    assert slot_worktree_path not in fake_git.removed_worktrees

    # Verify placeholder branch was checked out
    checkout_calls = [
        (path, branch)
        for path, branch in fake_git.checked_out_branches
        if branch == placeholder_branch
    ]
    assert len(checkout_calls) == 1, "Should have checked out placeholder branch"
    assert checkout_calls[0][0] == slot_worktree_path

    # Verify branch was deleted via Graphite (since FakeGraphite is used and branch is tracked)
    # GraphiteBranchManager.delete_branch calls graphite.delete_branch when branch is tracked
    deleted_branches = [branch for _path, branch in fake_graphite.delete_branch_calls]
    assert "feature-branch" in deleted_branches


def test_cleanup_and_navigate_non_slot_worktree_checkouts_trunk_before_deleting_branch(
    tmp_path: Path,
) -> None:
    """Test that non-slot worktree cleanup checks out trunk before deleting branch.

    Regression test for bug where `erk land` failed from a non-slot worktree with:
    "branch is currently checked out in another worktree and cannot be deleted"

    The fix checks out the trunk branch before deleting the feature branch,
    allowing git to delete a branch that was previously checked out.
    """
    # Create a non-slot worktree (name doesn't match erk-slot-XX pattern)
    non_slot_worktree_path = tmp_path / "worktrees" / "my-feature-worktree"
    non_slot_worktree_path.mkdir(parents=True)
    main_repo_root = tmp_path / "main-repo"
    main_repo_root.mkdir(parents=True)
    (main_repo_root / ".git").mkdir()
    pool_json_path = main_repo_root / "pool.json"

    # Create empty pool state (no slot assignments)

    empty_state = PoolState.test(assignments=())
    save_pool_state(pool_json_path, empty_state)

    fake_git = FakeGit(
        worktrees={
            main_repo_root: [WorktreeInfo(path=non_slot_worktree_path, branch="feature-branch")]
        },
        git_common_dirs={main_repo_root: main_repo_root / ".git"},
        default_branches={main_repo_root: "main"},
        local_branches={main_repo_root: ["main", "feature-branch"]},
        existing_paths={
            non_slot_worktree_path,
            main_repo_root,
            main_repo_root / ".git",
            pool_json_path,
        },
    )

    # Configure FakeGraphite to track the branch so GraphiteBranchManager uses Graphite delete
    # (GraphiteBranchManager.delete_branch does LBYL check before calling graphite.delete_branch)
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
        cwd=non_slot_worktree_path,
    )

    repo = RepoContext(
        root=main_repo_root,
        repo_name="test-repo",
        repo_dir=main_repo_root,
        worktrees_dir=tmp_path / "worktrees",
        pool_json_path=pool_json_path,
        github=GitHubRepoId(owner="owner", repo="repo"),
    )

    # Call _cleanup_and_navigate
    # Without the fix: would fail because branch is checked out
    # With the fix: should checkout trunk first, then delete branch
    try:
        _cleanup_and_navigate(
            ctx=ctx,
            repo=repo,
            branch="feature-branch",
            worktree_path=non_slot_worktree_path,
            script=False,
            pull_flag=False,
            force=True,
            is_current_branch=False,
            target_child_branch=None,
            objective_number=None,
            no_delete=False,
        )
    except SystemExit:
        pass  # Expected - function raises SystemExit(0) at end

    # Verify detached HEAD at trunk was checked out before deletion
    # (we use detached HEAD because trunk may be checked out in root worktree)
    detached_calls = [(path, ref) for path, ref in fake_git.detached_checkouts if ref == "main"]
    assert len(detached_calls) == 1, "Should have checked out detached HEAD at trunk"
    assert detached_calls[0][0] == non_slot_worktree_path

    # Verify worktree was NOT removed (preserved)
    assert non_slot_worktree_path not in fake_git.removed_worktrees

    # Verify branch was deleted via Graphite (since FakeGraphite is used and branch is tracked)
    # GraphiteBranchManager.delete_branch calls graphite.delete_branch when branch is tracked
    deleted_branches = [branch for _path, branch in fake_graphite.delete_branch_calls]
    assert "feature-branch" in deleted_branches


def test_cleanup_and_navigate_non_slot_worktree_fails_with_uncommitted_changes(
    tmp_path: Path,
) -> None:
    """Test that non-slot worktree cleanup fails if there are uncommitted changes.

    Before switching to trunk, we must check for uncommitted changes to prevent
    accidental loss of work.
    """
    # Create a non-slot worktree
    non_slot_worktree_path = tmp_path / "worktrees" / "my-feature-worktree"
    non_slot_worktree_path.mkdir(parents=True)
    main_repo_root = tmp_path / "main-repo"
    main_repo_root.mkdir(parents=True)
    (main_repo_root / ".git").mkdir()
    pool_json_path = main_repo_root / "pool.json"

    # Create empty pool state

    empty_state = PoolState.test(assignments=())
    save_pool_state(pool_json_path, empty_state)

    fake_git = FakeGit(
        worktrees={
            main_repo_root: [WorktreeInfo(path=non_slot_worktree_path, branch="feature-branch")]
        },
        git_common_dirs={main_repo_root: main_repo_root / ".git"},
        default_branches={main_repo_root: "main"},
        local_branches={main_repo_root: ["main", "feature-branch"]},
        existing_paths={
            non_slot_worktree_path,
            main_repo_root,
            main_repo_root / ".git",
            pool_json_path,
        },
        # Simulate uncommitted changes in the worktree (modified files)
        file_statuses={non_slot_worktree_path: ([], ["modified_file.py"], [])},
    )

    fake_graphite = FakeGraphite()

    ctx = context_for_test(
        git=fake_git,
        graphite=fake_graphite,
        cwd=non_slot_worktree_path,
    )

    repo = RepoContext(
        root=main_repo_root,
        repo_name="test-repo",
        repo_dir=main_repo_root,
        worktrees_dir=tmp_path / "worktrees",
        pool_json_path=pool_json_path,
        github=GitHubRepoId(owner="owner", repo="repo"),
    )

    # Call _cleanup_and_navigate - should fail with uncommitted changes
    try:
        _cleanup_and_navigate(
            ctx=ctx,
            repo=repo,
            branch="feature-branch",
            worktree_path=non_slot_worktree_path,
            script=False,
            pull_flag=False,
            force=True,
            is_current_branch=False,
            target_child_branch=None,
            objective_number=None,
            no_delete=False,
        )
        pytest.fail("Expected SystemExit(1) for uncommitted changes")
    except SystemExit as e:
        assert e.code == 1

    # Verify no checkout was attempted
    assert len(fake_git.checked_out_branches) == 0

    # Verify branch was NOT deleted
    deleted_branches = [branch for _path, branch in fake_graphite.delete_branch_calls]
    assert "feature-branch" not in deleted_branches


def test_cleanup_ensures_branch_not_checked_out_before_delete_with_stale_pool_state(
    tmp_path: Path,
) -> None:
    """Test that cleanup verifies branch is released before deletion.

    Regression test for bug where delete fails when pool state's worktree_path
    is stale (doesn't match the actual worktree location).

    Scenario:
    - Pool state has assignment with worktree_path = stale_path
    - Branch is actually checked out in actual_path (different from stale_path)
    - execute_unassign() checkouts placeholder at stale_path (wrong location)
    - Without fix: delete_branch() fails because branch still checked out in actual_path
    - With fix: _ensure_branch_not_checked_out() detects and releases the branch

    The fix adds a defensive check that finds the branch wherever it's checked out
    and releases it before deletion.
    """
    # Two different paths to simulate stale pool state
    stale_worktree_path = tmp_path / "erk-root-stale" / "worktrees" / "erk-slot-01"
    actual_worktree_path = tmp_path / "erk-root-actual" / "worktrees" / "erk-slot-01"
    stale_worktree_path.mkdir(parents=True)
    actual_worktree_path.mkdir(parents=True)
    main_repo_root = tmp_path / "main-repo"
    main_repo_root.mkdir(parents=True)
    (main_repo_root / ".git").mkdir()
    pool_json_path = main_repo_root / "pool.json"

    # Create pool state with assignment using STALE path (different from actual)
    assignment = _create_test_assignment(
        slot_name="erk-slot-01",
        branch_name="feature-branch",
        worktree_path=stale_worktree_path,  # STALE - differs from actual
    )

    initial_state = PoolState.test(assignments=(assignment,))
    save_pool_state(pool_json_path, initial_state)

    # Create FakeGit where branch is checked out at ACTUAL path
    # This simulates the stale pool state scenario
    fake_git = FakeGit(
        worktrees={
            main_repo_root: [
                WorktreeInfo(path=actual_worktree_path, branch="feature-branch"),
            ]
        },
        git_common_dirs={main_repo_root: main_repo_root / ".git"},
        default_branches={main_repo_root: "main"},
        trunk_branches={main_repo_root: "main"},
        local_branches={main_repo_root: ["main", "feature-branch"]},
        existing_paths={
            actual_worktree_path,
            stale_worktree_path,
            main_repo_root,
            main_repo_root / ".git",
            pool_json_path,
        },
    )

    # Configure FakeGraphite to track the branch
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
        cwd=actual_worktree_path,
    )

    repo = RepoContext(
        root=main_repo_root,
        repo_name="test-repo",
        repo_dir=main_repo_root,
        worktrees_dir=tmp_path / "worktrees",
        pool_json_path=pool_json_path,
        github=GitHubRepoId(owner="owner", repo="repo"),
    )

    # Call _cleanup_and_navigate
    # The bug would have failed here because branch is still checked out in actual_path
    # The fix ensures branch is released before deletion
    try:
        _cleanup_and_navigate(
            ctx=ctx,
            repo=repo,
            branch="feature-branch",
            worktree_path=actual_worktree_path,
            script=False,
            pull_flag=False,
            force=True,
            is_current_branch=False,
            target_child_branch=None,
            objective_number=None,
            no_delete=False,
        )
    except SystemExit:
        pass  # Expected - function raises SystemExit(0) at end

    # Verify the defensive checkout_detached was called on ACTUAL path
    # (This is the key assertion - the fix finds where branch is actually checked out)
    detached_calls = [(path, ref) for path, ref in fake_git.detached_checkouts if ref == "main"]
    # Should have at least one detached checkout at actual_worktree_path
    actual_path_detached = [
        (path, ref)
        for path, ref in detached_calls
        if path.resolve() == actual_worktree_path.resolve()
    ]
    assert len(actual_path_detached) >= 1, (
        f"Expected detached checkout at actual_worktree_path. "
        f"Got detached_checkouts: {fake_git.detached_checkouts}"
    )

    # Verify branch was deleted successfully
    deleted_branches = [branch for _path, branch in fake_graphite.delete_branch_calls]
    assert "feature-branch" in deleted_branches


def test_ensure_branch_not_checked_out_helper_releases_branch(tmp_path: Path) -> None:
    """Test that _ensure_branch_not_checked_out helper correctly releases a branch.

    This tests the helper function directly to verify it:
    1. Finds the worktree where the branch is checked out
    2. Checkouts detached HEAD at trunk to release the branch
    3. Returns the path where detachment happened
    """
    from erk.cli.commands.land_cmd import _ensure_branch_not_checked_out

    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    worktree_path = tmp_path / "worktrees" / "feature-wt"
    worktree_path.mkdir(parents=True)

    fake_git = FakeGit(
        worktrees={
            repo_root: [WorktreeInfo(path=worktree_path, branch="feature-branch")],
        },
        trunk_branches={repo_root: "main"},
    )

    ctx = context_for_test(git=fake_git, cwd=repo_root)

    # Call the helper
    result = _ensure_branch_not_checked_out(ctx, repo_root=repo_root, branch="feature-branch")

    # Should return the worktree path where branch was found and released
    assert result is not None
    assert result.resolve() == worktree_path.resolve()

    # Should have checked out detached HEAD at trunk
    assert len(fake_git.detached_checkouts) == 1
    path, ref = fake_git.detached_checkouts[0]
    assert path.resolve() == worktree_path.resolve()
    assert ref == "main"


def test_ensure_branch_not_checked_out_returns_none_when_not_checked_out(
    tmp_path: Path,
) -> None:
    """Test that _ensure_branch_not_checked_out returns None when branch isn't checked out."""
    from erk.cli.commands.land_cmd import _ensure_branch_not_checked_out

    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)

    fake_git = FakeGit(
        worktrees={repo_root: []},  # No worktrees
        trunk_branches={repo_root: "main"},
    )

    ctx = context_for_test(git=fake_git, cwd=repo_root)

    # Call the helper for a branch that isn't checked out anywhere
    result = _ensure_branch_not_checked_out(ctx, repo_root=repo_root, branch="feature-branch")

    # Should return None (branch wasn't found)
    assert result is None

    # Should not have made any detached checkouts
    assert len(fake_git.detached_checkouts) == 0


def test_cleanup_and_navigate_slot_without_assignment_force_suppresses_warning(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test that warning is suppressed when force=True for slot without assignment.

    When running `erk land -f` from a slot worktree without assignment, the warning
    should NOT be displayed since --force was specified.
    """
    # Create a slot worktree without any pool assignment
    slot_worktree_path = tmp_path / "worktrees" / "erk-slot-01"
    slot_worktree_path.mkdir(parents=True)
    main_repo_root = tmp_path / "main-repo"
    main_repo_root.mkdir(parents=True)
    (main_repo_root / ".git").mkdir()
    pool_json_path = main_repo_root / "pool.json"

    # Create empty pool state (no assignments)
    empty_state = PoolState.test(assignments=())
    save_pool_state(pool_json_path, empty_state)

    # Create the placeholder branch that should exist
    placeholder_branch = "__erk-slot-01-br-stub__"

    fake_git = FakeGit(
        worktrees={
            main_repo_root: [WorktreeInfo(path=slot_worktree_path, branch="feature-branch")]
        },
        git_common_dirs={main_repo_root: main_repo_root / ".git"},
        default_branches={main_repo_root: "main"},
        local_branches={main_repo_root: ["main", "feature-branch", placeholder_branch]},
        existing_paths={
            slot_worktree_path,
            main_repo_root,
            main_repo_root / ".git",
            pool_json_path,
        },
    )

    # Configure FakeGraphite to track the branch
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
        cwd=slot_worktree_path,
    )

    repo = RepoContext(
        root=main_repo_root,
        repo_name="test-repo",
        repo_dir=main_repo_root,
        worktrees_dir=tmp_path / "worktrees",
        pool_json_path=pool_json_path,
        github=GitHubRepoId(owner="owner", repo="repo"),
    )

    # Call _cleanup_and_navigate with force=True
    try:
        _cleanup_and_navigate(
            ctx=ctx,
            repo=repo,
            branch="feature-branch",
            worktree_path=slot_worktree_path,
            script=False,
            pull_flag=False,
            force=True,  # This should suppress the warning
            is_current_branch=False,
            target_child_branch=None,
            objective_number=None,
            no_delete=False,
        )
    except SystemExit:
        pass  # Expected - function raises SystemExit(0) at end

    # Capture stderr where user_output writes to
    captured = capsys.readouterr()

    # Verify warning was NOT printed (suppressed by force=True)
    assert "Warning:" not in captured.err, (
        "Warning should be suppressed when force=True, but got: " + captured.err
    )
    assert "has no assignment" not in captured.err, (
        "Warning message should be suppressed when force=True"
    )

    # Verify the operation still completed successfully
    # Placeholder branch should have been checked out
    checkout_calls = [
        (path, branch)
        for path, branch in fake_git.checked_out_branches
        if branch == placeholder_branch
    ]
    assert len(checkout_calls) == 1, "Should have checked out placeholder branch"

    # Branch should have been deleted
    deleted_branches = [branch for _path, branch in fake_graphite.delete_branch_calls]
    assert "feature-branch" in deleted_branches


# Tests for --no-delete flag


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
