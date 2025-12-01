"""Unit tests for FakeGitHub implementation.

These tests verify that the fake implementation behaves correctly and reliably.
Testing the fake ensures all higher-layer tests using FakeGitHub are reliable.
"""

from pathlib import Path

from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import WorkflowRun


def test_get_workflow_run_returns_correct_run_by_id() -> None:
    """Test that get_workflow_run returns the correct workflow run when found."""
    # Arrange
    run1 = WorkflowRun(
        run_id="123",
        status="completed",
        conclusion="success",
        branch="main",
        head_sha="abc",
    )
    run2 = WorkflowRun(
        run_id="456",
        status="in_progress",
        conclusion=None,
        branch="feature",
        head_sha="def",
    )
    github = FakeGitHub(workflow_runs=[run1, run2])
    repo_root = Path("/fake/repo")

    # Act
    result = github.get_workflow_run(repo_root, "456")

    # Assert
    assert result is not None, "Expected to find workflow run"
    assert result.run_id == "456"
    assert result.status == "in_progress"
    assert result.branch == "feature"


def test_get_workflow_run_returns_none_when_not_found() -> None:
    """Test that get_workflow_run returns None when run ID not found."""
    # Arrange
    run1 = WorkflowRun(
        run_id="123",
        status="completed",
        conclusion="success",
        branch="main",
        head_sha="abc",
    )
    github = FakeGitHub(workflow_runs=[run1])
    repo_root = Path("/fake/repo")

    # Act
    result = github.get_workflow_run(repo_root, "999")

    # Assert
    assert result is None, "Expected None for non-existent run ID"


def test_get_workflow_run_handles_empty_workflow_runs() -> None:
    """Test that get_workflow_run returns None when no workflow runs configured."""
    # Arrange
    github = FakeGitHub(workflow_runs=[])
    repo_root = Path("/fake/repo")

    # Act
    result = github.get_workflow_run(repo_root, "123")

    # Assert
    assert result is None, "Expected None when no workflow runs configured"


def test_get_workflow_runs_by_branches_prefers_in_progress_over_completed() -> None:
    """Test priority logic: in-progress runs preferred over completed runs."""
    # Arrange
    completed_run = WorkflowRun(
        run_id="111",
        status="completed",
        conclusion="success",
        branch="feature",
        head_sha="abc",
    )
    in_progress_run = WorkflowRun(
        run_id="222",
        status="in_progress",
        conclusion=None,
        branch="feature",
        head_sha="def",
    )
    github = FakeGitHub(workflow_runs=[completed_run, in_progress_run])
    repo_root = Path("/fake/repo")

    # Act
    result = github.get_workflow_runs_by_branches(repo_root, "dispatch-erk-queue.yml", ["feature"])

    # Assert
    assert "feature" in result
    assert result["feature"] is not None
    assert result["feature"].run_id == "222", "Expected in-progress run to be prioritized"
    assert result["feature"].status == "in_progress"


def test_get_workflow_runs_by_branches_prefers_queued_over_completed() -> None:
    """Test priority logic: queued runs preferred over completed runs."""
    # Arrange
    completed_run = WorkflowRun(
        run_id="333",
        status="completed",
        conclusion="success",
        branch="feature",
        head_sha="ghi",
    )
    queued_run = WorkflowRun(
        run_id="444",
        status="queued",
        conclusion=None,
        branch="feature",
        head_sha="jkl",
    )
    github = FakeGitHub(workflow_runs=[completed_run, queued_run])
    repo_root = Path("/fake/repo")

    # Act
    result = github.get_workflow_runs_by_branches(repo_root, "dispatch-erk-queue.yml", ["feature"])

    # Assert
    assert "feature" in result
    assert result["feature"] is not None
    assert result["feature"].run_id == "444", "Expected queued run to be prioritized"
    assert result["feature"].status == "queued"


def test_get_workflow_runs_by_branches_prefers_failed_over_success() -> None:
    """Test priority logic: failed runs preferred over successful completed runs."""
    # Arrange
    success_run = WorkflowRun(
        run_id="555",
        status="completed",
        conclusion="success",
        branch="feature",
        head_sha="mno",
    )
    failed_run = WorkflowRun(
        run_id="666",
        status="completed",
        conclusion="failure",
        branch="feature",
        head_sha="pqr",
    )
    github = FakeGitHub(workflow_runs=[success_run, failed_run])
    repo_root = Path("/fake/repo")

    # Act
    result = github.get_workflow_runs_by_branches(repo_root, "dispatch-erk-queue.yml", ["feature"])

    # Assert
    assert "feature" in result
    assert result["feature"] is not None
    assert result["feature"].run_id == "666", "Expected failed run to be prioritized"
    assert result["feature"].conclusion == "failure"


