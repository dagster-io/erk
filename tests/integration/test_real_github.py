"""Tests for RealGitHub with mocked subprocess execution.

These tests verify that RealGitHub correctly calls gh CLI commands and handles
responses. We use pytest monkeypatch to mock subprocess calls.
"""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from erk_shared.github.real import RealGitHub
from erk_shared.integrations.time.fake import FakeTime
from pytest import MonkeyPatch

from tests.integration.test_helpers import mock_subprocess_run

# ============================================================================
# get_pr_base_branch() Tests
# ============================================================================


def test_get_pr_base_branch_success(monkeypatch: MonkeyPatch) -> None:
    """Test getting PR base branch successfully."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="main\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub(FakeTime())
        result = ops.get_pr_base_branch(Path("/repo"), 123)

        assert result == "main"


def test_get_pr_base_branch_with_whitespace(monkeypatch: MonkeyPatch) -> None:
    """Test that get_pr_base_branch strips whitespace."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="  feature-branch  \n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub(FakeTime())
        result = ops.get_pr_base_branch(Path("/repo"), 456)

        assert result == "feature-branch"


def test_get_pr_base_branch_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test that get_pr_base_branch returns None on command failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Failed to execute gh command")

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub(FakeTime())
        # Gracefully returns None on failure
        result = ops.get_pr_base_branch(Path("/repo"), 123)
        assert result is None


def test_get_pr_base_branch_file_not_found(monkeypatch: MonkeyPatch) -> None:
    """Test that get_pr_base_branch returns None when gh CLI not installed."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise FileNotFoundError("gh command not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub(FakeTime())
        # Gracefully returns None when gh CLI not found
        result = ops.get_pr_base_branch(Path("/repo"), 123)
        assert result is None


# ============================================================================
# update_pr_base_branch() Tests
# ============================================================================


def test_update_pr_base_branch_success(monkeypatch: MonkeyPatch) -> None:
    """Test updating PR base branch successfully."""
    called_with = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub(FakeTime())
        ops.update_pr_base_branch(Path("/repo"), 123, "new-base")

        # Verify command was called correctly
        assert len(called_with) == 1
        assert called_with[0] == ["gh", "pr", "edit", "123", "--base", "new-base"]


def test_update_pr_base_branch_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test that update_pr_base_branch silently handles command failures."""
    called_with = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        raise RuntimeError("Failed to execute gh command")

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub(FakeTime())
        # Gracefully degrades - silently fails without raising
        ops.update_pr_base_branch(Path("/repo"), 123, "new-base")
        # Verify the command was attempted
        assert len(called_with) == 1


def test_update_pr_base_branch_file_not_found(monkeypatch: MonkeyPatch) -> None:
    """Test that update_pr_base_branch silently handles gh CLI not installed."""
    called_with = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        raise FileNotFoundError("gh command not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub(FakeTime())
        # Gracefully degrades - silently fails when gh not found
        ops.update_pr_base_branch(Path("/repo"), 123, "new-base")
        # Verify the command was attempted
        assert len(called_with) == 1


# ============================================================================
# merge_pr() Tests
# ============================================================================


def test_merge_pr_with_squash() -> None:
    """Test merge_pr calls gh pr merge with squash strategy."""
    repo_root = Path("/repo")
    pr_number = 123

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Verify correct command is called
        assert cmd == ["gh", "pr", "merge", "123", "--squash"]
        assert kwargs["cwd"] == repo_root
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["check"] is True

        # Return mock successful result
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="✓ Merged pull request #123\n",
            stderr="",
        )

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub(FakeTime())
        # Should not raise
        ops.merge_pr(repo_root, pr_number, squash=True, verbose=False)
    finally:
        subprocess.run = original_run


def test_merge_pr_without_squash() -> None:
    """Test merge_pr can be called without squash strategy."""
    repo_root = Path("/repo")
    pr_number = 456

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Verify squash flag is NOT included when squash=False
        assert cmd == ["gh", "pr", "merge", "456"]
        assert "--squash" not in cmd

        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="✓ Merged pull request #456\n",
            stderr="",
        )

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub(FakeTime())
        ops.merge_pr(repo_root, pr_number, squash=False, verbose=False)
    finally:
        subprocess.run = original_run


