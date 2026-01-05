"""Tests for RealGitHubIssues.close_issue()."""

import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from erk_shared.github.issues import RealGitHubIssues
from tests.integration.test_helpers import mock_subprocess_run


def test_close_issue_success(monkeypatch: MonkeyPatch) -> None:
    """Test close_issue calls gh CLI REST API with correct command structure."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="{}",  # REST API returns JSON
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        issues.close_issue(Path("/repo"), 42)

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        assert "--method" in cmd
        assert "PATCH" in cmd
        # Endpoint comes after --method PATCH
        assert any("repos/{owner}/{repo}/issues/42" in arg for arg in cmd)
        assert "-f" in cmd
        assert "state=closed" in cmd


def test_close_issue_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test close_issue raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Issue not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)

        with pytest.raises(RuntimeError, match="Issue not found"):
            issues.close_issue(Path("/repo"), 999)
