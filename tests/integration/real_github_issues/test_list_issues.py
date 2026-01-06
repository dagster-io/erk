"""Tests for RealGitHubIssues.list_issues()."""

import json
import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from erk_shared.github.issues import RealGitHubIssues
from tests.integration.test_helpers import mock_subprocess_run


def test_list_issues_all(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues without filters using REST API."""
    # REST API response format (differs from GraphQL):
    # - state: lowercase ("open" vs "OPEN")
    # - html_url instead of url
    # - created_at/updated_at with underscores
    # - user.login instead of author.login
    issues_data = [
        {
            "number": 1,
            "title": "Issue 1",
            "body": "Body 1",
            "state": "open",  # REST uses lowercase
            "html_url": "http://url/1",  # REST uses html_url
            "labels": [],
            "assignees": [],
            "created_at": "2024-01-01T00:00:00Z",  # REST uses snake_case
            "updated_at": "2024-01-01T00:00:00Z",
            "user": {"login": "user1"},  # REST uses user.login
        },
        {
            "number": 2,
            "title": "Issue 2",
            "body": "Body 2",
            "state": "closed",  # REST uses lowercase
            "html_url": "http://url/2",
            "labels": [],
            "assignees": [],
            "created_at": "2024-01-02T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "user": {"login": "user2"},
        },
    ]

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(issues_data),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        result = issues.list_issues(repo_root=Path("/repo"))

        assert len(result) == 2
        assert result[0].number == 1
        assert result[0].title == "Issue 1"
        assert result[0].state == "OPEN"  # Normalized to uppercase
        assert result[1].number == 2
        assert result[1].state == "CLOSED"  # Normalized to uppercase


def test_list_issues_with_state_filter(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues with state filter uses REST API query parameter."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        issues.list_issues(repo_root=Path("/repo"), state="open")

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        # REST API uses query parameter in URL, not --state flag
        endpoint = cmd[2]
        assert "repos/{owner}/{repo}/issues" in endpoint
        assert "state=open" in endpoint


def test_list_issues_with_labels_filter(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues with labels filter uses REST API comma-separated query parameter."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        issues.list_issues(repo_root=Path("/repo"), labels=["plan", "erk"])

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        # REST API uses comma-separated labels in query parameter
        endpoint = cmd[2]
        assert "repos/{owner}/{repo}/issues" in endpoint
        assert "labels=plan,erk" in endpoint


def test_list_issues_with_both_filters(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues with both labels and state filters uses REST API query parameters."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        issues.list_issues(repo_root=Path("/repo"), labels=["bug"], state="closed")

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        endpoint = cmd[2]
        assert "repos/{owner}/{repo}/issues" in endpoint
        assert "labels=bug" in endpoint
        assert "state=closed" in endpoint


def test_list_issues_rest_api_endpoint(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues uses REST API endpoint instead of GraphQL."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        issues.list_issues(repo_root=Path("/repo"))

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        # Uses REST API endpoint, not 'gh issue list --json'
        assert cmd[2] == "repos/{owner}/{repo}/issues"
        # No --json flag (gh api returns JSON by default)
        assert "--json" not in cmd


def test_list_issues_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("gh not authenticated")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)

        with pytest.raises(RuntimeError, match="not authenticated"):
            issues.list_issues(repo_root=Path("/repo"))


def test_list_issues_empty_response(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues handles empty results."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        result = issues.list_issues(repo_root=Path("/repo"))

        assert result == []


def test_list_issues_null_body(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues handles null body from REST API."""
    # REST API can return null for body when issue has no description
    issues_data = [
        {
            "number": 42,
            "title": "Issue without body",
            "body": None,  # REST can return null
            "state": "open",
            "html_url": "https://github.com/owner/repo/issues/42",
            "labels": [],
            "assignees": [],
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-16T14:45:00Z",
            "user": {"login": "octocat"},
        }
    ]

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(issues_data),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        result = issues.list_issues(repo_root=Path("/repo"))

        assert len(result) == 1
        assert result[0].body == ""  # null converted to empty string


def test_list_issues_parses_all_fields(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues correctly parses all IssueInfo fields from REST API response."""
    # REST API response format (differs from GraphQL):
    # - state: lowercase ("open" vs "OPEN")
    # - html_url instead of url
    # - created_at/updated_at with underscores
    # - user.login instead of author.login
    issues_data = [
        {
            "number": 123,
            "title": "Complex Issue Title with Special Chars: / & <>",
            "body": "Multi-line\nbody\nwith\nlinebreaks",
            "state": "open",  # REST uses lowercase
            "html_url": "https://github.com/owner/repo/issues/123",  # REST uses html_url
            "labels": [{"name": "bug"}, {"name": "documentation"}],
            "assignees": [{"login": "alice"}],
            "created_at": "2024-01-15T10:30:00Z",  # REST uses snake_case
            "updated_at": "2024-01-20T16:45:00Z",
            "user": {"login": "author_name"},  # REST uses user.login
        }
    ]

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(issues_data),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        result = issues.list_issues(repo_root=Path("/repo"))

        assert len(result) == 1
        issue = result[0]
        assert issue.number == 123
        assert issue.title == "Complex Issue Title with Special Chars: / & <>"
        assert issue.body == "Multi-line\nbody\nwith\nlinebreaks"
        assert issue.state == "OPEN"  # Normalized to uppercase
        assert issue.url == "https://github.com/owner/repo/issues/123"
        assert issue.author == "author_name"


def test_list_issues_with_limit(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues respects limit parameter using REST API per_page."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        issues.list_issues(repo_root=Path("/repo"), limit=10)

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        # REST API uses per_page query parameter, not --limit flag
        endpoint = cmd[2]
        assert "repos/{owner}/{repo}/issues" in endpoint
        assert "per_page=10" in endpoint
