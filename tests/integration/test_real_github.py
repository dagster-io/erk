"""Tests for RealGitHub with mocked subprocess execution.

These tests verify that RealGitHub correctly calls gh CLI commands and handles
responses. We use pytest monkeypatch to mock subprocess calls.
"""

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from erk_shared.gateway.time.fake import FakeTime
from erk_shared.github.real import RealGitHub
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
        ops = RealGitHub.for_test()
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
        ops = RealGitHub.for_test()
        result = ops.get_pr_base_branch(Path("/repo"), 456)

        assert result == "feature-branch"


def test_get_pr_base_branch_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test that get_pr_base_branch returns None on command failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("Failed to execute gh command")

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub.for_test()
        # Gracefully returns None on failure
        result = ops.get_pr_base_branch(Path("/repo"), 123)
        assert result is None


def test_get_pr_base_branch_file_not_found(monkeypatch: MonkeyPatch) -> None:
    """Test that get_pr_base_branch returns None when gh CLI not installed."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise FileNotFoundError("gh command not found")

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub.for_test()
        # Gracefully returns None when gh CLI not found
        result = ops.get_pr_base_branch(Path("/repo"), 123)
        assert result is None


# ============================================================================
# update_pr_base_branch() Tests
# ============================================================================


def test_update_pr_base_branch_success(monkeypatch: MonkeyPatch) -> None:
    """Test updating PR base branch successfully via REST API."""
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
        ops = RealGitHub.for_test()
        ops.update_pr_base_branch(Path("/repo"), 123, "new-base")

        # Verify REST API command format
        assert len(called_with) == 1
        cmd = called_with[0]
        assert cmd[0:4] == ["gh", "api", "--method", "PATCH"]
        assert "repos/{owner}/{repo}/pulls/123" in cmd[4]
        assert "-f" in cmd
        assert "base=new-base" in cmd


def test_update_pr_base_branch_command_failure(monkeypatch: MonkeyPatch) -> None:
    """Test that update_pr_base_branch silently handles command failures."""
    called_with = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        raise RuntimeError("Failed to execute gh command")

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub.for_test()
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
        ops = RealGitHub.for_test()
        # Gracefully degrades - silently fails when gh not found
        ops.update_pr_base_branch(Path("/repo"), 123, "new-base")
        # Verify the command was attempted
        assert len(called_with) == 1


# ============================================================================
# merge_pr() Tests
# ============================================================================


def test_merge_pr_with_squash() -> None:
    """Test merge_pr uses gh pr merge with --squash (no --delete-branch)."""
    repo_root = Path("/repo")
    pr_number = 123

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Verify gh pr merge command format WITHOUT --delete-branch
        # (--delete-branch fails from worktrees with "master already used by worktree")
        assert cmd[0:3] == ["gh", "pr", "merge"]
        assert "123" in cmd
        assert "--delete-branch" not in cmd  # Important: no --delete-branch
        assert "--squash" in cmd
        assert kwargs["cwd"] == repo_root
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["check"] is True

        # Return mock successful result
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="✓ Squashed and merged pull request #123\n",
            stderr="",
        )

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub.for_test()
        # Should not raise
        ops.merge_pr(repo_root, pr_number, squash=True, verbose=False)
    finally:
        subprocess.run = original_run


def test_merge_pr_without_squash() -> None:
    """Test merge_pr uses gh pr merge without --squash (no --delete-branch)."""
    repo_root = Path("/repo")
    pr_number = 456

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Verify gh pr merge command format WITHOUT --delete-branch
        assert cmd[0:3] == ["gh", "pr", "merge"]
        assert "456" in cmd
        assert "--delete-branch" not in cmd  # Important: no --delete-branch
        # Verify --squash is NOT included when squash=False
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

        ops = RealGitHub.for_test()
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

        ops = RealGitHub.for_test()

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
    """Test successful PR creation via REST API."""
    repo_root = Path("/repo")

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Verify REST API command format
        assert cmd[0:4] == ["gh", "api", "--method", "POST"]
        assert "repos/{owner}/{repo}/pulls" in cmd[4]
        assert "-f" in cmd
        assert "head=feat-test" in cmd
        assert "title=Test PR" in cmd
        assert "body=Test body" in cmd
        assert "base=main" in cmd
        assert kwargs["cwd"] == repo_root
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        assert kwargs["check"] is True

        # Return mock PR JSON response
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout='{"number": 123, "html_url": "https://github.com/owner/repo/pull/123"}\n',
            stderr="",
        )

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub.for_test()
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
    """Test PR creation without specifying base branch via REST API."""
    repo_root = Path("/repo")

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Verify REST API command format
        assert cmd[0:4] == ["gh", "api", "--method", "POST"]
        assert "repos/{owner}/{repo}/pulls" in cmd[4]
        assert "head=feat-test" in cmd
        assert "title=Test PR" in cmd
        assert "body=Test body" in cmd
        # Verify base is NOT included when base=None
        cmd_str = " ".join(cmd)
        assert "base=" not in cmd_str

        # Return mock PR JSON response
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout='{"number": 456, "html_url": "https://github.com/owner/repo/pull/456"}\n',
            stderr="",
        )

    original_run = subprocess.run
    try:
        subprocess.run = mock_run

        ops = RealGitHub.for_test()
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

        ops = RealGitHub.for_test()

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

        ops = RealGitHub.for_test()
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

        ops = RealGitHub.for_test()
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

        ops = RealGitHub.for_test()

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

        ops = RealGitHub.for_test()

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

        ops = RealGitHub.for_test()

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
        ops = RealGitHub.for_test()
        run_id = ops.trigger_workflow(
            repo_root=repo_root,
            workflow="test-workflow.yml",
            inputs={"issue_number": "1"},
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
        ops = RealGitHub.for_test()

        # Should raise error for invalid response format
        with pytest.raises(RuntimeError) as exc_info:
            ops.trigger_workflow(
                repo_root=repo_root,
                workflow="test-workflow.yml",
                inputs={"issue_number": "1"},
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
        ops = RealGitHub.for_test(time=fake_time)

        # Should raise error after max attempts
        with pytest.raises(RuntimeError) as exc_info:
            ops.trigger_workflow(
                repo_root=repo_root,
                workflow="test-workflow.yml",
                inputs={"issue_number": "1"},
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
        ops = RealGitHub.for_test()
        run_id = ops.trigger_workflow(
            repo_root=repo_root,
            workflow="test-workflow.yml",
            inputs={"issue_number": "1"},
        )

        # Should find the non-skipped/cancelled run
        assert run_id == "333"
        assert call_count >= 3  # trigger + 2 polls


# ============================================================================
# REST API Command Format Tests
# ============================================================================
# These tests verify that PR query methods use the REST API (gh api) instead of
# GraphQL (gh pr view --json), ensuring we use the separate REST quota.


def test_get_pr_base_branch_uses_rest_api(monkeypatch: MonkeyPatch) -> None:
    """Test that get_pr_base_branch uses REST API endpoint."""
    called_with: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="main\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub.for_test()
        ops.get_pr_base_branch(Path("/repo"), 123)

        assert len(called_with) == 1
        cmd = called_with[0]
        # Verify REST API format: gh api repos/{owner}/{repo}/pulls/123 --jq .base.ref
        assert cmd[0:2] == ["gh", "api"]
        assert "repos/{owner}/{repo}/pulls/123" in cmd[2]
        assert "--jq" in cmd
        assert ".base.ref" in cmd


def test_get_pr_title_uses_rest_api(monkeypatch: MonkeyPatch) -> None:
    """Test that get_pr_title uses REST API endpoint."""
    called_with: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="Fix bug in parser\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub.for_test()
        result = ops.get_pr_title(Path("/repo"), 456)

        assert result == "Fix bug in parser"
        assert len(called_with) == 1
        cmd = called_with[0]
        # Verify REST API format: gh api repos/{owner}/{repo}/pulls/456 --jq .title
        assert cmd[0:2] == ["gh", "api"]
        assert "repos/{owner}/{repo}/pulls/456" in cmd[2]
        assert "--jq" in cmd
        assert ".title" in cmd


def test_get_pr_body_uses_rest_api(monkeypatch: MonkeyPatch) -> None:
    """Test that get_pr_body uses REST API endpoint."""
    called_with: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="This PR fixes a critical bug.\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub.for_test()
        result = ops.get_pr_body(Path("/repo"), 789)

        assert result == "This PR fixes a critical bug."
        assert len(called_with) == 1
        cmd = called_with[0]
        # Verify REST API format: gh api repos/{owner}/{repo}/pulls/789 --jq .body
        assert cmd[0:2] == ["gh", "api"]
        assert "repos/{owner}/{repo}/pulls/789" in cmd[2]
        assert "--jq" in cmd
        assert ".body" in cmd


def test_has_pr_label_uses_rest_api(monkeypatch: MonkeyPatch) -> None:
    """Test that has_pr_label uses REST API endpoint."""
    called_with: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="bug\nenhancement\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub.for_test()
        result = ops.has_pr_label(Path("/repo"), 101, "bug")

        assert result is True
        assert len(called_with) == 1
        cmd = called_with[0]
        # Verify REST API format: gh api repos/{owner}/{repo}/pulls/101 --jq .labels[].name
        assert cmd[0:2] == ["gh", "api"]
        assert "repos/{owner}/{repo}/pulls/101" in cmd[2]
        assert "--jq" in cmd
        assert ".labels[].name" in cmd


def test_has_pr_label_returns_false_when_label_not_present(monkeypatch: MonkeyPatch) -> None:
    """Test that has_pr_label returns False when label is not in the list."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="bug\nenhancement\n",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub.for_test()
        result = ops.has_pr_label(Path("/repo"), 101, "urgent")

        assert result is False


