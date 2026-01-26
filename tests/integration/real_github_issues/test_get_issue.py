"""Tests for RealGitHubIssues.get_issue()."""

import json
import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from erk_shared.gateway.github.issues.real import RealGitHubIssues
from erk_shared.gateway.time.real import RealTime
from tests.integration.test_helpers import mock_subprocess_run


def test_get_issue_success(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue calls gh REST API and parses response."""
    # REST API response format (differs from GraphQL):
    # - state: lowercase ("open" vs "OPEN")
    # - html_url instead of url
    # - created_at/updated_at with underscores
    issue_data = {
        "number": 42,
        "title": "Test Issue Title",
        "body": "Test issue body content",
        "state": "open",  # REST uses lowercase
        "html_url": "https://github.com/owner/repo/issues/42",  # REST uses html_url
        "labels": [{"name": "bug"}, {"name": "enhancement"}],
        "assignees": [{"login": "alice"}, {"login": "bob"}],
        "created_at": "2024-01-15T10:30:00Z",  # REST uses snake_case
        "updated_at": "2024-01-16T14:45:00Z",
    }

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(issue_data),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None, time=RealTime())
        result = issues.get_issue(Path("/repo"), 42)

        assert result.number == 42
        assert result.title == "Test Issue Title"
        assert result.body == "Test issue body content"
        assert result.state == "OPEN"  # Normalized to uppercase
        assert result.url == "https://github.com/owner/repo/issues/42"


def test_get_issue_command_structure(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue constructs correct gh REST API command."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        # REST API response format
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(
                {
                    "number": 123,
                    "title": "Title",
                    "body": "Body",
                    "state": "open",
                    "html_url": "http://url",
                    "labels": [],
                    "assignees": [],
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                }
            ),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None, time=RealTime())
        issues.get_issue(Path("/repo"), 123)

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        # REST API endpoint with {owner}/{repo} placeholders
        assert cmd[2] == "repos/{owner}/{repo}/issues/123"


def test_get_issue_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Issue not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None, time=RealTime())

        with pytest.raises(RuntimeError, match="Issue not found"):
            issues.get_issue(Path("/repo"), 999)


def test_get_issue_null_body(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue handles null body from REST API."""
    # REST API can return null for body when issue has no description
    issue_data = {
        "number": 42,
        "title": "Issue without body",
        "body": None,  # REST can return null
        "state": "open",
        "html_url": "https://github.com/owner/repo/issues/42",
        "labels": [],
        "assignees": [],
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-16T14:45:00Z",
    }

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(issue_data),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None, time=RealTime())
        result = issues.get_issue(Path("/repo"), 42)

        assert result.body == ""  # null converted to empty string
