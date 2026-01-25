"""Integration tests for Beads gateway operations.

These tests verify that RealBeadsGateway correctly handles bd CLI operations.
Integration tests use actual bd subprocess calls to validate the abstractions.

Tests are skipped if the `bd` CLI is not installed on the system.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from erk_shared.gateway.beads.real import RealBeadsGateway
from erk_shared.gateway.time.real import RealTime

# Skip all tests in this module if bd CLI is not installed
pytestmark = pytest.mark.skipif(
    shutil.which("bd") is None,
    reason="bd CLI not installed",
)


def init_beads_repo(repo_path: Path) -> None:
    """Initialize a beads repository with bd init."""
    subprocess.run(["bd", "init"], cwd=repo_path, check=True, capture_output=True)


def set_issue_status(repo_path: Path, issue_id: str, status: str) -> None:
    """Set the status of an existing issue.

    Args:
        repo_path: Path to the beads repository
        issue_id: ID of the issue to update
        status: Status to set (open, in_progress, blocked, deferred, closed)
    """
    subprocess.run(
        ["bd", "status", issue_id, status],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )


def test_list_issues_empty_result(tmp_path: Path) -> None:
    """Test list_issues returns empty list when no issues exist."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_beads_repo(repo)

    gateway = RealBeadsGateway(time=RealTime(), cwd=repo)

    # Act
    issues = gateway.list_issues(labels=None, status=None, limit=None)

    # Assert
    assert issues == []


def test_list_issues_returns_all_issues(tmp_path: Path) -> None:
    """Test list_issues returns all issues when no filters are applied."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_beads_repo(repo)

    gateway = RealBeadsGateway(time=RealTime(), cwd=repo)

    # Create issues using gateway
    gateway.create_issue(title="First issue", labels=None, description=None)
    gateway.create_issue(title="Second issue", labels=None, description=None)

    # Act
    issues = gateway.list_issues(labels=None, status=None, limit=None)

    # Assert
    assert len(issues) == 2
    titles = {issue.title for issue in issues}
    assert "First issue" in titles
    assert "Second issue" in titles


def test_list_issues_with_labels(tmp_path: Path) -> None:
    """Test list_issues filters by labels correctly."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_beads_repo(repo)

    gateway = RealBeadsGateway(time=RealTime(), cwd=repo)

    # Create issues with different labels using gateway
    gateway.create_issue(title="Bug fix", labels=["bug"], description=None)
    gateway.create_issue(title="Feature request", labels=["feature"], description=None)
    gateway.create_issue(title="Bug with feature", labels=["bug", "feature"], description=None)

    # Act: Filter by "bug" label
    issues = gateway.list_issues(labels=["bug"], status=None, limit=None)

    # Assert: Should return issues with "bug" label
    assert len(issues) == 2
    titles = {issue.title for issue in issues}
    assert "Bug fix" in titles
    assert "Bug with feature" in titles
    assert "Feature request" not in titles


def test_list_issues_with_status(tmp_path: Path) -> None:
    """Test list_issues filters by status correctly."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_beads_repo(repo)

    gateway = RealBeadsGateway(time=RealTime(), cwd=repo)

    # Create issues and set statuses (create_issue always creates with "open")
    open_issue = gateway.create_issue(title="Open issue", labels=None, description=None)
    in_progress_issue = gateway.create_issue(
        title="In progress issue", labels=None, description=None
    )
    closed_issue = gateway.create_issue(title="Closed issue", labels=None, description=None)

    # Set non-open statuses using bd CLI
    set_issue_status(repo, in_progress_issue.id, "in_progress")
    set_issue_status(repo, closed_issue.id, "closed")

    # Act: Filter by "open" status
    issues = gateway.list_issues(labels=None, status="open", limit=None)

    # Assert: Should return only open issues
    assert len(issues) == 1
    assert issues[0].title == "Open issue"
    assert issues[0].id == open_issue.id
    assert issues[0].status == "open"


def test_list_issues_with_limit(tmp_path: Path) -> None:
    """Test list_issues respects limit parameter."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_beads_repo(repo)

    gateway = RealBeadsGateway(time=RealTime(), cwd=repo)

    # Create multiple issues using gateway
    for i in range(5):
        gateway.create_issue(title=f"Issue {i}", labels=None, description=None)

    # Act: Request only 2 issues
    issues = gateway.list_issues(labels=None, status=None, limit=2)

    # Assert
    assert len(issues) == 2


