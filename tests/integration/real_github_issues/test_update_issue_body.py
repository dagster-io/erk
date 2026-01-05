"""Tests for RealGitHubIssues.update_issue_body()."""

import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from erk_shared.github.issues import RealGitHubIssues
from tests.integration.test_helpers import mock_subprocess_run


def test_update_issue_body_success(monkeypatch: MonkeyPatch) -> None:
    """Test update_issue_body calls gh CLI REST API with correct command structure."""
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
        issues.update_issue_body(Path("/repo"), 42, "Updated body content")

        # Verify command structure (REST API)
        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        assert "--method" in cmd
        assert "PATCH" in cmd
        # Endpoint comes after --method PATCH
        assert any("repos/{owner}/{repo}/issues/42" in arg for arg in cmd)
        assert "-f" in cmd
        assert "body=Updated body content" in cmd


def test_update_issue_body_multiline(monkeypatch: MonkeyPatch) -> None:
    """Test update_issue_body handles multiline body content."""
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
        multiline_body = """# Heading

Paragraph with **bold** text.

- List item 1
- List item 2"""
        issues.update_issue_body(Path("/repo"), 10, multiline_body)

        cmd = created_commands[0]
        # REST API passes body as -f parameter
        assert f"body={multiline_body}" in cmd


def test_update_issue_body_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test update_issue_body raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Issue not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)

        with pytest.raises(RuntimeError, match="Issue not found"):
            issues.update_issue_body(Path("/repo"), 999, "New body")