# ============================================================================
# delete_remote_branch() Tests
# ============================================================================


def test_delete_remote_branch_success(monkeypatch: MonkeyPatch) -> None:
    """Test delete_remote_branch uses correct REST API endpoint."""
    called_with: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        # DELETE returns empty response on success
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub.for_test()
        result = ops.delete_remote_branch(Path("/repo"), "feature-branch")

        assert result is True
        assert len(called_with) == 1
        cmd = called_with[0]
        # Verify REST API: gh api --method DELETE repos/.../git/refs/heads/{branch}
        assert cmd[0:4] == ["gh", "api", "--method", "DELETE"]
        assert "repos/{owner}/{repo}/git/refs/heads/feature-branch" in cmd[4]


def test_delete_remote_branch_not_found_returns_true(monkeypatch: MonkeyPatch) -> None:
    """Test delete_remote_branch returns True when branch doesn't exist (404)."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Simulate 404 error from GitHub API
        raise subprocess.CalledProcessError(1, cmd, stderr="Reference does not exist")

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub.for_test()
        # Should return True even for 404 (branch already deleted)
        result = ops.delete_remote_branch(Path("/repo"), "nonexistent-branch")

        assert result is True


def test_delete_remote_branch_other_error_returns_false(monkeypatch: MonkeyPatch) -> None:
    """Test delete_remote_branch returns False on other errors (e.g., protected branch)."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        # Simulate error from protected branch or auth failure
        raise subprocess.CalledProcessError(1, cmd, stderr="Cannot delete protected branch")

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGitHub.for_test()
        # Should return False for errors other than 404
        result = ops.delete_remote_branch(Path("/repo"), "protected-branch")

        assert result is False


