"""Tests for RealGitHubIssues.get_current_username()."""

import subprocess

from pytest import MonkeyPatch

from erk_shared.github.issues import RealGitHubIssues
from tests.integration.test_helpers import mock_subprocess_run


def test_get_current_username_success(monkeypatch: MonkeyPatch) -> None:
    """Test get_current_username returns username when authenticated."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Verify correct command structure
        assert cmd == ["gh", "api", "user", "--jq", ".login"]
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="octocat\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        result = issues.get_current_username()

        assert result == "octocat"


def test_get_current_username_not_authenticated(monkeypatch: MonkeyPatch) -> None:
    """Test get_current_username returns None when not authenticated."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="",
            stderr="error: not logged in",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        result = issues.get_current_username()

        assert result is None


def test_get_current_username_strips_whitespace(monkeypatch: MonkeyPatch) -> None:
    """Test get_current_username strips trailing whitespace from output."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="  username-with-spaces  \n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        result = issues.get_current_username()

        assert result == "username-with-spaces"