def test_merge_pr_returns_error_string_on_failure() -> None:
    """Test merge_pr returns error message string when gh pr merge fails."""
    repo_root = Path("/repo")
    pr_number = 789

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise subprocess.CalledProcessError(1, cmd, stderr="PR not found")

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub(FakeTime())

        # Should return error message string (not False)
        result = ops.merge_pr(repo_root, pr_number, squash=True, verbose=False)
        assert isinstance(result, str)
        assert "PR not found" in result
    finally:
        subprocess.run = original_run


# ============================================================================
# create_pr() Tests
# ============================================================================


def test_create_pr_success() -> None:
    """Test successful PR creation."""
    repo_root = Path("/repo")

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Verify correct command is called
        assert cmd == [
            "gh",
            "pr",
            "create",
            "--head",
            "feat-test",
            "--title",
            "Test PR",
            "--body",
            "Test body",
            "--base",
            "main",
        ]
        assert kwargs["cwd"] == repo_root
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["check"] is True

        # Return mock PR URL
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="https://github.com/owner/repo/pull/123\n",
            stderr="",
        )

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub(FakeTime())
        pr_number = ops.create_pr(
            repo_root=repo_root,
            branch="feat-test",
            title="Test PR",
            body="Test body",
            base="main",
        )

        assert pr_number == 123
    finally:
        subprocess.run = original_run


def test_create_pr_without_base() -> None:
    """Test PR creation without specifying base branch."""
    repo_root = Path("/repo")

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Verify --base flag is NOT included when base=None
        assert cmd == [
            "gh",
            "pr",
            "create",
            "--head",
            "feat-test",
            "--title",
            "Test PR",
            "--body",
            "Test body",
        ]
        assert "--base" not in cmd

        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="https://github.com/owner/repo/pull/456\n",
            stderr="",
        )

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub(FakeTime())
        pr_number = ops.create_pr(
            repo_root=repo_root,
            branch="feat-test",
            title="Test PR",
            body="Test body",
            base=None,
        )

        assert pr_number == 456
    finally:
        subprocess.run = original_run


def test_create_pr_failure() -> None:
    """Test PR creation failure handling."""
    repo_root = Path("/repo")

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise subprocess.CalledProcessError(1, cmd, stderr="Error: PR already exists")

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub(FakeTime())

        # Should raise RuntimeError (from run_subprocess_with_context wrapper)
        with pytest.raises(RuntimeError) as exc_info:
            ops.create_pr(
                repo_root=repo_root,
                branch="feat-test",
                title="Test PR",
                body="Test body",
                base="main",
            )

        # Verify error context includes operation description
        assert "create pull request" in str(exc_info.value)
    finally:
        subprocess.run = original_run


# ============================================================================
# list_workflow_runs() Tests
# ============================================================================


def test_list_workflow_runs_success() -> None:
    """Test list_workflow_runs parses gh run list output correctly."""
    repo_root = Path("/repo")

    sample_response = json.dumps(
        [
            {
                "databaseId": 1234567890,
                "status": "completed",
                "conclusion": "success",
                "headBranch": "feat-1",
                "headSha": "abc123def456",
                "createdAt": "2025-01-15T10:30:00Z",
            },
            {
                "databaseId": 1234567891,
                "status": "completed",
                "conclusion": "failure",
                "headBranch": "feat-2",
                "headSha": "def456ghi789",
                "createdAt": "2025-01-15T11:00:00Z",
            },
            {
                "databaseId": 1234567892,
                "status": "in_progress",
                "conclusion": None,
                "headBranch": "feat-3",
                "headSha": "ghi789jkl012",
                "createdAt": "2025-01-15T11:30:00Z",
            },
        ]
    )

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Verify command structure
        assert cmd == [
            "gh",
            "run",
            "list",
            "--workflow",
            "implement-plan.yml",
            "--json",
            "databaseId,status,conclusion,headBranch,headSha,displayTitle,createdAt",
            "--limit",
            "50",
        ]

        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=sample_response,
            stderr="",
        )

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub(FakeTime())
        result = ops.list_workflow_runs(repo_root, "implement-plan.yml", limit=50)

        assert len(result) == 3
        assert result[0].run_id == "1234567890"
        assert result[0].status == "completed"
        assert result[0].conclusion == "success"
        assert result[0].branch == "feat-1"
        assert result[0].head_sha == "abc123def456"
        assert result[0].created_at == datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)

        assert result[1].conclusion == "failure"
        assert result[1].created_at == datetime(2025, 1, 15, 11, 0, 0, tzinfo=UTC)
        assert result[2].status == "in_progress"
        assert result[2].conclusion is None
        assert result[2].created_at == datetime(2025, 1, 15, 11, 30, 0, tzinfo=UTC)
    finally:
        subprocess.run = original_run


