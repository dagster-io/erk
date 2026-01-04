"""Unit tests for land command parsing utilities."""

from datetime import UTC, datetime
from pathlib import Path

from erk.cli.commands.land_cmd import (
    ParsedArgument,
    _find_assignment_by_worktree_path,
    parse_argument,
)
from erk.core.worktree_pool import PoolState, SlotAssignment


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


# Tests for _find_assignment_by_worktree_path


def test_find_assignment_by_worktree_path_finds_matching_slot(tmp_path: Path) -> None:
    """Test that _find_assignment_by_worktree_path finds a matching slot assignment."""
    worktree_path = tmp_path / "worktrees" / "erk-managed-wt-01"
    worktree_path.mkdir(parents=True)

    assignment = _create_test_assignment("erk-managed-wt-01", "feature-branch", worktree_path)
    state = PoolState.test(assignments=(assignment,))

    result = _find_assignment_by_worktree_path(state, worktree_path)

    assert result is not None
    assert result.slot_name == "erk-managed-wt-01"
    assert result.branch_name == "feature-branch"


def test_find_assignment_by_worktree_path_returns_none_for_non_slot(tmp_path: Path) -> None:
    """Test that _find_assignment_by_worktree_path returns None for non-slot worktrees."""
    slot_worktree = tmp_path / "worktrees" / "erk-managed-wt-01"
    slot_worktree.mkdir(parents=True)
    regular_worktree = tmp_path / "worktrees" / "regular-worktree"
    regular_worktree.mkdir(parents=True)

    assignment = _create_test_assignment("erk-managed-wt-01", "feature-branch", slot_worktree)
    state = PoolState.test(assignments=(assignment,))

    result = _find_assignment_by_worktree_path(state, regular_worktree)

    assert result is None


def test_find_assignment_by_worktree_path_returns_none_for_empty_pool(tmp_path: Path) -> None:
    """Test that _find_assignment_by_worktree_path returns None when pool has no assignments."""
    worktree_path = tmp_path / "worktrees" / "some-worktree"
    worktree_path.mkdir(parents=True)

    state = PoolState.test(assignments=())

    result = _find_assignment_by_worktree_path(state, worktree_path)

    assert result is None


def test_find_assignment_by_worktree_path_returns_none_for_nonexistent_path(
    tmp_path: Path,
) -> None:
    """Test that _find_assignment_by_worktree_path returns None for nonexistent paths."""
    slot_worktree = tmp_path / "worktrees" / "erk-managed-wt-01"
    slot_worktree.mkdir(parents=True)
    nonexistent_path = tmp_path / "worktrees" / "nonexistent"

    assignment = _create_test_assignment("erk-managed-wt-01", "feature-branch", slot_worktree)
    state = PoolState.test(assignments=(assignment,))

    result = _find_assignment_by_worktree_path(state, nonexistent_path)

    assert result is None


def test_find_assignment_by_worktree_path_handles_multiple_assignments(tmp_path: Path) -> None:
    """Test that _find_assignment_by_worktree_path finds correct assignment among multiple."""
    wt1 = tmp_path / "worktrees" / "erk-managed-wt-01"
    wt1.mkdir(parents=True)
    wt2 = tmp_path / "worktrees" / "erk-managed-wt-02"
    wt2.mkdir(parents=True)

    assignment1 = _create_test_assignment("erk-managed-wt-01", "feature-a", wt1)
    assignment2 = _create_test_assignment("erk-managed-wt-02", "feature-b", wt2)
    state = PoolState.test(assignments=(assignment1, assignment2))

    result = _find_assignment_by_worktree_path(state, wt2)

    assert result is not None
    assert result.slot_name == "erk-managed-wt-02"
    assert result.branch_name == "feature-b"
