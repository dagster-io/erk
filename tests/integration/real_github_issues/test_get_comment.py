"""Tests for RealGitHubIssues.get_comment_by_id()."""

import subprocess
from pathlib import Path

from pytest import MonkeyPatch

from erk_shared.github.issues.real import RealGitHubIssues
from tests.integration.test_helpers import mock_subprocess_run


def test_get_comment_by_id_success(monkeypatch: MonkeyPatch) -> None:
    """Test get_comment_by_id calls gh REST API correctly."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="This is the comment body",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        body = issues.get_comment_by_id(Path("/repo"), 12345678)

        assert body == "This is the comment body"

        # Verify command structure
        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        assert "repos/{owner}/{repo}/issues/comments/12345678" in cmd[2]
        assert "--jq" in cmd
        assert ".body" in cmd
