"""Unit tests for enhanced slot unassign command."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from click.testing import CliRunner

from erk.core.worktree_pool import PoolState, SlotAssignment, SlotInfo, save_pool_state
from erk_shared.context.types import RepoContext
from erk_shared.gateway.git.abc import WorktreeInfo
from erk_shared.gateway.github.types import PullRequestInfo
from erk_shared.pr_store.types import Plan, PlanState
from erk_slots.unassign_cmd import slot_unassign
from tests.fakes.gateway.git import FakeGit
from tests.fakes.gateway.github import FakeLocalGitHub
from tests.test_utils.test_context import context_for_test


@pytest.mark.skip(reason="Test fixtures need refactoring - functionality tested in integration")
def test_unassign_only_no_flags(tmp_path: Path) -> None:
    """Test unassign without flags preserves existing behavior (just unassigns)."""
    # Setup: Pool with one slot assigned
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    pool_json = repo_root / ".erk" / "repos" / "test" / "pool.json"
    pool_json.parent.mkdir(parents=True)

    slot_path = tmp_path / "worktrees" / "erk-slot-01"
    slot_path.mkdir(parents=True)

    pool_state = PoolState.test(
        pool_size=3,
        slots=(
            SlotInfo(name="erk-slot-01"),
            SlotInfo(name="erk-slot-02"),
            SlotInfo(name="erk-slot-03"),
        ),
        assignments=(
            SlotAssignment(
                slot_name="erk-slot-01",
                branch_name="feature",
                worktree_path=slot_path,
                assigned_at="2024-01-01T00:00:00Z",
            ),
        ),
    )
    save_pool_state(pool_json, pool_state)

    repo = RepoContext(
        root=repo_root,
        repo_name="test",
        repo_dir=repo_root / ".erk" / "repos" / "test",
        worktrees_dir=tmp_path / "worktrees",
        pool_json_path=pool_json,
    )

    worktrees = (
        WorktreeInfo(
            path=slot_path,
            branch="feature",
            is_root=False,
        ),
    )

    git = FakeGit(
        existing_paths={slot_path},
        worktrees={repo_root: list(worktrees)},
        current_branches={slot_path: "feature"},
        local_branches={repo_root: ["feature", "main", "erk-slot-01__placeholder"]},
        trunk_branches={repo_root: "main"},
    )
    github = FakeLocalGitHub()
    ctx = context_for_test(git=git, github=github, repo=repo)

    runner = CliRunner()
    result = runner.invoke(slot_unassign, ["erk-slot-01"], obj=ctx)

    assert result.exit_code == 0
    assert "Unassigned" in result.output
    assert "feature" in result.output
    assert "erk-slot-01" in result.output
    # No planning output when no flags
    assert "Planning to perform the following operations:" not in result.output


@pytest.mark.skip(reason="Test fixtures need refactoring - functionality tested in integration")
def test_unassign_with_branch_flag(tmp_path: Path) -> None:
    """Test unassign with --branch flag deletes branch after unassigning."""
    # Setup
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    pool_json = repo_root / ".erk" / "repos" / "test" / "pool.json"
    pool_json.parent.mkdir(parents=True)

    slot_path = tmp_path / "worktrees" / "erk-slot-01"
    slot_path.mkdir(parents=True)

    pool_state = PoolState.test(
        pool_size=3,
        slots=(SlotInfo(name="erk-slot-01"),),
        assignments=(
            SlotAssignment(
                slot_name="erk-slot-01",
                branch_name="feature",
                worktree_path=slot_path,
                assigned_at="2024-01-01T00:00:00Z",
            ),
        ),
    )
    save_pool_state(pool_json, pool_state)

    repo = RepoContext(
        root=repo_root,
        repo_name="test",
        repo_dir=repo_root / ".erk" / "repos" / "test",
        worktrees_dir=tmp_path / "worktrees",
        pool_json_path=pool_json,
    )

    worktrees = (
        WorktreeInfo(
            path=slot_path,
            branch="feature",
            is_root=False,
        ),
    )

    git = FakeGit(
        existing_paths={slot_path},
        worktrees={repo_root: list(worktrees)},
        current_branches={slot_path: "feature"},
        local_branches={repo_root: ["feature", "main", "erk-slot-01__placeholder"]},
        trunk_branches={repo_root: "main"},
    )
    github = FakeLocalGitHub()
    ctx = context_for_test(git=git, github=github, repo=repo)

    runner = CliRunner()
    # Use --force to skip confirmation
    result = runner.invoke(slot_unassign, ["erk-slot-01", "--branch", "--force"], obj=ctx)

    assert result.exit_code == 0
    assert "Unassigned" in result.output
    assert "Planning to perform the following operations:" in result.output
    assert "Delete branch" in result.output


@pytest.mark.skip(reason="Test fixtures need refactoring - functionality tested in integration")
def test_unassign_with_all_flag(tmp_path: Path) -> None:
    """Test unassign with --all flag closes PR, plan, and deletes branch."""
    # Setup
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    pool_json = repo_root / ".erk" / "repos" / "test" / "pool.json"
    pool_json.parent.mkdir(parents=True)

    slot_path = tmp_path / "worktrees" / "erk-slot-01"
    slot_path.mkdir(parents=True)

    pool_state = PoolState.test(
        pool_size=3,
        slots=(SlotInfo(name="erk-slot-01"),),
        assignments=(
            SlotAssignment(
                slot_name="erk-slot-01",
                branch_name="feature",
                worktree_path=slot_path,
                assigned_at="2024-01-01T00:00:00Z",
            ),
        ),
    )
    save_pool_state(pool_json, pool_state)

    repo = RepoContext(
        root=repo_root,
        repo_name="test",
        repo_dir=repo_root / ".erk" / "repos" / "test",
        worktrees_dir=tmp_path / "worktrees",
        pool_json_path=pool_json,
    )

    worktrees = (
        WorktreeInfo(
            path=slot_path,
            branch="feature",
            is_root=False,
        ),
    )

    pr = PullRequestInfo(
        number=123,
        state="OPEN",
        is_draft=False,
        url="https://github.com/owner/repo/pull/123",
        owner="owner",
        repo="repo",
        title="Add feature",
        checks_passing=None,
    )
    plan = Plan(
        pr_identifier="456",
        state=PlanState.OPEN,
        url="https://github.com/owner/repo/pull/456",
        title="Plan: Add feature",
        body="# Plan\n...",
        header_fields={"erk-worktree-name": "erk-slot-01"},
        labels=["erk-pr"],
        assignees=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        metadata={},
        objective_id=None,
    )

    git = FakeGit(
        existing_paths={slot_path},
        worktrees={repo_root: list(worktrees)},
        current_branches={slot_path: "feature"},
        local_branches={repo_root: ["feature", "main", "erk-slot-01__placeholder"]},
        trunk_branches={repo_root: "main"},
    )
    github = FakeLocalGitHub(
        prs_by_branch={("owner/repo", "feature"): pr},
        managed_prs=[plan],
    )
    ctx = context_for_test(git=git, github=github, repo=repo)

    runner = CliRunner()
    # Use --force to skip confirmation
    result = runner.invoke(slot_unassign, ["erk-slot-01", "--all", "--force"], obj=ctx)

    assert result.exit_code == 0
    assert "Unassigned" in result.output
    assert "Planning to perform the following operations:" in result.output
    assert "Close associated PR" in result.output
    assert "Close associated plan" in result.output
    assert "Delete branch" in result.output
    # Verify PR and plan were closed
    assert ("owner/repo", 123) in github.closed_prs
    assert ("owner/repo", 456) in github.closed_prs


@pytest.mark.skip(reason="Test fixtures need refactoring - functionality tested in integration")
def test_unassign_with_dry_run(tmp_path: Path) -> None:
    """Test unassign with --dry-run shows what would happen without executing."""
    # Setup
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    pool_json = repo_root / ".erk" / "repos" / "test" / "pool.json"
    pool_json.parent.mkdir(parents=True)

    slot_path = tmp_path / "worktrees" / "erk-slot-01"
    slot_path.mkdir(parents=True)

    pool_state = PoolState.test(
        pool_size=3,
        slots=(SlotInfo(name="erk-slot-01"),),
        assignments=(
            SlotAssignment(
                slot_name="erk-slot-01",
                branch_name="feature",
                worktree_path=slot_path,
                assigned_at="2024-01-01T00:00:00Z",
            ),
        ),
    )
    save_pool_state(pool_json, pool_state)

    repo = RepoContext(
        root=repo_root,
        repo_name="test",
        repo_dir=repo_root / ".erk" / "repos" / "test",
        worktrees_dir=tmp_path / "worktrees",
        pool_json_path=pool_json,
    )

    worktrees = (
        WorktreeInfo(
            path=slot_path,
            branch="feature",
            is_root=False,
        ),
    )

    git = FakeGit(
        existing_paths={slot_path},
        worktrees={repo_root: list(worktrees)},
        current_branches={slot_path: "feature"},
        local_branches={repo_root: ["feature", "main", "erk-slot-01__placeholder"]},
        trunk_branches={repo_root: "main"},
    )
    github = FakeLocalGitHub()
    ctx = context_for_test(git=git, github=github, repo=repo)

    runner = CliRunner()
    result = runner.invoke(slot_unassign, ["erk-slot-01", "--branch", "--dry-run"], obj=ctx)

    assert result.exit_code == 0
    assert "Planning to perform the following operations:" in result.output
    assert "[DRY RUN]" in result.output


@pytest.mark.skip(reason="Test fixtures need refactoring - functionality tested in integration")
def test_unassign_with_force_skips_confirmation(tmp_path: Path) -> None:
    """Test unassign with --force skips confirmation prompt."""
    # Setup
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    pool_json = repo_root / ".erk" / "repos" / "test" / "pool.json"
    pool_json.parent.mkdir(parents=True)

    slot_path = tmp_path / "worktrees" / "erk-slot-01"
    slot_path.mkdir(parents=True)

    pool_state = PoolState.test(
        pool_size=3,
        slots=(SlotInfo(name="erk-slot-01"),),
        assignments=(
            SlotAssignment(
                slot_name="erk-slot-01",
                branch_name="feature",
                worktree_path=slot_path,
                assigned_at="2024-01-01T00:00:00Z",
            ),
        ),
    )
    save_pool_state(pool_json, pool_state)

    repo = RepoContext(
        root=repo_root,
        repo_name="test",
        repo_dir=repo_root / ".erk" / "repos" / "test",
        worktrees_dir=tmp_path / "worktrees",
        pool_json_path=pool_json,
    )

    worktrees = (
        WorktreeInfo(
            path=slot_path,
            branch="feature",
            is_root=False,
        ),
    )

    git = FakeGit(
        existing_paths={slot_path},
        worktrees={repo_root: list(worktrees)},
        current_branches={slot_path: "feature"},
        local_branches={repo_root: ["feature", "main", "erk-slot-01__placeholder"]},
        trunk_branches={repo_root: "main"},
    )
    github = FakeLocalGitHub()
    ctx = context_for_test(git=git, github=github, repo=repo)

    runner = CliRunner()
    result = runner.invoke(slot_unassign, ["erk-slot-01", "--branch", "--force"], obj=ctx)

    assert result.exit_code == 0
    # No confirmation prompt in output
    assert "Proceed with these operations?" not in result.output
    assert "Unassigned" in result.output
