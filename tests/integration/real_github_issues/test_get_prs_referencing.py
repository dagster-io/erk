"""Tests for RealGitHubIssues.get_prs_referencing_issue()."""

import json
import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from erk_shared.gateway.github.issues.real import RealGitHubIssues
from erk_shared.gateway.time.real import RealTime
from tests.integration.test_helpers import mock_subprocess_run


def test_get_prs_referencing_issue_success(monkeypatch: MonkeyPatch) -> None:
    """Test get_prs_referencing_issue parses timeline API response correctly."""
    # JSON output from jq expression that filters cross-referenced PRs
    json_output = json.dumps(
        [
            {"number": 100, "state": "open", "is_draft": True},
            {"number": 101, "state": "closed", "is_draft": False},
        ]
    )

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json_output,
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None, time=RealTime())
        result = issues.get_prs_referencing_issue(Path("/repo"), 42)

        assert len(result) == 2
        assert result[0].number == 100
        assert result[0].state == "OPEN"  # State is uppercased
        assert result[0].is_draft is True
        assert result[1].number == 101
        assert result[1].state == "CLOSED"
        assert result[1].is_draft is False


def test_get_prs_referencing_issue_empty(monkeypatch: MonkeyPatch) -> None:
    """Test get_prs_referencing_issue handles empty response."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None, time=RealTime())
        result = issues.get_prs_referencing_issue(Path("/repo"), 42)

        assert result == []


def test_get_prs_referencing_issue_empty_array(monkeypatch: MonkeyPatch) -> None:
    """Test get_prs_referencing_issue handles empty JSON array."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None, time=RealTime())
        result = issues.get_prs_referencing_issue(Path("/repo"), 42)

        assert result == []


def test_get_prs_referencing_issue_command_structure(monkeypatch: MonkeyPatch) -> None:
    """Test get_prs_referencing_issue constructs correct gh CLI command."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None, time=RealTime())
        issues.get_prs_referencing_issue(Path("/repo"), 123)

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        # Should use timeline endpoint with issue number
        assert any("timeline" in arg for arg in cmd)
        assert any("123" in arg for arg in cmd)
        assert "--jq" in cmd


def test_get_prs_referencing_issue_handles_null_draft(monkeypatch: MonkeyPatch) -> None:
    """Test get_prs_referencing_issue handles null/missing is_draft field."""
    # Some PR responses may have null or missing draft field
    json_output = json.dumps(
        [
            {"number": 100, "state": "open", "is_draft": None},
            {"number": 101, "state": "open"},  # is_draft missing entirely
        ]
    )

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json_output,
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None, time=RealTime())
        result = issues.get_prs_referencing_issue(Path("/repo"), 42)

        # Both should default to False when is_draft is null/missing
        assert len(result) == 2
        assert result[0].is_draft is False
        assert result[1].is_draft is False


def test_get_prs_referencing_issue_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test get_prs_referencing_issue raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Issue not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None, time=RealTime())

        with pytest.raises(RuntimeError, match="Issue not found"):
            issues.get_prs_referencing_issue(Path("/repo"), 999)
