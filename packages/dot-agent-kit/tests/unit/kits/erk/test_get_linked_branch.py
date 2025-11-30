"""Unit tests for get_linked_branch kit CLI command.

Tests retrieval of development branches linked to GitHub issues via gh CLI.
"""

import json
import subprocess

import pytest
from click.testing import CliRunner

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.get_linked_branch import (
    LinkedBranchError,
    LinkedBranchResult,
    _get_linked_branch_impl,
)
from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.get_linked_branch import (
    get_linked_branch as get_linked_branch_command,
)


def _make_completed_process(
    returncode: int,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    """Create a CompletedProcess for testing."""
    return subprocess.CompletedProcess(
        args=["gh", "issue", "develop", "--list"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


# ============================================================================
# 1. Successful Branch Retrieval Tests
# ============================================================================


def test_get_linked_branch_success() -> None:
    """Test successful retrieval of linked branch."""
    # gh issue develop --list returns: branch-name\tURL
    result = _get_linked_branch_impl(
        123,
        run_command=_make_completed_process(
            returncode=0,
            stdout="123-feature-name\thttps://github.com/owner/repo/tree/123-feature-name\n",
        ),
    )
    assert isinstance(result, LinkedBranchResult)
    assert result.success is True
    assert result.issue_number == 123
    assert result.branch_name == "123-feature-name"


def test_get_linked_branch_multiple_branches() -> None:
    """Test when multiple branches are linked - returns first one."""
    # Multiple branches linked to same issue
    result = _get_linked_branch_impl(
        456,
        run_command=_make_completed_process(
            returncode=0,
            stdout="456-first-branch\thttps://github.com/owner/repo/tree/456-first-branch\n"
            "456-second-branch\thttps://github.com/owner/repo/tree/456-second-branch\n",
        ),
    )
    assert isinstance(result, LinkedBranchResult)
    assert result.success is True
    assert result.branch_name == "456-first-branch"


def test_get_linked_branch_hyphenated_name() -> None:
    """Test branch name with hyphens."""
    result = _get_linked_branch_impl(
        789,
        run_command=_make_completed_process(
            returncode=0,
            stdout="789-feature-with-hyphens\thttps://github.com/owner/repo/tree/789-feature-with-hyphens\n",
        ),
    )
    assert isinstance(result, LinkedBranchResult)
    assert result.branch_name == "789-feature-with-hyphens"


def test_get_linked_branch_slash_in_name() -> None:
    """Test branch name with slashes."""
    result = _get_linked_branch_impl(
        100,
        run_command=_make_completed_process(
            returncode=0,
            stdout="feature/100-add-login\thttps://github.com/owner/repo/tree/feature/100-add-login\n",
        ),
    )
    assert isinstance(result, LinkedBranchResult)
    assert result.branch_name == "feature/100-add-login"


# ============================================================================
# 2. No Linked Branch Tests
# ============================================================================


def test_get_linked_branch_no_branch_empty_output() -> None:
    """Test when no branch is linked - empty output."""
    result = _get_linked_branch_impl(
        999,
        run_command=_make_completed_process(
            returncode=0,
            stdout="",
        ),
    )
    assert isinstance(result, LinkedBranchError)
    assert result.success is False
    assert result.error == "no_linked_branch"
    assert "#999" in result.message


def test_get_linked_branch_no_branch_whitespace_only() -> None:
    """Test when no branch is linked - whitespace only output."""
    result = _get_linked_branch_impl(
        888,
        run_command=_make_completed_process(
            returncode=0,
            stdout="   \n  \n",
        ),
    )
    assert isinstance(result, LinkedBranchError)
    assert result.success is False
    assert result.error == "no_linked_branch"


# ============================================================================
# 3. Error Handling Tests
# ============================================================================


def test_get_linked_branch_gh_command_failed() -> None:
    """Test when gh command fails."""
    result = _get_linked_branch_impl(
        123,
        run_command=_make_completed_process(
            returncode=1,
            stderr="gh: Could not resolve to an issue",
        ),
    )
    assert isinstance(result, LinkedBranchError)
    assert result.success is False
    assert result.error == "gh_command_failed"
    assert "Could not resolve" in result.message


def test_get_linked_branch_gh_not_authenticated() -> None:
    """Test when gh is not authenticated."""
    result = _get_linked_branch_impl(
        123,
        run_command=_make_completed_process(
            returncode=1,
            stderr="gh: To use GitHub CLI in a workflow, set the GH_TOKEN env var.",
        ),
    )
    assert isinstance(result, LinkedBranchError)
    assert result.success is False
    assert result.error == "gh_command_failed"
    assert "GH_TOKEN" in result.message


# ============================================================================
# 4. CLI Command Tests
# ============================================================================


def test_cli_success_with_linked_branch(monkeypatch: "pytest.MonkeyPatch") -> None:
    """Test CLI command with linked branch found."""
    from dot_agent_kit.data.kits.erk.kit_cli_commands.erk import get_linked_branch as module

    def mock_run_command(issue_number: int) -> subprocess.CompletedProcess[str]:
        return _make_completed_process(
            returncode=0,
            stdout="123-my-feature\thttps://github.com/owner/repo/tree/123-my-feature\n",
        )

    monkeypatch.setattr(module, "_run_gh_issue_develop_list", mock_run_command)

    runner = CliRunner()
    result = runner.invoke(get_linked_branch_command, ["123"])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 123
    assert output["branch_name"] == "123-my-feature"


def test_cli_no_linked_branch(monkeypatch: "pytest.MonkeyPatch") -> None:
    """Test CLI command when no linked branch found."""
    from dot_agent_kit.data.kits.erk.kit_cli_commands.erk import get_linked_branch as module

    def mock_run_command(issue_number: int) -> subprocess.CompletedProcess[str]:
        return _make_completed_process(returncode=0, stdout="")

    monkeypatch.setattr(module, "_run_gh_issue_develop_list", mock_run_command)

    runner = CliRunner()
    result = runner.invoke(get_linked_branch_command, ["456"])

    # no_linked_branch is not a CLI error - it's a valid response
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "no_linked_branch"


def test_cli_gh_command_failure(monkeypatch: "pytest.MonkeyPatch") -> None:
    """Test CLI command exits with error on gh failure."""
    from dot_agent_kit.data.kits.erk.kit_cli_commands.erk import get_linked_branch as module

    def mock_run_command(issue_number: int) -> subprocess.CompletedProcess[str]:
        return _make_completed_process(returncode=1, stderr="gh: error occurred")

    monkeypatch.setattr(module, "_run_gh_issue_develop_list", mock_run_command)

    runner = CliRunner()
    result = runner.invoke(get_linked_branch_command, ["789"])

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "gh_command_failed"


def test_cli_json_output_structure_success(monkeypatch: "pytest.MonkeyPatch") -> None:
    """Test that JSON output has expected structure on success."""
    from dot_agent_kit.data.kits.erk.kit_cli_commands.erk import get_linked_branch as module

    def mock_run_command(issue_number: int) -> subprocess.CompletedProcess[str]:
        return _make_completed_process(
            returncode=0,
            stdout="test-branch\thttps://github.com/owner/repo/tree/test-branch\n",
        )

    monkeypatch.setattr(module, "_run_gh_issue_develop_list", mock_run_command)

    runner = CliRunner()
    result = runner.invoke(get_linked_branch_command, ["100"])

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "issue_number" in output
    assert "branch_name" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["branch_name"], str)


def test_cli_json_output_structure_error(monkeypatch: "pytest.MonkeyPatch") -> None:
    """Test that JSON output has expected structure on error."""
    from dot_agent_kit.data.kits.erk.kit_cli_commands.erk import get_linked_branch as module

    def mock_run_command(issue_number: int) -> subprocess.CompletedProcess[str]:
        return _make_completed_process(returncode=0, stdout="")

    monkeypatch.setattr(module, "_run_gh_issue_develop_list", mock_run_command)

    runner = CliRunner()
    result = runner.invoke(get_linked_branch_command, ["200"])

    assert result.exit_code == 0  # no_linked_branch is not CLI error
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "error" in output
    assert "message" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["error"], str)
    assert isinstance(output["message"], str)
