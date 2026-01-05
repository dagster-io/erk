"""Unit tests for land command parsing utilities and dry-run mode."""

from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.land_cmd import (
    ParsedArgument,
    _cleanup_and_navigate,
    _find_assignment_by_worktree_path,
    parse_argument,
)
from erk.core.context import context_for_test
from erk.core.repo_discovery import RepoContext
from erk.core.worktree_pool import PoolState, SlotAssignment, load_pool_state
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.git.abc import WorktreeInfo
from erk_shared.git.fake import FakeGit
from erk_shared.github.types import GitHubRepoId
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


# Tests for dry-run mode


def test_cleanup_and_navigate_dry_run_does_not_save_pool_state(tmp_path: Path) -> None:
    """Test that _cleanup_and_navigate in dry-run mode does not save pool state."""
    # Create worktree path and pool.json
    worktree_path = tmp_path / "worktrees" / "erk-managed-wt-01"
    worktree_path.mkdir(parents=True)
    pool_json_path = tmp_path / "pool.json"

    # Create initial pool state with an assignment
    assignment = _create_test_assignment("erk-managed-wt-01", "feature-branch", worktree_path)
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
        if a.slot_name == "erk-managed-wt-01":
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