def test_list_workflow_runs_custom_limit() -> None:
    """Test list_workflow_runs respects custom limit parameter."""
    repo_root = Path("/repo")

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Verify custom limit is passed
        assert "--limit" in cmd
        assert "10" in cmd

        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="[]", stderr="")

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub(FakeTime())
        result = ops.list_workflow_runs(repo_root, "test.yml", limit=10)

        assert result == []
    finally:
        subprocess.run = original_run


def test_list_workflow_runs_command_failure() -> None:
    """Test list_workflow_runs propagates errors on command failure."""
    repo_root = Path("/repo")

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise subprocess.CalledProcessError(1, cmd, stderr="gh not authenticated")

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub(FakeTime())

        # Should raise RuntimeError with helpful message instead of silently failing
        with pytest.raises(RuntimeError, match="gh not authenticated"):
            ops.list_workflow_runs(repo_root, "test.yml")
    finally:
        subprocess.run = original_run


def test_list_workflow_runs_json_decode_error() -> None:
    """Test list_workflow_runs propagates JSONDecodeError on malformed JSON."""
    repo_root = Path("/repo")

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="not valid json", stderr=""
        )

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub(FakeTime())

        # Should raise JSONDecodeError instead of silently failing
        with pytest.raises(json.JSONDecodeError):
            ops.list_workflow_runs(repo_root, "test.yml")
    finally:
        subprocess.run = original_run


def test_list_workflow_runs_missing_fields() -> None:
    """Test list_workflow_runs propagates KeyError when JSON has missing fields."""
    repo_root = Path("/repo")

    # Missing 'headBranch' field
    sample_response = json.dumps(
        [
            {
                "databaseId": 123,
                "status": "completed",
                "conclusion": "success",
                # headBranch missing
                "headSha": "abc123",
            }
        ]
    )

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout=sample_response, stderr=""
        )

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub(FakeTime())

        # Should raise KeyError instead of silently failing
        with pytest.raises(KeyError, match="headBranch"):
            ops.list_workflow_runs(repo_root, "test.yml")
    finally:
        subprocess.run = original_run


# ============================================================================
# trigger_workflow() Tests - Edge Cases for Polling Logic
# ============================================================================


def test_trigger_workflow_handles_empty_list_during_polling(monkeypatch: MonkeyPatch) -> None:
    """Test trigger_workflow continues polling when run list is empty."""
    repo_root = Path("/repo")
    call_count = 0
    captured_distinct_id = None

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        nonlocal call_count, captured_distinct_id
        call_count += 1

        # First call: gh workflow run (trigger) - capture distinct_id from inputs
        if "workflow" in cmd and "run" in cmd:
            # Extract distinct_id from the -f distinct_id=xxx argument
            for i, arg in enumerate(cmd):
                if arg == "-f" and i + 1 < len(cmd) and cmd[i + 1].startswith("distinct_id="):
                    captured_distinct_id = cmd[i + 1].split("=", 1)[1]
                    break
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="",
                stderr="",
            )

        # Second call: gh run list (returns empty list - workflow not appeared yet)
        if call_count == 2:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="[]",
                stderr="",
            )

        # Third call: gh run list (workflow appears now with captured distinct_id)
        run_data = json.dumps(
            [
                {
                    "databaseId": 123456,
                    "displayTitle": f"Test workflow: issue-1:{captured_distinct_id}",
                    "conclusion": None,
                }
            ]
        )
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=run_data,
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub(FakeTime())
        run_id = ops.trigger_workflow(
            repo_root,
            "test-workflow.yml",
            {"issue_number": "1"},
        )

        # Should successfully find run ID after empty list
        assert run_id == "123456"
        assert call_count >= 3  # trigger + at least 2 polls


