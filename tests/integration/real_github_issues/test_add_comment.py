"""Tests for RealGitHubIssues.add_comment()."""

import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from erk_shared.github.issues import RealGitHubIssues
from tests.integration.test_helpers import mock_subprocess_run


def test_add_comment_success(monkeypatch: MonkeyPatch) -> None:
    """Test add_comment calls gh REST API and returns comment ID."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        # REST API returns comment ID via --jq ".id"
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="12345678\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        comment_id = issues.add_comment(Path("/repo"), 42, "This is my comment body")

        # Verify return value
        assert comment_id == 12345678

        # Verify command structure (REST API)
        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        assert "repos/{owner}/{repo}/issues/42/comments" in cmd[2]
        assert "-X" in cmd
        assert "POST" in cmd
        assert "-f" in cmd
        assert "body=This is my comment body" in cmd
        assert "--jq" in cmd
        assert ".id" in cmd


def test_add_comment_multiline_body(monkeypatch: MonkeyPatch) -> None:
    """Test add_comment handles multiline comment bodies."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="99999\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        multiline_body = """First line of comment

Second line after blank line

Third line"""
        comment_id = issues.add_comment(Path("/repo"), 10, multiline_body)

        assert comment_id == 99999
        cmd = created_commands[0]
        # Body is passed as -f parameter
        assert f"body={multiline_body}" in cmd


def test_add_comment_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test add_comment raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Issue not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)

        with pytest.raises(RuntimeError, match="Issue not found"):
            issues.add_comment(Path("/repo"), 999, "Comment body")
