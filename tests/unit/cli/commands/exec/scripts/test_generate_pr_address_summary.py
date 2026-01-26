"""Tests for generate-pr-address-summary exec command.

Tests the enhanced PR comment generation for pr-address workflow.

Uses fake-driven testing with injected dependencies via ErkContext.
"""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.generate_pr_address_summary import (
    PR_ADDRESS_MARKER,
    _build_failure_comment,
    _build_no_changes_comment,
    _build_success_comment,
    _build_summary_prompt,
    generate_pr_address_summary,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.prompt_executor.fake import FakePromptExecutor


def test_build_summary_prompt_contains_diff() -> None:
    """Test that _build_summary_prompt includes diff content."""
    diff_content = "+added line\n-removed line"

    prompt = _build_summary_prompt(diff_content)

    assert "+added line" in prompt
    assert "-removed line" in prompt
    assert "Summarize" in prompt


def test_build_success_comment_includes_all_sections() -> None:
    """Test that success comment includes all required sections."""
    comment = _build_success_comment(
        pr_number=123,
        summary="Fixed the authentication flow.",
        model_name="claude-sonnet-4-5",
        run_url="https://github.com/owner/repo/actions/runs/789",
        commit_count=2,
    )

    # Check marker
    assert PR_ADDRESS_MARKER in comment

    # Check sections
    assert "## PR Review Comments Addressed" in comment
    assert "erk pr address-remote 123" in comment
    assert "### What is this?" in comment
    assert "Erk" in comment
    assert "### Changes Made" in comment
    assert "Fixed the authentication flow." in comment
    assert "### Details" in comment
    assert "claude-sonnet-4-5" in comment
    assert "View details" in comment
    assert "Commits added:** 2" in comment


def test_build_no_changes_comment_includes_explanation() -> None:
    """Test that no-changes comment explains the situation."""
    comment = _build_no_changes_comment(
        pr_number=123,
        model_name="claude-sonnet-4-5",
        run_url="https://github.com/owner/repo/actions/runs/789",
    )

    # Check marker
    assert PR_ADDRESS_MARKER in comment

    # Check sections
    assert "## PR Review Comments Addressed" in comment
    assert "No changes were needed" in comment
    assert "already addressed" in comment
    assert "claude-sonnet-4-5" in comment


def test_build_failure_comment_includes_error_info() -> None:
    """Test that failure comment includes workflow link."""
    comment = _build_failure_comment(
        pr_number=123,
        run_url="https://github.com/owner/repo/actions/runs/789",
    )

    # Check marker
    assert PR_ADDRESS_MARKER in comment

    # Check sections
    assert "Failed" in comment
    assert "View workflow logs" in comment
    assert "https://github.com/owner/repo/actions/runs/789" in comment


def test_generate_pr_address_summary_requires_options() -> None:
    """Test that required options are enforced."""
    runner = CliRunner()

    result = runner.invoke(generate_pr_address_summary, [])

    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()


def test_generate_pr_address_summary_failure_status(tmp_path: Path) -> None:
    """Test that failure status returns failure comment without needing diff."""
    fake_git = FakeGit(repository_roots={tmp_path: tmp_path})

    test_ctx = ErkContext.for_test(cwd=tmp_path, repo_root=tmp_path, git=fake_git)

    runner = CliRunner()
    result = runner.invoke(
        generate_pr_address_summary,
        [
            "--pr-number",
            "123",
            "--pre-head",
            "abc1234",
            "--run-url",
            "https://example.com/run",
            "--job-status",
            "failure",
        ],
        obj=test_ctx,
    )

    assert result.exit_code == 0
    assert PR_ADDRESS_MARKER in result.output
    assert "Failed" in result.output


def test_generate_pr_address_summary_no_changes(tmp_path: Path) -> None:
    """Test that empty diff produces no-changes comment."""
    fake_git = FakeGit(repository_roots={tmp_path: tmp_path})

    test_ctx = ErkContext.for_test(cwd=tmp_path, repo_root=tmp_path, git=fake_git)

    runner = CliRunner()
    # Provide empty stdin
    result = runner.invoke(
        generate_pr_address_summary,
        [
            "--pr-number",
            "123",
            "--pre-head",
            "abc1234",
            "--run-url",
            "https://example.com/run",
            "--job-status",
            "success",
        ],
        obj=test_ctx,
        input="",  # Empty diff
    )

    assert result.exit_code == 0
    assert PR_ADDRESS_MARKER in result.output
    assert "No changes were needed" in result.output


def test_generate_pr_address_summary_with_changes(tmp_path: Path) -> None:
    """Test that diff content triggers Claude summary generation."""
    fake_git = FakeGit(
        repository_roots={tmp_path: tmp_path},
        commits_ahead={(tmp_path, "abc1234"): 2},
    )
    fake_executor = FakePromptExecutor(output="Fixed authentication logic and updated tests.")

    test_ctx = ErkContext.for_test(
        cwd=tmp_path,
        repo_root=tmp_path,
        git=fake_git,
        prompt_executor=fake_executor,
    )

    runner = CliRunner()
    result = runner.invoke(
        generate_pr_address_summary,
        [
            "--pr-number",
            "123",
            "--pre-head",
            "abc1234",
            "--model-name",
            "claude-sonnet-4-5",
            "--run-url",
            "https://example.com/run",
            "--job-status",
            "success",
        ],
        obj=test_ctx,
        input="+added line\n-removed line",  # Non-empty diff
    )

    assert result.exit_code == 0
    assert PR_ADDRESS_MARKER in result.output
    assert "Fixed authentication logic and updated tests." in result.output
    assert "Commits added:** 2" in result.output

    # Verify Claude was called with haiku model
    assert len(fake_executor.prompt_calls) == 1
    assert fake_executor.prompt_calls[0].model == "haiku"


def test_generate_pr_address_summary_claude_failure(tmp_path: Path) -> None:
    """Test that Claude execution failure exits with error."""
    fake_git = FakeGit(repository_roots={tmp_path: tmp_path})
    fake_executor = FakePromptExecutor(should_fail=True, error="API error")

    test_ctx = ErkContext.for_test(
        cwd=tmp_path,
        repo_root=tmp_path,
        git=fake_git,
        prompt_executor=fake_executor,
    )

    runner = CliRunner()
    result = runner.invoke(
        generate_pr_address_summary,
        [
            "--pr-number",
            "123",
            "--pre-head",
            "abc1234",
            "--run-url",
            "https://example.com/run",
            "--job-status",
            "success",
        ],
        obj=test_ctx,
        input="+added line",  # Non-empty diff to trigger Claude
    )

    assert result.exit_code == 1
    assert "Claude execution failed" in result.output


def test_generate_pr_address_summary_empty_claude_output(tmp_path: Path) -> None:
    """Test that empty Claude output uses default message."""
    fake_git = FakeGit(repository_roots={tmp_path: tmp_path})
    fake_executor = FakePromptExecutor(output="")  # Empty output

    test_ctx = ErkContext.for_test(
        cwd=tmp_path,
        repo_root=tmp_path,
        git=fake_git,
        prompt_executor=fake_executor,
    )

    runner = CliRunner()
    result = runner.invoke(
        generate_pr_address_summary,
        [
            "--pr-number",
            "123",
            "--pre-head",
            "abc1234",
            "--run-url",
            "https://example.com/run",
            "--job-status",
            "success",
        ],
        obj=test_ctx,
        input="+added line",  # Non-empty diff
    )

    assert result.exit_code == 0
    # Should fall back to default message
    assert "Changes were made to address review comments." in result.output
