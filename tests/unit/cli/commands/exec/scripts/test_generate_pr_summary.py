"""Tests for generate-pr-summary kit CLI command.

Tests the PR summary generation from PR diff using Claude.

Uses fake-driven testing with injected dependencies via DotAgentContext.
"""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.generate_pr_summary import (
    _build_prompt,
    generate_pr_summary,
)
from erk_shared.context import ErkContext


def test_build_prompt_contains_diff_and_context(tmp_path: Path) -> None:
    """Test that _build_prompt includes diff content and branch context."""
    diff_content = "+added line\n-removed line"
    current_branch = "feature-branch"
    parent_branch = "main"

    prompt = _build_prompt(diff_content, current_branch, parent_branch, tmp_path)

    # Should include diff
    assert "+added line" in prompt
    assert "-removed line" in prompt

    # Should include branch context
    assert "Current branch: feature-branch" in prompt
    assert "Parent branch: main" in prompt

    # Should NOT include commit messages section
    assert "Developer's Commit Messages" not in prompt
    assert "commit messages were written" not in prompt


def test_build_prompt_uses_commit_message_system_prompt(tmp_path: Path) -> None:
    """Test that _build_prompt uses the shared commit message prompt."""
    prompt = _build_prompt("diff", "branch", "main", tmp_path)

    # Should include the system prompt content
    assert "commit message generator" in prompt.lower()
    # Key parts of COMMIT_MESSAGE_SYSTEM_PROMPT should be present
    assert "Analyze the provided git diff" in prompt


def test_generate_pr_summary_requires_pr_number() -> None:
    """Test that --pr-number is required."""
    runner = CliRunner()

    result = runner.invoke(generate_pr_summary, [])

    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()


def test_generate_pr_summary_exits_on_context_not_initialized() -> None:
    """Test that command exits when context is not initialized."""
    runner = CliRunner()

    # Invoke without context setup
    result = runner.invoke(generate_pr_summary, ["--pr-number", "123"])

    assert result.exit_code == 1
    assert "Context not initialized" in result.output


def test_generate_pr_summary_exits_on_empty_diff() -> None:
    """Test that command exits when PR diff is empty."""
    from erk_shared.github.fake import FakeGitHub

    # Create fake GitHub that returns empty diff
    fake_github = FakeGitHub(pr_diffs={123: ""})

    test_ctx = ErkContext.for_test(github=fake_github)

    runner = CliRunner()
    result = runner.invoke(
        generate_pr_summary,
        ["--pr-number", "123"],
        obj=test_ctx,
    )

    assert result.exit_code == 1
    assert "empty" in result.output.lower()


def test_generate_pr_summary_exits_on_whitespace_only_diff() -> None:
    """Test that command exits when PR diff is whitespace only."""
    from erk_shared.github.fake import FakeGitHub

    # Create fake GitHub that returns whitespace-only diff
    fake_github = FakeGitHub(pr_diffs={123: "   \n\t\n  "})

    test_ctx = ErkContext.for_test(github=fake_github)

    runner = CliRunner()
    result = runner.invoke(
        generate_pr_summary,
        ["--pr-number", "123"],
        obj=test_ctx,
    )

    assert result.exit_code == 1
    assert "empty" in result.output.lower()


def test_generate_pr_summary_truncates_large_diff() -> None:
    """Test that large diffs are truncated with warning."""
    from erk_shared.gateway.gt.prompts import MAX_DIFF_CHARS
    from erk_shared.github.fake import FakeGitHub
    from erk_shared.prompt_executor.fake import FakePromptExecutor

    # Create fake GitHub with very large diff
    large_diff = "+" + "x" * (MAX_DIFF_CHARS + 1000)
    fake_github = FakeGitHub(pr_diffs={123: large_diff})

    # Use FakePromptExecutor to avoid actual Claude CLI call
    fake_executor = FakePromptExecutor(output="Summary output")

    test_ctx = ErkContext.for_test(
        github=fake_github,
        prompt_executor=fake_executor,
    )

    runner = CliRunner()
    result = runner.invoke(
        generate_pr_summary,
        ["--pr-number", "123"],
        obj=test_ctx,
    )

    # Should warn about truncation
    assert "truncated" in result.output.lower()