def test_get_workflow_runs_by_branches_returns_most_recent_when_multiple_completed() -> None:
    """Test that most recent completed run is returned when multiple exist."""
    # Arrange: Two completed successful runs (first in list is most recent)
    recent_run = WorkflowRun(
        run_id="777",
        status="completed",
        conclusion="success",
        branch="feature",
        head_sha="stu",
    )
    older_run = WorkflowRun(
        run_id="888",
        status="completed",
        conclusion="success",
        branch="feature",
        head_sha="vwx",
    )
    github = FakeGitHub(workflow_runs=[recent_run, older_run])
    repo_root = Path("/fake/repo")

    # Act
    result = github.get_workflow_runs_by_branches(repo_root, "dispatch-erk-queue.yml", ["feature"])

    # Assert
    assert "feature" in result
    assert result["feature"] is not None
    assert result["feature"].run_id == "777", "Expected first (most recent) run"


def test_get_workflow_runs_by_branches_handles_empty_branches() -> None:
    """Test that batch query handles empty branches list gracefully."""
    # Arrange
    run = WorkflowRun(
        run_id="999",
        status="completed",
        conclusion="success",
        branch="feature",
        head_sha="xyz",
    )
    github = FakeGitHub(workflow_runs=[run])
    repo_root = Path("/fake/repo")

    # Act
    result = github.get_workflow_runs_by_branches(repo_root, "dispatch-erk-queue.yml", [])

    # Assert
    assert result == {}, "Expected empty dict for empty branches list"


def test_get_workflow_runs_by_branches_handles_no_matching_runs() -> None:
    """Test that batch query returns empty dict when no runs match branches."""
    # Arrange
    run = WorkflowRun(
        run_id="101",
        status="completed",
        conclusion="success",
        branch="other-branch",
        head_sha="aaa",
    )
    github = FakeGitHub(workflow_runs=[run])
    repo_root = Path("/fake/repo")

    # Act
    result = github.get_workflow_runs_by_branches(
        repo_root, "dispatch-erk-queue.yml", ["feature", "main"]
    )

    # Assert
    assert result == {}, "Expected empty dict when no runs match branches"


def test_get_workflow_runs_by_branches_handles_multiple_branches() -> None:
    """Test batch query returns correct runs for multiple branches."""
    # Arrange
    run1 = WorkflowRun(
        run_id="201",
        status="completed",
        conclusion="success",
        branch="feature-1",
        head_sha="bbb",
    )
    run2 = WorkflowRun(
        run_id="202",
        status="in_progress",
        conclusion=None,
        branch="feature-2",
        head_sha="ccc",
    )
    run3 = WorkflowRun(
        run_id="203",
        status="completed",
        conclusion="failure",
        branch="feature-3",
        head_sha="ddd",
    )
    github = FakeGitHub(workflow_runs=[run1, run2, run3])
    repo_root = Path("/fake/repo")

    # Act
    result = github.get_workflow_runs_by_branches(
        repo_root, "dispatch-erk-queue.yml", ["feature-1", "feature-2", "feature-3"]
    )

    # Assert
    assert len(result) == 3, "Expected runs for all three branches"
    assert result["feature-1"].run_id == "201"
    assert result["feature-2"].run_id == "202"
    assert result["feature-3"].run_id == "203"


def test_get_workflow_runs_by_branches_omits_branches_without_runs() -> None:
    """Test that batch query only includes branches with workflow runs."""
    # Arrange
    run = WorkflowRun(
        run_id="301",
        status="completed",
        conclusion="success",
        branch="has-run",
        head_sha="eee",
    )
    github = FakeGitHub(workflow_runs=[run])
    repo_root = Path("/fake/repo")

    # Act
    result = github.get_workflow_runs_by_branches(
        repo_root, "dispatch-erk-queue.yml", ["has-run", "no-run"]
    )

    # Assert
    assert "has-run" in result
    assert "no-run" not in result, "Branch without runs should not be in result"


def test_get_workflow_runs_by_branches_priority_order() -> None:
    """Test complete priority order: active > failed > completed."""
    # Arrange: Create one branch with runs in all states
    completed_success = WorkflowRun(
        run_id="401",
        status="completed",
        conclusion="success",
        branch="test",
        head_sha="fff",
    )
    completed_failure = WorkflowRun(
        run_id="402",
        status="completed",
        conclusion="failure",
        branch="test",
        head_sha="ggg",
    )
    in_progress = WorkflowRun(
        run_id="403",
        status="in_progress",
        conclusion=None,
        branch="test",
        head_sha="hhh",
    )

    # Test 1: Only completed runs (failure preferred)
    github1 = FakeGitHub(workflow_runs=[completed_success, completed_failure])
    result1 = github1.get_workflow_runs_by_branches(Path("/fake"), "workflow.yml", ["test"])
    assert result1["test"].run_id == "402", "Expected failed run when no active runs"

    # Test 2: Active run present (highest priority)
    github2 = FakeGitHub(workflow_runs=[completed_success, completed_failure, in_progress])
    result2 = github2.get_workflow_runs_by_branches(Path("/fake"), "workflow.yml", ["test"])
    assert result2["test"].run_id == "403", "Expected in-progress run (highest priority)"

    # Test 3: Only completed success (fallback to most recent)
    github3 = FakeGitHub(workflow_runs=[completed_success])
    result3 = github3.get_workflow_runs_by_branches(Path("/fake"), "workflow.yml", ["test"])
    assert result3["test"].run_id == "401", "Expected completed success as fallback"
