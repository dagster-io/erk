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


def create_beads_issue(
    repo_path: Path,
    *,
    title: str,
    labels: list[str] | None,
    status: str | None,
) -> str:
    """Create a beads issue and return its ID.

    Args:
        repo_path: Path to the beads repository
        title: Issue title
        labels: Optional list of labels
        status: Optional status to set

    Returns:
        The created issue ID
    """
    cmd = ["bd", "create", title]

    if labels:
        for label in labels:
            cmd.extend(["--label", label])

    result = subprocess.run(
        cmd,
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )

    # Extract issue ID from output (format: "Created issue: bd-XXXXXXXX")
    output = result.stdout.strip()
    issue_id = output.split()[-1]

    # Set status if specified (default is "open")
    if status is not None and status != "open":
        subprocess.run(
            ["bd", "status", issue_id, status],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )

    return issue_id


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

    # Create some issues
    create_beads_issue(repo, title="First issue", labels=None, status=None)
    create_beads_issue(repo, title="Second issue", labels=None, status=None)

    gateway = RealBeadsGateway(time=RealTime(), cwd=repo)

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

    # Create issues with different labels
    create_beads_issue(repo, title="Bug fix", labels=["bug"], status=None)
    create_beads_issue(repo, title="Feature request", labels=["feature"], status=None)
    create_beads_issue(repo, title="Bug with feature", labels=["bug", "feature"], status=None)

    gateway = RealBeadsGateway(time=RealTime(), cwd=repo)

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

    # Create issues with different statuses
    create_beads_issue(repo, title="Open issue", labels=None, status="open")
    create_beads_issue(repo, title="In progress issue", labels=None, status="in_progress")
    create_beads_issue(repo, title="Closed issue", labels=None, status="closed")

    gateway = RealBeadsGateway(time=RealTime(), cwd=repo)

    # Act: Filter by "open" status
    issues = gateway.list_issues(labels=None, status="open", limit=None)

    # Assert: Should return only open issues
    assert len(issues) == 1
    assert issues[0].title == "Open issue"
    assert issues[0].status == "open"


def test_list_issues_with_limit(tmp_path: Path) -> None:
    """Test list_issues respects limit parameter."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_beads_repo(repo)

    # Create multiple issues
    for i in range(5):
        create_beads_issue(repo, title=f"Issue {i}", labels=None, status=None)

    gateway = RealBeadsGateway(time=RealTime(), cwd=repo)

    # Act: Request only 2 issues
    issues = gateway.list_issues(labels=None, status=None, limit=2)

    # Assert
    assert len(issues) == 2


def test_list_issues_combined_filters(tmp_path: Path) -> None:
    """Test list_issues with multiple filters applied."""
    repo = tmp_path / "repo"
    repo.mkdir()
    init_beads_repo(repo)

    # Create diverse issues
    create_beads_issue(repo, title="Open bug", labels=["bug"], status="open")
    create_beads_issue(repo, title="Closed bug", labels=["bug"], status="closed")
    create_beads_issue(repo, title="Open feature", labels=["feature"], status="open")
    create_beads_issue(repo, title="Closed feature", labels=["feature"], status="closed")

    gateway = RealBeadsGateway(time=RealTime(), cwd=repo)

    # Act: Filter by "bug" label AND "open" status
    issues = gateway.list_issues(labels=["bug"], status="open", limit=None)

    # Assert
    assert len(issues) == 1
    assert issues[0].title == "Open bug"


def test_list_issues_bd_not_installed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    # Create an issue with labels
    create_beads_issue(repo, title="Test issue", labels=["test-label"], status="open")

    gateway = RealBeadsGateway(time=RealTime(), cwd=repo)

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