# ============================================================================
# list_prs() Tests
# ============================================================================


def test_list_prs_success(monkeypatch: MonkeyPatch) -> None:
    """Test list_prs returns dict of PRs keyed by branch name."""
    called_with: list[list[str]] = []

    sample_response = json.dumps(
        [
            {
                "number": 123,
                "state": "open",
                "html_url": "https://github.com/owner/repo/pull/123",
                "draft": False,
                "title": "Feature A",
                "head": {"ref": "feature-a"},
            },
            {
                "number": 456,
                "state": "open",
                "html_url": "https://github.com/owner/repo/pull/456",
                "draft": True,
                "title": "Feature B",
                "head": {"ref": "feature-b"},
            },
        ]
    )

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=sample_response,
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        from erk_shared.github.types import RepoInfo

        ops = RealGitHub.for_test(repo_info=RepoInfo(owner="owner", name="repo"))
        result = ops.list_prs(Path("/repo"), state="open")

        # Verify REST API command format
        assert len(called_with) == 1
        cmd = called_with[0]
        assert cmd[0:2] == ["gh", "api"]
        assert "/repos/owner/repo/pulls?state=open&per_page=100" in cmd[2]

        # Verify result
        assert len(result) == 2
        assert "feature-a" in result
        assert "feature-b" in result
        assert result["feature-a"].number == 123
        assert result["feature-a"].state == "OPEN"
        assert result["feature-a"].is_draft is False
        assert result["feature-b"].number == 456
        assert result["feature-b"].is_draft is True


