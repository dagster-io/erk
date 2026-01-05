"""Tests for RealGitHubIssues label operations."""

import subprocess
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from erk_shared.github.issues import RealGitHubIssues
from tests.integration.test_helpers import mock_subprocess_run

# ============================================================================
# ensure_label_exists() tests
# ============================================================================


def test_ensure_label_exists_creates_new(monkeypatch: MonkeyPatch) -> None:
    """Test ensure_label_exists creates label when it doesn't exist."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        # First call: REST API label check (returns empty - label doesn't exist)
        if "api" in cmd and "repos/{owner}/{repo}/labels" in cmd:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="",
                stderr="",
            )
        # Second call: label create
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        issues.ensure_label_exists(
            Path("/repo"),
            label="erk-plan",
            description="Implementation plan",
            color="0E8A16",
        )

        # Should have made 2 calls: REST API check then create
        assert len(created_commands) == 2

        # Verify first command is REST API labels check
        check_cmd = created_commands[0]
        assert check_cmd[0] == "gh"
        assert check_cmd[1] == "api"
        assert "repos/{owner}/{repo}/labels" in check_cmd

        # Verify create command structure
        create_cmd = created_commands[1]
        assert create_cmd[0] == "gh"
        assert create_cmd[1] == "label"
        assert create_cmd[2] == "create"
        assert "erk-plan" in create_cmd
        assert "--description" in create_cmd
        assert "Implementation plan" in create_cmd
        assert "--color" in create_cmd
        assert "0E8A16" in create_cmd


def test_ensure_label_exists_already_exists(monkeypatch: MonkeyPatch) -> None:
    """Test ensure_label_exists is no-op when label already exists."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        # Label already exists (REST API returns label name via --jq)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="erk-plan",  # Non-empty output means label exists
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        issues.ensure_label_exists(
            Path("/repo"),
            label="erk-plan",
            description="Implementation plan",
            color="0E8A16",
        )

        # Should have made only 1 call: REST API labels check (no create needed)
        assert len(created_commands) == 1
        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        assert "repos/{owner}/{repo}/labels" in cmd


def test_ensure_label_exists_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test ensure_label_exists raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("gh not authenticated")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)

        with pytest.raises(RuntimeError, match="not authenticated"):
            issues.ensure_label_exists(Path("/repo"), "label", "desc", "color")


# ============================================================================
# ensure_label_on_issue() tests
# ============================================================================


def test_ensure_label_on_issue_success(monkeypatch: MonkeyPatch) -> None:
    """Test ensure_label_on_issue calls gh CLI REST API with correct command structure."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",  # REST API returns JSON array of labels
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        issues.ensure_label_on_issue(Path("/repo"), 42, "erk-plan")

        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        assert "--method" in cmd
        assert "POST" in cmd
        # Endpoint comes after --method POST
        assert any("repos/{owner}/{repo}/issues/42/labels" in arg for arg in cmd)
        assert "-f" in cmd
        assert "labels[]=erk-plan" in cmd


def test_ensure_label_on_issue_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test ensure_label_on_issue raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Issue not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)

        with pytest.raises(RuntimeError, match="Issue not found"):
            issues.ensure_label_on_issue(Path("/repo"), 999, "label")
