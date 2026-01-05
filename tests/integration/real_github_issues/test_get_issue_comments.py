"""Tests for RealGitHubIssues.get_issue_comments()."""

import json
import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from erk_shared.github.issues import RealGitHubIssues
from tests.integration.test_helpers import mock_subprocess_run


def test_get_issue_comments_success(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue_comments parses comment bodies correctly."""
    # JSON array output from jq "[.[].body]"
    json_output = json.dumps(["First comment", "Second comment", "Third comment"])

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json_output,
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        result = issues.get_issue_comments(Path("/repo"), 42)

        assert result == ["First comment", "Second comment", "Third comment"]


def test_get_issue_comments_empty(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue_comments handles no comments."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        result = issues.get_issue_comments(Path("/repo"), 42)

        assert result == []


def test_get_issue_comments_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue_comments raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Issue not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)

        with pytest.raises(RuntimeError, match="Issue not found"):
            issues.get_issue_comments(Path("/repo"), 999)


def test_get_issue_comments_multiline_bodies_preserved(monkeypatch: MonkeyPatch) -> None:
    """Test multi-line comment bodies are preserved as single list items.

    This is the critical bug fix test. The previous implementation used
    jq ".[].body" with split("\\n") which incorrectly split multi-line
    markdown comments into separate list items.

    The fix uses JSON array output format which preserves newlines within
    comment bodies.
    """
    # Simulate JSON array output from jq "[.[].body]"
    # This preserves multi-line bodies correctly
    json_output = json.dumps(
        [
            "Line 1\nLine 2\nLine 3",  # Multi-line first comment
            "Single line comment",  # Single line
            "Another\nmulti-line\ncomment",  # Another multi-line
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
        issues = RealGitHubIssues(target_repo=None)
        result = issues.get_issue_comments(Path("/repo"), 42)

        # Should be 3 comments, NOT 8 (which would happen with split("\n"))
        assert len(result) == 3
        assert result[0] == "Line 1\nLine 2\nLine 3"
        assert result[1] == "Single line comment"
        assert result[2] == "Another\nmulti-line\ncomment"


def test_get_issue_comments_with_plan_markers(monkeypatch: MonkeyPatch) -> None:
    """Test comment containing plan markers preserves multi-line structure.

    This verifies the specific use case from Issue #1221 where a 299-line
    plan comment was being corrupted because newlines split it into
    separate "comments".
    """
    plan_comment = """<!-- erk:plan-content -->
# Plan: Test Implementation

## Step 1
Implementation details with newlines and formatting.

## Step 2
More details across multiple lines.

<!-- /erk:plan-content -->"""

    json_output = json.dumps([plan_comment])

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=json_output,
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        result = issues.get_issue_comments(Path("/repo"), 42)

        # Should be exactly ONE comment with all content intact
        assert len(result) == 1
        assert "<!-- erk:plan-content -->" in result[0]
        assert "<!-- /erk:plan-content -->" in result[0]
        assert "## Step 1" in result[0]
        assert "## Step 2" in result[0]


def test_get_issue_comments_command_uses_json_array_output(monkeypatch: MonkeyPatch) -> None:
    """Test get_issue_comments uses jq array format for reliable parsing."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",  # Empty JSON array
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        issues.get_issue_comments(Path("/repo"), 42)

        # Verify command structure
        cmd = created_commands[0]
        assert "gh" in cmd
        assert "api" in cmd
        assert "--jq" in cmd
        # The jq expression should output a JSON array, not raw lines
        jq_idx = cmd.index("--jq") + 1
        jq_expr = cmd[jq_idx]
        # Should use [.[].body] not .[].body
        assert jq_expr.startswith("[") and jq_expr.endswith("]"), (
            f"jq expression should wrap in array brackets: {jq_expr}"
        )
