"""Tests for RealGitHubIssues.create_issue()."""

import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from erk_shared.github.issues import RealGitHubIssues
from tests.integration.test_helpers import mock_subprocess_run


def test_create_issue_success(monkeypatch: MonkeyPatch) -> None:
    """Test create_issue calls gh CLI REST API and parses response."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        # REST API returns "number url" format via --jq
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="42 https://github.com/owner/repo/issues/42\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        result = issues.create_issue(
            repo_root=Path("/repo"),
            title="Test Issue",
            body="Test body content",
            labels=["plan", "erk"],
        )

        # Verify issue number and URL extracted from response
        assert result.number == 42
        assert result.url == "https://github.com/owner/repo/issues/42"

        # Verify gh command structure (REST API)
        assert len(created_commands) == 1
        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        assert "repos/{owner}/{repo}/issues" in cmd[2]
        assert "-X" in cmd
        assert "POST" in cmd
        assert "-f" in cmd
        assert "title=Test Issue" in cmd
        assert "body=Test body content" in cmd
        # Verify labels are passed as array elements
        assert "labels[]=plan" in cmd
        assert "labels[]=erk" in cmd
        # REST API uses --jq for response parsing
        assert "--jq" in cmd


def test_create_issue_multiple_labels(monkeypatch: MonkeyPatch) -> None:
    """Test create_issue includes all labels in command."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        # REST API returns "number url" format via --jq
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="1 https://github.com/owner/repo/issues/1\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        issues.create_issue(
            repo_root=Path("/repo"),
            title="Title",
            body="Body",
            labels=["label1", "label2", "label3"],
        )

        cmd = created_commands[0]
        # REST API uses -f labels[]=value format for array elements
        assert "labels[]=label1" in cmd
        assert "labels[]=label2" in cmd
        assert "labels[]=label3" in cmd


def test_create_issue_no_labels(monkeypatch: MonkeyPatch) -> None:
    """Test create_issue works with empty labels list."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        # REST API returns "number url" format via --jq
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="1 https://github.com/owner/repo/issues/1\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        issues.create_issue(repo_root=Path("/repo"), title="Title", body="Body", labels=[])

        cmd = created_commands[0]
        # No labels[] flags should be present
        assert not any("labels[]" in arg for arg in cmd)


def test_create_issue_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test create_issue raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("gh command failed: not authenticated")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)

        with pytest.raises(RuntimeError, match="not authenticated"):
            issues.create_issue(
                repo_root=Path("/repo"), title="Title", body="Body", labels=["label"]
            )