def test_trigger_workflow_errors_on_invalid_json_structure(monkeypatch: MonkeyPatch) -> None:
    """Test trigger_workflow raises error when gh returns non-list JSON."""
    repo_root = Path("/repo")

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # First call: gh workflow run (trigger)
        if "workflow" in cmd and "run" in cmd:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="",
                stderr="",
            )

        # Second call: gh run list (returns invalid JSON structure - dict instead of list)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout='{"error": "invalid"}',
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub(FakeTime())

        # Should raise error for invalid response format
        with pytest.raises(RuntimeError) as exc_info:
            ops.trigger_workflow(
                repo_root,
                "test-workflow.yml",
                {"issue_number": "1"},
            )

        error_msg = str(exc_info.value)
        assert "invalid response format" in error_msg
        assert "Expected JSON array" in error_msg


def test_trigger_workflow_timeout_after_max_attempts(monkeypatch: MonkeyPatch) -> None:
    """Test trigger_workflow raises error after exhausting retry attempts."""
    repo_root = Path("/repo")

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # First call: gh workflow run (trigger)
        if "workflow" in cmd and "run" in cmd:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="",
                stderr="",
            )

        # All polling calls: return empty list (workflow never appears)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        # Use FakeTime that never sleeps
        fake_time = FakeTime()
        ops = RealGitHub(fake_time)

        # Should raise error after max attempts
        with pytest.raises(RuntimeError) as exc_info:
            ops.trigger_workflow(
                repo_root,
                "test-workflow.yml",
                {"issue_number": "1"},
            )

        error_msg = str(exc_info.value)
        assert "could not find run" in error_msg
        assert "after 15 attempts" in error_msg
        assert "Debug commands:" in error_msg
        assert "gh run list --workflow test-workflow.yml" in error_msg


def test_trigger_workflow_skips_cancelled_runs(monkeypatch: MonkeyPatch) -> None:
    """Test trigger_workflow skips runs with conclusion skipped/cancelled."""
    repo_root = Path("/repo")
    call_count = 0
    captured_distinct_id = None

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        nonlocal call_count, captured_distinct_id
        call_count += 1

        # First call: gh workflow run (trigger) - capture distinct_id from inputs
        if "workflow" in cmd and "run" in cmd:
            # Extract distinct_id from the -f distinct_id=xxx argument
            for i, arg in enumerate(cmd):
                if arg == "-f" and i + 1 < len(cmd) and cmd[i + 1].startswith("distinct_id="):
                    captured_distinct_id = cmd[i + 1].split("=", 1)[1]
                    break
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="",
                stderr="",
            )

        # Second call: returns skipped and cancelled runs with captured distinct_id
        if call_count == 2:
            run_data = json.dumps(
                [
                    {
                        "databaseId": 111,
                        "displayTitle": f"Test: issue-1:{captured_distinct_id}",
                        "conclusion": "skipped",
                    },
                    {
                        "databaseId": 222,
                        "displayTitle": f"Test: issue-1:{captured_distinct_id}",
                        "conclusion": "cancelled",
                    },
                ]
            )
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=run_data,
                stderr="",
            )

        # Third call: returns valid run with captured distinct_id
        run_data = json.dumps(
            [
                {
                    "databaseId": 333,
                    "displayTitle": f"Test: issue-1:{captured_distinct_id}",
                    "conclusion": None,
                }
            ]
        )
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=run_data,
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub(FakeTime())
        run_id = ops.trigger_workflow(
            repo_root,
            "test-workflow.yml",
            {"issue_number": "1"},
        )

        # Should find the non-skipped/cancelled run
        assert run_id == "333"
        assert call_count >= 3  # trigger + 2 polls
