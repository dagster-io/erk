"""Tests for RealIssueLinkBranches with mocked subprocess execution.

These tests verify that RealIssueLinkBranches correctly calls gh CLI commands
and handles responses. We use pytest monkeypatch to mock subprocess calls.

Layer 2: Integration Sanity Tests - validates command construction and
response parsing with mocked subprocess calls.
"""

import subprocess
from pathlib import Path

import pytest
from erk_shared.github.issue_link_branches_real import RealIssueLinkBranches
from pytest import MonkeyPatch

from tests.integration.test_helpers import mock_subprocess_run

# ============================================================================
# get_linked_branch() tests
# ============================================================================


def test_get_linked_branch_returns_branch_when_exists(monkeypatch: MonkeyPatch) -> None:
    """Test get_linked_branch returns branch name when one exists."""
    created_commands: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="123-my-feature-branch\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issue_link = RealIssueLinkBranches()
        result = issue_link.get_linked_branch(Path("/repo"), 123)

        assert result == "123-my-feature-branch"

        # Verify command structure
        assert len(created_commands) == 1
        cmd = created_commands[0]
        assert cmd[0] == "gh"
        assert cmd[1] == "issue"
        assert cmd[2] == "develop"
        assert cmd[3] == "--list"
        assert cmd[4] == "123"


def test_get_linked_branch_returns_none_when_no_branch(monkeypatch: MonkeyPatch) -> None:
    """Test get_linked_branch returns None when no branch is linked."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",  # Empty output means no linked branches
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issue_link = RealIssueLinkBranches()
        result = issue_link.get_linked_branch(Path("/repo"), 456)

        assert result is None


def test_get_linked_branch_returns_first_when_multiple(monkeypatch: MonkeyPatch) -> None:
    """Test get_linked_branch returns first branch when multiple are linked."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Multiple branches linked to same issue (one per line)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="123-first-branch\n123-second-branch\n123-third-branch\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issue_link = RealIssueLinkBranches()
        result = issue_link.get_linked_branch(Path("/repo"), 123)

        # Should return first branch only
        assert result == "123-first-branch"


def test_get_linked_branch_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test get_linked_branch raises RuntimeError on gh CLI failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("gh command failed: not authenticated")

    with mock_subprocess_run(monkeypatch, mock_run):
        issue_link = RealIssueLinkBranches()

        with pytest.raises(RuntimeError, match="not authenticated"):
            issue_link.get_linked_branch(Path("/repo"), 123)


def test_get_linked_branch_parses_tab_separated_output(monkeypatch: MonkeyPatch) -> None:
    """Test get_linked_branch extracts only branch name from tab-separated output.

    gh issue develop --list outputs: "branch-name\thttps://github.com/..."
    We should only return the branch name, not the URL.
    """

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Real gh output format: branch name, tab, URL
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="123-my-feature\thttps://github.com/owner/repo/tree/123-my-feature\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issue_link = RealIssueLinkBranches()
        result = issue_link.get_linked_branch(Path("/repo"), 123)

        # Should return ONLY the branch name, not the URL
        assert result == "123-my-feature"
        assert "\t" not in result
        assert "https://" not in result


# ============================================================================
# create_development_branch() tests
# ============================================================================


def test_create_development_branch_creates_new_branch(monkeypatch: MonkeyPatch) -> None:
    """Test create_development_branch creates branch when none exists."""
    created_commands: list[list[str]] = []
    call_count = [0]

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)
        call_count[0] += 1

        # First call: get_linked_branch (--list) returns empty
        if "--list" in cmd:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="",  # No existing branch
                stderr="",
            )

        # Second call: gh issue develop (create) returns success
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issue_link = RealIssueLinkBranches()
        result = issue_link.create_development_branch(
            Path("/repo"), 42, branch_name="42-new-feature"
        )

        # Branch name comes from what we pass in, not from stdout
        assert result.branch_name == "42-new-feature"
        assert result.issue_number == 42
        assert result.already_existed is False

        # Should have made 2 calls: list check, then create
        assert call_count[0] == 2

        # Verify create command structure (second call)
        create_cmd = created_commands[1]
        assert create_cmd[0] == "gh"
        assert create_cmd[1] == "issue"
        assert create_cmd[2] == "develop"
        assert create_cmd[3] == "42"
        assert "--name" in create_cmd
        assert "42-new-feature" in create_cmd
        assert "--list" not in create_cmd


def test_create_development_branch_returns_existing(monkeypatch: MonkeyPatch) -> None:
    """Test create_development_branch returns existing branch without creating."""
    call_count = [0]

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        call_count[0] += 1
        # get_linked_branch returns existing branch
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="123-existing-branch\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issue_link = RealIssueLinkBranches()
        # Even though we pass a branch_name, existing branch takes precedence
        result = issue_link.create_development_branch(
            Path("/repo"), 123, branch_name="123-new-name"
        )

        assert result.branch_name == "123-existing-branch"
        assert result.issue_number == 123
        assert result.already_existed is True

        # Should only have made 1 call (list check), no create
        assert call_count[0] == 1


def test_create_development_branch_with_base_branch(monkeypatch: MonkeyPatch) -> None:
    """Test create_development_branch includes --base when specified."""
    created_commands: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)

        # First call: list returns empty
        if "--list" in cmd:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="",
                stderr="",
            )

        # Second call: create returns success
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issue_link = RealIssueLinkBranches()
        result = issue_link.create_development_branch(
            Path("/repo"), 42, branch_name="42-feature", base_branch="develop"
        )

        assert result.branch_name == "42-feature"
        assert result.already_existed is False

        # Verify create command includes --name and --base
        create_cmd = created_commands[1]
        assert "--name" in create_cmd
        assert "42-feature" in create_cmd
        assert "--base" in create_cmd
        assert "develop" in create_cmd


def test_create_development_branch_without_base_branch(monkeypatch: MonkeyPatch) -> None:
    """Test create_development_branch omits --base when not specified."""
    created_commands: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        created_commands.append(cmd)

        if "--list" in cmd:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="",
                stderr="",
            )

        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issue_link = RealIssueLinkBranches()
        issue_link.create_development_branch(Path("/repo"), 42, branch_name="42-feature")

        # Verify create command includes --name but NOT --base
        create_cmd = created_commands[1]
        assert "--name" in create_cmd
        assert "42-feature" in create_cmd
        assert "--base" not in create_cmd


def test_create_development_branch_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test create_development_branch raises RuntimeError on gh CLI failure."""
    call_count = [0]

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        call_count[0] += 1

        # First call succeeds (list returns empty)
        if "--list" in cmd:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="",
                stderr="",
            )

        # Second call (create) fails
        raise RuntimeError("gh command failed: issue not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        issue_link = RealIssueLinkBranches()

        with pytest.raises(RuntimeError, match="issue not found"):
            issue_link.create_development_branch(Path("/repo"), 999, branch_name="999-feature")


def test_create_development_branch_uses_provided_name(monkeypatch: MonkeyPatch) -> None:
    """Test create_development_branch uses provided branch_name directly."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        if "--list" in cmd:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="",
                stderr="",
            )

        # gh issue develop no longer returns branch name when --name is used
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        issue_link = RealIssueLinkBranches()
        result = issue_link.create_development_branch(
            Path("/repo"), 42, branch_name="42-my-custom-branch"
        )

        # Branch name comes from what we pass in, not from stdout
        assert result.branch_name == "42-my-custom-branch"
