"""Unit tests for get_pr_for_branch kit CLI command.

Tests retrieval of open PR numbers for branches via gh CLI.
"""

import json
import subprocess

import pytest
from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.get_pr_for_branch import (
    PrForBranchError,
    PrForBranchResult,
    _get_pr_for_branch_impl,
)
from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.get_pr_for_branch import (
    get_pr_for_branch as get_pr_for_branch_command,
)


def _make_completed_process(
    returncode: int,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    """Create a CompletedProcess for testing."""
    return subprocess.CompletedProcess(
        args=["gh", "pr", "list", "--state", "open", "--head", "test", "--json", "number"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


# ============================================================================
# 1. Successful PR Retrieval Tests
# ============================================================================


def test_get_pr_for_branch_success() -> None:
    """Test successful retrieval of PR for branch."""
    result = _get_pr_for_branch_impl(
        "123-feature",
        run_command=_make_completed_process(
            returncode=0,
            stdout='[{"number": 456}]',
        ),
    )
    assert isinstance(result, PrForBranchResult)
    assert result.success is True
    assert result.branch_name == "123-feature"
    assert result.pr_number == 456
    assert result.pr_exists is True


def test_get_pr_for_branch_large_pr_number() -> None:
    """Test with large PR number."""
    result = _get_pr_for_branch_impl(
        "big-pr-branch",
        run_command=_make_completed_process(
            returncode=0,
            stdout='[{"number": 99999}]',
        ),
    )
    assert isinstance(result, PrForBranchResult)
    assert result.pr_number == 99999
    assert result.pr_exists is True


def test_get_pr_for_branch_hyphenated_name() -> None:
    """Test branch name with hyphens."""
    result = _get_pr_for_branch_impl(
        "feat-add-user-auth",
        run_command=_make_completed_process(
            returncode=0,
            stdout='[{"number": 100}]',
        ),
    )
    assert isinstance(result, PrForBranchResult)
    assert result.branch_name == "feat-add-user-auth"
    assert result.pr_number == 100


def test_get_pr_for_branch_slash_in_name() -> None:
    """Test branch name with slashes."""
    result = _get_pr_for_branch_impl(
        "feature/add-login",
        run_command=_make_completed_process(
            returncode=0,
            stdout='[{"number": 200}]',
        ),
    )
    assert isinstance(result, PrForBranchResult)
    assert result.branch_name == "feature/add-login"
    assert result.pr_exists is True


# ============================================================================
# 2. No PR Found Tests
# ============================================================================


def test_get_pr_for_branch_no_pr_empty_array() -> None:
    """Test when no PR exists - empty JSON array."""
    result = _get_pr_for_branch_impl(
        "no-pr-branch",
        run_command=_make_completed_process(
            returncode=0,
            stdout="[]",
        ),
    )
    assert isinstance(result, PrForBranchResult)
    assert result.success is True
    assert result.branch_name == "no-pr-branch"
    assert result.pr_number is None
    assert result.pr_exists is False


def test_get_pr_for_branch_no_pr_empty_output() -> None:
    """Test when no PR exists - empty output."""
    result = _get_pr_for_branch_impl(
        "another-no-pr-branch",
        run_command=_make_completed_process(
            returncode=0,
            stdout="",
        ),
    )
    assert isinstance(result, PrForBranchResult)
    assert result.success is True
    assert result.pr_number is None
    assert result.pr_exists is False


def test_get_pr_for_branch_no_pr_whitespace_only() -> None:
    """Test when no PR exists - whitespace only output."""
    result = _get_pr_for_branch_impl(
        "whitespace-branch",
        run_command=_make_completed_process(
            returncode=0,
            stdout="   \n  ",
        ),
    )
    assert isinstance(result, PrForBranchResult)
    assert result.success is True
    assert result.pr_number is None
    assert result.pr_exists is False


# ============================================================================
# 3. Error Handling Tests
# ============================================================================


def test_get_pr_for_branch_gh_command_failed() -> None:
    """Test when gh command fails."""
    result = _get_pr_for_branch_impl(
        "error-branch",
        run_command=_make_completed_process(
            returncode=1,
            stderr="gh: error running pr list",
        ),
    )
    assert isinstance(result, PrForBranchError)
    assert result.success is False
    assert result.error == "gh_command_failed"
    assert "pr list" in result.message


def test_get_pr_for_branch_gh_not_authenticated() -> None:
    """Test when gh is not authenticated."""
    result = _get_pr_for_branch_impl(
        "auth-error-branch",
        run_command=_make_completed_process(
            returncode=1,
            stderr="gh: To use GitHub CLI, set the GH_TOKEN environment variable.",
        ),
    )
    assert isinstance(result, PrForBranchError)
    assert result.success is False
    assert result.error == "gh_command_failed"
    assert "GH_TOKEN" in result.message


def test_get_pr_for_branch_gh_repo_not_found() -> None:
    """Test when repository is not found."""
    result = _get_pr_for_branch_impl(
        "no-repo-branch",
        run_command=_make_completed_process(
            returncode=1,
            stderr="gh: Could not determine repository for current directory",
        ),
    )
    assert isinstance(result, PrForBranchError)
    assert result.success is False
    assert result.error == "gh_command_failed"


# ============================================================================
# 4. CLI Command Tests
# ============================================================================


def test_cli_success_with_pr(monkeypatch: "pytest.MonkeyPatch") -> None:
    """Test CLI command with PR found."""
    from dot_agent_kit.data.kits.erk.kit_cli_commands.erk import get_pr_for_branch as module

    def mock_run_command(branch_name: str) -> subprocess.CompletedProcess[str]:
        return _make_completed_process(
            returncode=0,
            stdout='[{"number": 789}]',
        )

    monkeypatch.setattr(module, "_run_gh_pr_list", mock_run_command)

    runner = CliRunner()
    result = runner.invoke(get_pr_for_branch_command, ["test-branch"])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["branch_name"] == "test-branch"
    assert output["pr_number"] == 789
    assert output["pr_exists"] is True


def test_cli_no_pr_found(monkeypatch: "pytest.MonkeyPatch") -> None:
    """Test CLI command when no PR found."""
    from dot_agent_kit.data.kits.erk.kit_cli_commands.erk import get_pr_for_branch as module

    def mock_run_command(branch_name: str) -> subprocess.CompletedProcess[str]:
        return _make_completed_process(returncode=0, stdout="[]")

    monkeypatch.setattr(module, "_run_gh_pr_list", mock_run_command)

    runner = CliRunner()
    result = runner.invoke(get_pr_for_branch_command, ["no-pr-branch"])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_exists"] is False
    assert output["pr_number"] is None


def test_cli_gh_command_failure(monkeypatch: "pytest.MonkeyPatch") -> None:
    """Test CLI command exits with error on gh failure."""
    from dot_agent_kit.data.kits.erk.kit_cli_commands.erk import get_pr_for_branch as module

    def mock_run_command(branch_name: str) -> subprocess.CompletedProcess[str]:
        return _make_completed_process(returncode=1, stderr="gh: error occurred")

    monkeypatch.setattr(module, "_run_gh_pr_list", mock_run_command)

    runner = CliRunner()
    result = runner.invoke(get_pr_for_branch_command, ["error-branch"])

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "gh_command_failed"


def test_cli_json_output_structure_success(monkeypatch: "pytest.MonkeyPatch") -> None:
    """Test that JSON output has expected structure on success with PR."""
    from dot_agent_kit.data.kits.erk.kit_cli_commands.erk import get_pr_for_branch as module

    def mock_run_command(branch_name: str) -> subprocess.CompletedProcess[str]:
        return _make_completed_process(
            returncode=0,
            stdout='[{"number": 123}]',
        )

    monkeypatch.setattr(module, "_run_gh_pr_list", mock_run_command)

    runner = CliRunner()
    result = runner.invoke(get_pr_for_branch_command, ["test-branch"])

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "branch_name" in output
    assert "pr_number" in output
    assert "pr_exists" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["branch_name"], str)
    assert isinstance(output["pr_number"], int)
    assert isinstance(output["pr_exists"], bool)


def test_cli_json_output_structure_no_pr(monkeypatch: "pytest.MonkeyPatch") -> None:
    """Test that JSON output has expected structure when no PR exists."""
    from dot_agent_kit.data.kits.erk.kit_cli_commands.erk import get_pr_for_branch as module

    def mock_run_command(branch_name: str) -> subprocess.CompletedProcess[str]:
        return _make_completed_process(returncode=0, stdout="[]")

    monkeypatch.setattr(module, "_run_gh_pr_list", mock_run_command)

    runner = CliRunner()
    result = runner.invoke(get_pr_for_branch_command, ["no-pr-branch"])

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "branch_name" in output
    assert "pr_number" in output
    assert "pr_exists" in output

    # pr_number should be null/None
    assert output["pr_number"] is None
    assert output["pr_exists"] is False


def test_cli_json_output_structure_error(monkeypatch: "pytest.MonkeyPatch") -> None:
    """Test that JSON output has expected structure on error."""
    from dot_agent_kit.data.kits.erk.kit_cli_commands.erk import get_pr_for_branch as module

    def mock_run_command(branch_name: str) -> subprocess.CompletedProcess[str]:
        return _make_completed_process(returncode=1, stderr="some error")

    monkeypatch.setattr(module, "_run_gh_pr_list", mock_run_command)

    runner = CliRunner()
    result = runner.invoke(get_pr_for_branch_command, ["error-branch"])

    assert result.exit_code == 1
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "error" in output
    assert "message" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["error"], str)
    assert isinstance(output["message"], str)
