"""Tests for RealGitHubIssues.remove_label_from_issue()."""

import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from erk_shared.gateway.github.issues.real import RealGitHubIssues
from erk_shared.gateway.time.real import RealTime
from tests.integration.test_helpers import mock_subprocess_run


def test_remove_label_from_issue_success(monkeypatch: MonkeyPatch) -> None:
    """Test remove_label_from_issue calls gh CLI REST API with correct command structure."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",  # DELETE returns empty on success
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None, time=RealTime())
        issues.remove_label_from_issue(Path("/repo"), 42, "bug")

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        assert "--method" in cmd
        assert "DELETE" in cmd
        # Endpoint comes after --method DELETE
        assert any("repos/{owner}/{repo}/issues/42/labels/bug" in arg for arg in cmd)


def test_remove_label_from_issue_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test remove_label_from_issue raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Issue not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None, time=RealTime())

        with pytest.raises(RuntimeError, match="Issue not found"):
            issues.remove_label_from_issue(Path("/repo"), 999, "label")
