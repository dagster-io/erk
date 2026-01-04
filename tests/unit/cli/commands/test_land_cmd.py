"""Unit tests for land command parsing utilities."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk.cli.commands.land_cmd import (
    ParsedArgument,
    _cleanup_and_navigate,
    parse_argument,
)
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import (
    PoolState,
    SlotAssignment,
    SlotInfo,
    load_pool_state,
    save_pool_state,
)
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from tests.fakes.script_writer import FakeScriptWriter
from tests.fakes.shell import FakeShell


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


# -----------------------------------------------------------------------------
# Tests for _cleanup_and_navigate with pool slots
# -----------------------------------------------------------------------------


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


def test_cleanup_and_navigate_unassigns_managed_slot(tmp_path: Path) -> None:
    """Test that landing in a managed slot unassigns instead of deleting."""
    # Setup directories
    root_worktree = tmp_path / "repo"
    root_worktree.mkdir()
    git_dir = root_worktree / ".git"
    git_dir.mkdir()

    erk_root = tmp_path / "erks"
    erk_root.mkdir()
    repo_dir = erk_root / "repos" / root_worktree.name
    repo_dir.mkdir(parents=True)
    worktrees_dir = repo_dir / "worktrees"
    worktrees_dir.mkdir()

    # Create managed worktree directory
    worktree_path = worktrees_dir / "erk-managed-wt-01"
    worktree_path.mkdir()

    repo = RepoContext(
        root=root_worktree,
        repo_name=root_worktree.name,
        repo_dir=repo_dir,
        worktrees_dir=worktrees_dir,
        pool_json_path=repo_dir / "pool.json",
    )

    # Create pool state with assignment
    assignment = _create_test_assignment("erk-managed-wt-01", "feature-branch", worktree_path)
    initial_state = PoolState.test(
        slots=(SlotInfo(name="erk-managed-wt-01"),),
        assignments=(assignment,),
    )
    save_pool_state(repo.pool_json_path, initial_state)

    # Setup FakeGit
    git_ops = FakeGit(
        worktrees={
            root_worktree: [
                WorktreeInfo(path=root_worktree, branch="main", is_root=True),
                WorktreeInfo(path=worktree_path, branch="feature-branch"),
            ]
        },
        current_branches={root_worktree: "main", worktree_path: "feature-branch"},
        git_common_dirs={root_worktree: git_dir, worktree_path: git_dir},
        default_branches={root_worktree: "main"},
        trunk_branches={root_worktree: "main"},
        local_branches={root_worktree: ["main", "feature-branch", "__erk-slot-01-placeholder__"]},
    )

    global_config = GlobalConfig.test(erk_root)

    ctx = context_for_test(
        cwd=worktree_path,
        git=git_ops,
        graphite=FakeGraphite(),
        github=FakeGitHub(),
        shell=FakeShell(),
        global_config=global_config,
        script_writer=FakeScriptWriter(),
    )

    # Call _cleanup_and_navigate (it raises SystemExit for navigation)
    with pytest.raises(SystemExit):
        _cleanup_and_navigate(
            ctx=ctx,
            repo=repo,
            branch="feature-branch",
            worktree_path=worktree_path,
            script=True,
            pull_flag=False,
            force=True,
            is_current_branch=True,
            target_child_branch=None,
        )

    # Verify assignment was removed from pool state
    state = load_pool_state(repo.pool_json_path)
    assert state is not None
    assert len(state.assignments) == 0

    # Verify placeholder branch was checked out (unassign behavior)
    assert (worktree_path, "__erk-slot-01-placeholder__") in git_ops.checked_out_branches

    # Verify branch was deleted (PR merged, so branch should be removed)
    assert "feature-branch" in git_ops.deleted_branches


def test_cleanup_and_navigate_deletes_regular_worktree(tmp_path: Path) -> None:
    """Test that landing in a non-pool worktree uses existing deletion logic."""
    # Setup directories
    root_worktree = tmp_path / "repo"
    root_worktree.mkdir()
    git_dir = root_worktree / ".git"
    git_dir.mkdir()

    erk_root = tmp_path / "erks"
    erk_root.mkdir()
    repo_dir = erk_root / "repos" / root_worktree.name
    repo_dir.mkdir(parents=True)
    worktrees_dir = repo_dir / "worktrees"
    worktrees_dir.mkdir()

    # Create a regular (non-pool) worktree directory
    worktree_path = worktrees_dir / "feature-branch"  # Not named erk-managed-wt-XX
    worktree_path.mkdir()

    repo = RepoContext(
        root=root_worktree,
        repo_name=root_worktree.name,
        repo_dir=repo_dir,
        worktrees_dir=worktrees_dir,
        pool_json_path=repo_dir / "pool.json",
    )

    # Setup FakeGit
    git_ops = FakeGit(
        worktrees={
            root_worktree: [
                WorktreeInfo(path=root_worktree, branch="main", is_root=True),
                WorktreeInfo(path=worktree_path, branch="feature-branch"),
            ]
        },
        current_branches={root_worktree: "main", worktree_path: "feature-branch"},
        git_common_dirs={root_worktree: git_dir, worktree_path: git_dir},
        default_branches={root_worktree: "main"},
        trunk_branches={root_worktree: "main"},
        local_branches={root_worktree: ["main", "feature-branch"]},
    )

    global_config = GlobalConfig.test(erk_root)

    ctx = context_for_test(
        cwd=worktree_path,
        git=git_ops,
        graphite=FakeGraphite(),
        github=FakeGitHub(),
        shell=FakeShell(),
        global_config=global_config,
        script_writer=FakeScriptWriter(),
    )

    # Call _cleanup_and_navigate (it raises SystemExit for navigation)
    with pytest.raises(SystemExit):
        _cleanup_and_navigate(
            ctx=ctx,
            repo=repo,
            branch="feature-branch",
            worktree_path=worktree_path,
            script=True,
            pull_flag=False,
            force=True,
            is_current_branch=True,
            target_child_branch=None,
        )

    # Verify worktree was removed (deletion logic, not unassign)
    assert worktree_path in git_ops.removed_worktrees

    # Verify branch was deleted with graphite
    assert "feature-branch" in git_ops.deleted_branches


def test_cleanup_and_navigate_handles_stale_pool_assignment(tmp_path: Path) -> None:
    """Test that a worktree named like pool slot but without assignment falls back to deletion."""
    # Setup directories
    root_worktree = tmp_path / "repo"
    root_worktree.mkdir()
    git_dir = root_worktree / ".git"
    git_dir.mkdir()

    erk_root = tmp_path / "erks"
    erk_root.mkdir()
    repo_dir = erk_root / "repos" / root_worktree.name
    repo_dir.mkdir(parents=True)
    worktrees_dir = repo_dir / "worktrees"
    worktrees_dir.mkdir()

    # Create worktree with pool slot name but no assignment in pool state
    worktree_path = worktrees_dir / "erk-managed-wt-01"  # Looks like pool slot
    worktree_path.mkdir()

    repo = RepoContext(
        root=root_worktree,
        repo_name=root_worktree.name,
        repo_dir=repo_dir,
        worktrees_dir=worktrees_dir,
        pool_json_path=repo_dir / "pool.json",
    )

    # Create empty pool state (no assignments - stale state)
    initial_state = PoolState.test(
        slots=(SlotInfo(name="erk-managed-wt-01"),),
        assignments=(),  # No assignments
    )
    save_pool_state(repo.pool_json_path, initial_state)

    # Setup FakeGit
    git_ops = FakeGit(
        worktrees={
            root_worktree: [
                WorktreeInfo(path=root_worktree, branch="main", is_root=True),
                WorktreeInfo(path=worktree_path, branch="feature-branch"),
            ]
        },
        current_branches={root_worktree: "main", worktree_path: "feature-branch"},
        git_common_dirs={root_worktree: git_dir, worktree_path: git_dir},
        default_branches={root_worktree: "main"},
        trunk_branches={root_worktree: "main"},
        local_branches={root_worktree: ["main", "feature-branch"]},
    )

    global_config = GlobalConfig.test(erk_root)

    ctx = context_for_test(
        cwd=worktree_path,
        git=git_ops,
        graphite=FakeGraphite(),
        github=FakeGitHub(),
        shell=FakeShell(),
        global_config=global_config,
        script_writer=FakeScriptWriter(),
    )

    # Call _cleanup_and_navigate (it raises SystemExit for navigation)
    with pytest.raises(SystemExit):
        _cleanup_and_navigate(
            ctx=ctx,
            repo=repo,
            branch="feature-branch",
            worktree_path=worktree_path,
            script=True,
            pull_flag=False,
            force=True,
            is_current_branch=True,
            target_child_branch=None,
        )

    # Verify worktree was removed (fallback to deletion logic)
    assert worktree_path in git_ops.removed_worktrees

    # Verify branch was deleted with graphite
    assert "feature-branch" in git_ops.deleted_branches

    # Verify pool state is unchanged (still no assignments)
    state = load_pool_state(repo.pool_json_path)
    assert state is not None
    assert len(state.assignments) == 0
