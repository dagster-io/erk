"""Unit tests for generate_pr_body kit CLI command.

Tests generating complete PR body with summary and footer.
Uses FakeGitHub, FakeGit, and FakePromptExecutor for dependency injection.
"""

import json
from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.prompt_executor.fake import FakePromptExecutor

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.data.kits.erk.scripts.erk.generate_pr_body import (
    GenerateError,
    GenerateSuccess,
    _build_summary_prompt,
    _generate_pr_body_impl,
)
from dot_agent_kit.data.kits.erk.scripts.erk.generate_pr_body import (
    generate_pr_body as generate_pr_body_command,
)

# ============================================================================
# 1. Prompt Building Tests (2 tests)
# ============================================================================


def test_build_summary_prompt_includes_diff_and_context() -> None:
    """Test that _build_summary_prompt includes diff content and branch context."""
    diff_content = "+added line\n-removed line"
    current_branch = "feature-branch"
    parent_branch = "main"

    prompt = _build_summary_prompt(diff_content, current_branch, parent_branch)

    # Should include diff
    assert "+added line" in prompt
    assert "-removed line" in prompt

    # Should include branch context
    assert "Current branch: feature-branch" in prompt
    assert "Parent branch: main" in prompt


def test_build_summary_prompt_uses_commit_message_system_prompt() -> None:
    """Test that _build_summary_prompt uses the shared commit message prompt."""
    prompt = _build_summary_prompt("diff", "branch", "main")

    # Should include key parts of COMMIT_MESSAGE_SYSTEM_PROMPT
    assert "Analyze the provided git diff" in prompt


# ============================================================================
# 2. Implementation Logic Tests (4 tests)
# ============================================================================


def test_impl_generates_body_with_summary_and_footer(tmp_path: Path) -> None:
    """Test that implementation generates body with summary and footer."""
    github = FakeGitHub(pr_diffs={123: "+added line"})
    git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "main"},
    )
    executor = FakePromptExecutor(output="Fix the authentication flow")

    result = _generate_pr_body_impl(github, git, executor, tmp_path, 123, issue_number=456)

    assert isinstance(result, GenerateSuccess)
    assert result.success is True
    assert "## Summary" in result.body
    assert "Fix the authentication flow" in result.body
    assert "Closes #456" in result.body
    assert "erk pr checkout 123" in result.body


def test_impl_omits_closes_when_no_issue(tmp_path: Path) -> None:
    """Test that Closes reference is omitted when no issue number."""
    github = FakeGitHub(pr_diffs={123: "+added line"})
    git = FakeGit()
    executor = FakePromptExecutor(output="Summary text")

    result = _generate_pr_body_impl(github, git, executor, tmp_path, 123, issue_number=None)

    assert isinstance(result, GenerateSuccess)
    assert "Closes #" not in result.body
    assert "erk pr checkout 123" in result.body


def test_impl_error_on_empty_diff(tmp_path: Path) -> None:
    """Test error when PR diff is empty."""
    github = FakeGitHub(pr_diffs={123: "   \n\t\n  "})
    git = FakeGit()
    executor = FakePromptExecutor(output="Summary")

    result = _generate_pr_body_impl(github, git, executor, tmp_path, 123, issue_number=None)

    assert isinstance(result, GenerateError)
    assert result.success is False
    assert result.error == "empty_diff"


def test_impl_error_on_claude_failure(tmp_path: Path) -> None:
    """Test error when Claude execution fails."""
    github = FakeGitHub(pr_diffs={123: "+added line"})
    git = FakeGit()
    executor = FakePromptExecutor(error="Model timeout", should_fail=True)

    result = _generate_pr_body_impl(github, git, executor, tmp_path, 123, issue_number=None)

    assert isinstance(result, GenerateError)
    assert result.success is False
    assert result.error == "claude_failed"


# ============================================================================
# 3. CLI Command Tests (4 tests)
# ============================================================================


def test_cli_success_with_issue(tmp_path: Path) -> None:
    """Test CLI generates body with issue reference."""
    runner = CliRunner()
    github = FakeGitHub(pr_diffs={1895: "+new code"})
    executor = FakePromptExecutor(output="Add new feature")
    ctx = DotAgentContext.for_test(
        github=github,
        prompt_executor=executor,
        repo_root=tmp_path,
        cwd=tmp_path,
    )

    result = runner.invoke(
        generate_pr_body_command,
        ["--pr-number", "1895", "--issue-number", "100"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert "## Summary" in output["body"]
    assert "Closes #100" in output["body"]


def test_cli_success_without_issue(tmp_path: Path) -> None:
    """Test CLI generates body without issue reference."""
    runner = CliRunner()
    github = FakeGitHub(pr_diffs={1895: "+new code"})
    executor = FakePromptExecutor(output="Add feature")
    ctx = DotAgentContext.for_test(
        github=github,
        prompt_executor=executor,
        repo_root=tmp_path,
        cwd=tmp_path,
    )

    result = runner.invoke(
        generate_pr_body_command,
        ["--pr-number", "1895"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert "Closes #" not in output["body"]


def test_cli_error_empty_diff(tmp_path: Path) -> None:
    """Test CLI exits with error on empty diff."""
    runner = CliRunner()
    github = FakeGitHub(pr_diffs={123: ""})
    ctx = DotAgentContext.for_test(
        github=github,
        repo_root=tmp_path,
        cwd=tmp_path,
    )

    result = runner.invoke(
        generate_pr_body_command,
        ["--pr-number", "123"],
        obj=ctx,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "empty_diff"


def test_cli_json_output_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure."""
    runner = CliRunner()
    github = FakeGitHub(pr_diffs={999: "+code"})
    executor = FakePromptExecutor(output="Summary")
    ctx = DotAgentContext.for_test(
        github=github,
        prompt_executor=executor,
        repo_root=tmp_path,
        cwd=tmp_path,
    )

    result = runner.invoke(
        generate_pr_body_command,
        ["--pr-number", "999"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "body" in output
    assert isinstance(output["success"], bool)
    assert isinstance(output["body"], str)