def test_list_issues_combined_filters(tmp_path: Path) -> None:
    """Test list_issues with multiple filters applied."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_beads_repo(repo)

    gateway = RealBeadsGateway(time=RealTime(), cwd=repo)

    # Create issues with labels using gateway
    open_bug = gateway.create_issue(title="Open bug", labels=["bug"], description=None)
    closed_bug = gateway.create_issue(title="Closed bug", labels=["bug"], description=None)
    gateway.create_issue(title="Open feature", labels=["feature"], description=None)
    closed_feature = gateway.create_issue(
        title="Closed feature", labels=["feature"], description=None
    )

    # Set closed statuses
    set_issue_status(repo, closed_bug.id, "closed")
    set_issue_status(repo, closed_feature.id, "closed")

    # Act: Filter by "bug" label AND "open" status
    issues = gateway.list_issues(labels=["bug"], status="open", limit=None)

    # Assert
    assert len(issues) == 1
    assert issues[0].title == "Open bug"
    assert issues[0].id == open_bug.id


def test_list_issues_bd_not_installed(tmp_path: Path) -> None:
    """Test list_issues raises RuntimeError when bd CLI fails."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Don't init beads - this will cause bd to fail
    gateway = RealBeadsGateway(time=RealTime(), cwd=repo)

    # Act & Assert: Should raise RuntimeError due to bd failure
    with pytest.raises(RuntimeError, match="bd list failed"):
        gateway.list_issues(labels=None, status=None, limit=None)


def test_list_issues_returns_issue_fields(tmp_path: Path) -> None:
    """Test list_issues returns BeadsIssue with all expected fields."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_beads_repo(repo)

    gateway = RealBeadsGateway(time=RealTime(), cwd=repo)

    # Create an issue with labels using gateway
    gateway.create_issue(title="Test issue", labels=["test-label"], description=None)

    # Act
    issues = gateway.list_issues(labels=None, status=None, limit=None)

    # Assert: Verify issue has all expected fields
    assert len(issues) == 1
    issue = issues[0]

    # Required fields should be populated
    assert issue.id.startswith("bd-")
    assert issue.title == "Test issue"
    assert issue.status == "open"
    assert "test-label" in issue.labels
    assert issue.created_at  # Non-empty ISO timestamp
    assert issue.updated_at  # Non-empty ISO timestamp

    # Optional fields have defaults
    assert isinstance(issue.description, str)
    assert isinstance(issue.notes, str)
    # assignee may be None


def test_create_issue_returns_valid_beads_issue(tmp_path: Path) -> None:
    """Test create_issue returns a BeadsIssue with all expected fields."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_beads_repo(repo)

    gateway = RealBeadsGateway(time=RealTime(), cwd=repo)

    # Act
    issue = gateway.create_issue(
        title="Created via gateway",
        labels=["gateway-test", "integration"],
        description="Description content here",
    )

    # Assert: Verify returned issue has all expected fields
    assert issue.id.startswith("bd-")
    assert issue.title == "Created via gateway"
    assert issue.status == "open"
    assert "gateway-test" in issue.labels
    assert "integration" in issue.labels
    assert issue.description == "Description content here"
    assert issue.created_at  # Non-empty ISO timestamp
    assert issue.updated_at  # Non-empty ISO timestamp

    # Verify it actually exists by listing
    listed = gateway.list_issues(labels=["gateway-test"], status=None, limit=None)
    assert len(listed) == 1
    assert listed[0].id == issue.id


def test_create_issue_bd_not_initialized(tmp_path: Path) -> None:
    """Test create_issue raises RuntimeError when bd is not initialized."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Don't init beads - this will cause bd to fail
    gateway = RealBeadsGateway(time=RealTime(), cwd=repo)

    # Act & Assert: Should raise RuntimeError due to bd failure
    with pytest.raises(RuntimeError, match="bd create failed"):
        gateway.create_issue(title="Should fail", labels=None, description=None)
