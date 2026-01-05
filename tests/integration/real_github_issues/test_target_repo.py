"""Tests for RealGitHubIssues cross-repo target_repo functionality."""

import json
import subprocess
from pathlib import Path

from pytest import MonkeyPatch

from erk_shared.github.issues import RealGitHubIssues
from tests.integration.test_helpers import mock_subprocess_run


def test_target_repo_property_returns_configured_value() -> None:
    """Test target_repo property returns the configured value."""
    issues = RealGitHubIssues(target_repo="owner/plans-repo")
    assert issues.target_repo == "owner/plans-repo"

    issues_none = RealGitHubIssues(target_repo=None)
    assert issues_none.target_repo is None


def test_create_issue_with_target_repo_includes_r_flag(monkeypatch: MonkeyPatch) -> None:
    """Test create_issue includes -R flag when target_repo is set."""
    created_commands: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        # REST API returns "number url" format via --jq
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="42 https://github.com/owner/plans-repo/issues/42\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo="owner/plans-repo")
        issues.create_issue(
            Path("/repo"),
            title="Test Issue",
            body="Test body",
            labels=["plan"],
        )

        cmd = created_commands[0]
        # Verify -R flag is inserted after 'gh'
        assert cmd[0] == "gh"
        assert cmd[1] == "-R"
        assert cmd[2] == "owner/plans-repo"
        assert cmd[3] == "api"  # REST API command


def test_get_issue_with_target_repo_includes_r_flag(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue includes -R flag when target_repo is set."""
    created_commands: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json.dumps(
                {
                    "number": 42,
                    "title": "Test",
                    "body": "Body",
                    "state": "open",
                    "html_url": "https://github.com/owner/plans-repo/issues/42",
                    "labels": [],
                    "assignees": [],
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                    "user": {"login": "testuser"},
                }
            ),
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo="owner/plans-repo")
        issues.get_issue(Path("/repo"), 42)

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "-R"
        assert cmd[2] == "owner/plans-repo"
        assert cmd[3] == "api"


def test_list_issues_with_target_repo_includes_r_flag(monkeypatch: MonkeyPatch) -> None:
    """Test list_issues includes -R flag when target_repo is set."""
    created_commands: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo="owner/plans-repo")
        issues.list_issues(Path("/repo"), labels=["erk-plan"])

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "-R"
        assert cmd[2] == "owner/plans-repo"
        assert cmd[3] == "api"