def test_list_prs_with_closed_state(monkeypatch: MonkeyPatch) -> None:
    """Test list_prs filters by closed state."""
    called_with: list[list[str]] = []

    sample_response = json.dumps(
        [
            {
                "number": 789,
                "state": "closed",
                "merged": False,
                "html_url": "https://github.com/owner/repo/pull/789",
                "draft": False,
                "title": "Closed PR",
                "head": {"ref": "closed-branch"},
            },
        ]
    )

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=sample_response,
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        from erk_shared.github.types import RepoInfo

        ops = RealGitHub.for_test(repo_info=RepoInfo(owner="owner", name="repo"))
        result = ops.list_prs(Path("/repo"), state="closed")

        # Verify state parameter passed
        assert len(called_with) == 1
        assert "state=closed" in called_with[0][2]

        # Verify result
        assert len(result) == 1
        assert result["closed-branch"].state == "CLOSED"


def test_list_prs_merged_state(monkeypatch: MonkeyPatch) -> None:
    """Test list_prs correctly identifies merged PRs."""
    sample_response = json.dumps(
        [
            {
                "number": 999,
                "state": "closed",
                "merged": True,
                "html_url": "https://github.com/owner/repo/pull/999",
                "draft": False,
                "title": "Merged PR",
                "head": {"ref": "merged-branch"},
            },
        ]
    )

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=sample_response,
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        from erk_shared.github.types import RepoInfo

        ops = RealGitHub.for_test(repo_info=RepoInfo(owner="owner", name="repo"))
        result = ops.list_prs(Path("/repo"), state="all")

        assert result["merged-branch"].state == "MERGED"


def test_list_prs_api_failure_returns_empty(monkeypatch: MonkeyPatch) -> None:
    """Test list_prs returns empty dict on API failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("API failure")

    with mock_subprocess_run(monkeypatch, mock_run):
        from erk_shared.github.types import RepoInfo

        ops = RealGitHub.for_test(repo_info=RepoInfo(owner="owner", name="repo"))
        result = ops.list_prs(Path("/repo"), state="open")

        # Should return empty dict, not raise
        assert result == {}


# ============================================================================
# get_open_prs_with_base_branch() Tests
# ============================================================================


def test_get_open_prs_with_base_branch_success(monkeypatch: MonkeyPatch) -> None:
    """Test get_open_prs_with_base_branch uses correct REST API endpoint."""
    called_with: list[list[str]] = []

    sample_response = json.dumps(
        [
            {
                "number": 123,
                "state": "open",
                "html_url": "https://github.com/owner/repo/pull/123",
                "draft": False,
                "title": "Feature A",
                "head": {"ref": "feature-a"},
            },
            {
                "number": 456,
                "state": "open",
                "html_url": "https://github.com/owner/repo/pull/456",
                "draft": True,
                "title": "Feature B",
                "head": {"ref": "feature-b"},
            },
        ]
    )

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout=sample_response,
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        from erk_shared.github.types import RepoInfo

        ops = RealGitHub.for_test(repo_info=RepoInfo(owner="owner", name="repo"))
        result = ops.get_open_prs_with_base_branch(Path("/repo"), "main")

        # Verify REST API command format
        assert len(called_with) == 1
        cmd = called_with[0]
        assert cmd[0:2] == ["gh", "api"]
        assert "/repos/owner/repo/pulls?base=main&state=open&per_page=100" in cmd[2]

        # Verify result
        assert len(result) == 2
        assert result[0].number == 123
        assert result[0].state == "OPEN"
        assert result[0].head_branch == "feature-a"
        assert result[0].is_draft is False
        assert result[1].number == 456
        assert result[1].head_branch == "feature-b"
        assert result[1].is_draft is True


def test_get_open_prs_with_base_branch_empty_result(monkeypatch: MonkeyPatch) -> None:
    """Test get_open_prs_with_base_branch returns empty list when no matching PRs."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="[]",
            stderr="",
        )

    with mock_subprocess_run(monkeypatch, mock_run):
        from erk_shared.github.types import RepoInfo

        ops = RealGitHub.for_test(repo_info=RepoInfo(owner="owner", name="repo"))
        result = ops.get_open_prs_with_base_branch(Path("/repo"), "feature-1")

        assert result == []


def test_get_open_prs_with_base_branch_api_failure_returns_empty(
    monkeypatch: MonkeyPatch,
) -> None:
    """Test get_open_prs_with_base_branch returns empty list on API failure."""

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise RuntimeError("API failure")

    with mock_subprocess_run(monkeypatch, mock_run):
        from erk_shared.github.types import RepoInfo

        ops = RealGitHub.for_test(repo_info=RepoInfo(owner="owner", name="repo"))
        result = ops.get_open_prs_with_base_branch(Path("/repo"), "main")

        # Should return empty list, not raise
        assert result == []
