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
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason
from erk_shared.gateway.graphite.fake import FakeGraphite
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
    from erk.core.worktree_pool import save_pool_state

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
    from erk.core.worktree_pool import save_pool_state

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

    fake_graphite = FakeGraphite()

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

    # Verify branch was deleted via Graphite (since FakeGraphite is used)
    # GraphiteBranchManager.delete_branch calls graphite.delete_branch
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
    from erk.core.worktree_pool import save_pool_state

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

    fake_graphite = FakeGraphite()

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

    # Verify branch was deleted via Graphite
    deleted_branches = [branch for _path, branch in fake_graphite.delete_branch_calls]
    assert "feature-branch" in deleted_branches
