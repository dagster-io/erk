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
            repo_root=Path("/repo"),
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
            repo_root=Path("/repo"),
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
            issues.ensure_label_exists(
                repo_root=Path("/repo"), label="label", description="desc", color="color"
            )


# ============================================================================
# label_exists() tests
# ============================================================================


def test_label_exists_returns_true_when_found(monkeypatch: MonkeyPatch) -> None:
    """Test label_exists returns True when label exists in repository."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        # REST API returns label name via --jq filter
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="erk-plan",  # Non-empty output means label exists
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        result = issues.label_exists(Path("/repo"), "erk-plan")

        assert result is True
        assert len(created_commands) == 1
        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "api"
        assert "repos/{owner}/{repo}/labels" in cmd
        assert "--jq" in cmd


def test_label_exists_returns_false_when_not_found(monkeypatch: MonkeyPatch) -> None:
    """Test label_exists returns False when label doesn't exist."""
    created_commands = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        # REST API returns empty string when label not found (--jq filter matches nothing)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)
        result = issues.label_exists(Path("/repo"), "nonexistent-label")

        assert result is False
        assert len(created_commands) == 1


def test_label_exists_uses_cache(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Test label_exists uses cache to avoid redundant API calls.

    Note: Cache only works with real paths. With non-existent paths like Path("/repo"),
    the RealLabelCache disables itself (cache_path=None) and always returns False from has().
    """
    api_calls = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        api_calls.append(cmd)
        # Handle git rev-parse for cache init
        if "rev-parse" in cmd:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=str(tmp_path / ".git"),
                stderr="",
            )
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="erk-plan",
            stderr="",
        )

    # Create a fake .git directory so cache works
    (tmp_path / ".git").mkdir()

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)

        # First call should hit API
        result1 = issues.label_exists(tmp_path, "erk-plan")
        assert result1 is True
        assert len(api_calls) == 1

        # Second call should use cache (no additional API call)
        result2 = issues.label_exists(tmp_path, "erk-plan")
        assert result2 is True
        assert len(api_calls) == 1  # Still just 1 call


def test_label_exists_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test label_exists raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("gh not authenticated")

    with mock_subprocess_run(monkeypatch, mock_run):
        issues = RealGitHubIssues(target_repo=None)

        with pytest.raises(RuntimeError, match="not authenticated"):
            issues.label_exists(Path("/repo"), "erk-plan")


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
