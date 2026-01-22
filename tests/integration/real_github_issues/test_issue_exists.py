"""Tests for RealGitHubIssues.issue_exists()."""

import subprocess
from pathlib import Path

from pytest import MonkeyPatch

from erk_shared.github.issues.real import RealGitHubIssues
from tests.integration.test_helpers import mock_subprocess_run


def test_issue_exists_returns_true_when_found(monkeypatch: MonkeyPatch) -> None:
    """Test issue_exists returns True when gh CLI succeeds."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="{}",  # Minimal valid response
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        result = issues.issue_exists(Path("/repo"), 42)

        assert result is True


def test_issue_exists_returns_false_when_not_found(monkeypatch: MonkeyPatch) -> None:
    """Test issue_exists returns False when gh CLI fails (404)."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,  # Non-zero = issue not found (404)
            stdout="",
            stderr="Issue not found",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        result = issues.issue_exists(Path("/repo"), 999)

        assert result is False


def test_issue_exists_command_structure(monkeypatch: MonkeyPatch) -> None:
    """Test issue_exists constructs correct gh REST API command."""
    created_commands: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="{}",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        issues.issue_exists(Path("/repo"), 123)

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        # REST API endpoint with {owner}/{repo} placeholders
        assert cmd[2] == "repos/{owner}/{repo}/issues/123"
        assert "--silent" in cmd
