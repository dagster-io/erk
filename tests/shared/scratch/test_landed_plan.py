"""Unit tests for landed plan scratch state.

Layer 3 (Pure Unit Tests): Tests for landed plan state with tmp_path fixture.
"""

from pathlib import Path

from erk_shared.scratch.landed_plan import (
    LandedPlanState,
    read_landed_plan_state,
    write_landed_plan_state,
)


def test_write_and_read_round_trip(tmp_path: Path) -> None:
    """Write and read round-trip preserves all fields."""
    # Create repo structure
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    state = LandedPlanState(
        plan_issue=123,
        objective_issue=42,
        pr_number=456,
        pr_title="Add new feature",
    )

    session_id = "test-session-abc123"

    # Write state
    file_path = write_landed_plan_state(session_id, state, repo_root=repo_root)

    # Verify file was created in expected location
    assert file_path.exists()
    assert ".erk/scratch/sessions/test-session-abc123/last-landed-plan.json" in str(file_path)

    # Read state back
    result = read_landed_plan_state(session_id, repo_root=repo_root)

    assert result is not None
    assert result.plan_issue == 123
    assert result.objective_issue == 42
    assert result.pr_number == 456
    assert result.pr_title == "Add new feature"


def test_read_returns_none_when_file_missing(tmp_path: Path) -> None:
    """Read returns None when file doesn't exist."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    session_id = "nonexistent-session"

    result = read_landed_plan_state(session_id, repo_root=repo_root)
    assert result is None


def test_write_creates_directory_structure(tmp_path: Path) -> None:
    """Write creates nested directory structure if not exists."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    state = LandedPlanState(
        plan_issue=1,
        objective_issue=2,
        pr_number=3,
        pr_title="Test",
    )

    session_id = "new-session"

    # Directory should not exist yet
    scratch_dir = repo_root / ".erk" / "scratch" / "sessions" / session_id
    assert not scratch_dir.exists()

    # Write should create it
    write_landed_plan_state(session_id, state, repo_root=repo_root)

    assert scratch_dir.exists()


def test_write_overwrites_existing_file(tmp_path: Path) -> None:
    """Write overwrites existing file with new state."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    session_id = "test-session"

    # Write first state
    state1 = LandedPlanState(
        plan_issue=1,
        objective_issue=10,
        pr_number=100,
        pr_title="First",
    )
    write_landed_plan_state(session_id, state1, repo_root=repo_root)

    # Write second state (should overwrite)
    state2 = LandedPlanState(
        plan_issue=2,
        objective_issue=20,
        pr_number=200,
        pr_title="Second",
    )
    write_landed_plan_state(session_id, state2, repo_root=repo_root)

    # Read should return second state
    result = read_landed_plan_state(session_id, repo_root=repo_root)

    assert result is not None
    assert result.plan_issue == 2
    assert result.objective_issue == 20
    assert result.pr_number == 200
    assert result.pr_title == "Second"


def test_landed_plan_state_is_frozen() -> None:
    """LandedPlanState is immutable (frozen dataclass)."""
    state = LandedPlanState(
        plan_issue=1,
        objective_issue=2,
        pr_number=3,
        pr_title="Test",
    )

    # Should be hashable (frozen dataclasses are)
    hash(state)

    # Should raise AttributeError on assignment attempt
    try:
        state.plan_issue = 999  # type: ignore[misc]
        raise AssertionError("Should have raised AttributeError")
    except AttributeError:
        pass
