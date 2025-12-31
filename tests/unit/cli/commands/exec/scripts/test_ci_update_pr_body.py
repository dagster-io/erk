"""Unit tests for ci_update_pr_body kit CLI command.

Tests the PR body update with AI-generated summary and footer.
Uses FakeGit, FakeGitHub, and FakePromptExecutor for dependency injection.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.ci_update_pr_body import (
    UpdateError,
    UpdateSuccess,
    _build_pr_body,
    _build_prompt,
    _update_pr_body_impl,
)
from erk.cli.commands.exec.scripts.ci_update_pr_body import (
    ci_update_pr_body as ci_update_pr_body_command,
)
from erk_shared.context import ErkContext
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRDetails, PullRequestInfo
from erk_shared.prompt_executor.fake import FakePromptExecutor

# ============================================================================
# 1. Helper Function Tests
# ============================================================================


def test_build_prompt_contains_diff_and_context() -> None:
    """Test that _build_prompt includes diff content and branch context."""
    diff_content = "+added line\n-removed line"
    current_branch = "feature-branch"
    parent_branch = "main"

    prompt = _build_prompt(diff_content, current_branch, parent_branch)

    # Should include diff
    assert "+added line" in prompt
    assert "-removed line" in prompt

    # Should include branch context
    assert "Current branch: feature-branch" in prompt
    assert "Parent branch: main" in prompt


def test_build_pr_body_includes_summary_and_footer() -> None:
    """Test that _build_pr_body includes all required sections."""
    body = _build_pr_body(
        summary="This is the summary",
        pr_number=123,
        issue_number=456,
        run_id=None,
        run_url=None,
    )

    assert "## Summary" in body
    assert "This is the summary" in body
    assert "Closes #456" in body
    assert "erk pr checkout 123" in body


def test_build_pr_body_includes_workflow_link_when_provided() -> None:
    """Test that _build_pr_body includes workflow link when run_id and run_url are provided."""
    body = _build_pr_body(
        summary="Summary",
        pr_number=123,
        issue_number=456,
        run_id="789",
        run_url="https://github.com/owner/repo/actions/runs/789",
    )

    assert "Remotely executed" in body
    assert "Run #789" in body
    assert "https://github.com/owner/repo/actions/runs/789" in body


def test_build_pr_body_omits_workflow_link_when_not_provided() -> None:
    """Test that _build_pr_body omits workflow link when run_id or run_url is None."""
    body = _build_pr_body(
        summary="Summary",
        pr_number=123,
        issue_number=456,
        run_id=None,
        run_url=None,
    )

    assert "Remotely executed" not in body


# ============================================================================
# 2. Implementation Logic Tests
# ============================================================================


def test_impl_success(tmp_path: Path) -> None:
    """Test successful PR body update."""
    # Create FakeGit with current branch
    git = FakeGit(current_branches={tmp_path: "feature-branch"})

    # Create PRDetails for the branch
    pr_details = PRDetails(
        number=123,
        url="https://github.com/owner/repo/pull/123",
        title="Test PR",
        body="Old body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )

    github = FakeGitHub(
        prs={
            "feature-branch": PullRequestInfo(
                number=123,
                state="OPEN",
                url="https://github.com/owner/repo/pull/123",
                is_draft=False,
                title="Test PR",
                checks_passing=True,
                owner="test-owner",
                repo="test-repo",
            )
        },
        pr_details={123: pr_details},
        pr_diffs={123: "+added line\n-removed line"},
    )

    executor = FakePromptExecutor(output="Generated PR summary")

    result = _update_pr_body_impl(
        git, github, executor, tmp_path, issue_number=456, run_id=None, run_url=None
    )

    assert isinstance(result, UpdateSuccess)
    assert result.success is True
    assert result.pr_number == 123


def test_impl_no_pr_for_branch(tmp_path: Path) -> None:
    """Test error when no PR exists for the current branch."""
    git = FakeGit(current_branches={tmp_path: "feature-branch"})
    # No PR configured for this branch
    github = FakeGitHub()
    executor = FakePromptExecutor()

    result = _update_pr_body_impl(
        git, github, executor, tmp_path, issue_number=456, run_id=None, run_url=None
    )

    assert isinstance(result, UpdateError)
    assert result.success is False
    assert result.error == "pr_not_found"


def test_impl_empty_diff(tmp_path: Path) -> None:
    """Test error when PR diff is empty."""
    git = FakeGit(current_branches={tmp_path: "feature-branch"})

    pr_details = PRDetails(
        number=123,
        url="https://github.com/owner/repo/pull/123",
        title="Test PR",
        body="Old body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )

    github = FakeGitHub(
        prs={
            "feature-branch": PullRequestInfo(
                number=123,
                state="OPEN",
                url="https://github.com/owner/repo/pull/123",
                is_draft=False,
                title="Test PR",
                checks_passing=True,
                owner="test-owner",
                repo="test-repo",
            )
        },
        pr_details={123: pr_details},
        pr_diffs={123: ""},  # Empty diff
    )

    executor = FakePromptExecutor()

    result = _update_pr_body_impl(
        git, github, executor, tmp_path, issue_number=456, run_id=None, run_url=None
    )

    assert isinstance(result, UpdateError)
    assert result.success is False
    assert result.error == "empty_diff"


def test_impl_claude_failure(tmp_path: Path) -> None:
    """Test error when Claude execution fails."""
    git = FakeGit(current_branches={tmp_path: "feature-branch"})

    pr_details = PRDetails(
        number=123,
        url="https://github.com/owner/repo/pull/123",
        title="Test PR",
        body="Old body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )

    github = FakeGitHub(
        prs={
            "feature-branch": PullRequestInfo(
                number=123,
                state="OPEN",
                url="https://github.com/owner/repo/pull/123",
                is_draft=False,
                title="Test PR",
                checks_passing=True,
                owner="test-owner",
                repo="test-repo",
            )
        },
        pr_details={123: pr_details},
        pr_diffs={123: "+some diff"},
    )

    executor = FakePromptExecutor(should_fail=True, error="API error")

    result = _update_pr_body_impl(
        git, github, executor, tmp_path, issue_number=456, run_id=None, run_url=None
    )

    assert isinstance(result, UpdateError)
    assert result.success is False
    assert result.error == "claude_failed"
    assert "API error" in result.message


def test_impl_claude_empty_output(tmp_path: Path) -> None:
    """Test error when Claude returns success but with empty output."""
    git = FakeGit(current_branches={tmp_path: "feature-branch"})

    pr_details = PRDetails(
        number=123,
        url="https://github.com/owner/repo/pull/123",
        title="Test PR",
        body="Old body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )

    github = FakeGitHub(
        prs={
            "feature-branch": PullRequestInfo(
                number=123,
                state="OPEN",
                url="https://github.com/owner/repo/pull/123",
                is_draft=False,
                title="Test PR",
                checks_passing=True,
                owner="test-owner",
                repo="test-repo",
            )
        },
        pr_details={123: pr_details},
        pr_diffs={123: "+some diff"},
    )

    executor = FakePromptExecutor(output="")

    result = _update_pr_body_impl(
        git, github, executor, tmp_path, issue_number=456, run_id=None, run_url=None
    )

    assert isinstance(result, UpdateError)
    assert result.success is False
    assert result.error == "claude_failed"
    assert "empty output" in result.message.lower()


# ============================================================================
# 3. CLI Command Tests
# ============================================================================


def test_cli_success(tmp_path: Path) -> None:
    """Test CLI command when PR body is updated successfully."""
    git = FakeGit(current_branches={tmp_path: "feature-branch"})

    pr_details = PRDetails(
        number=123,
        url="https://github.com/owner/repo/pull/123",
        title="Test PR",
        body="Old body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )

    github = FakeGitHub(
        prs={
            "feature-branch": PullRequestInfo(
                number=123,
                state="OPEN",
                url="https://github.com/owner/repo/pull/123",
                is_draft=False,
                title="Test PR",
                checks_passing=True,
                owner="test-owner",
                repo="test-repo",
            )
        },
        pr_details={123: pr_details},
        pr_diffs={123: "+added line"},
    )

    executor = FakePromptExecutor(output="Generated summary")

    ctx = ErkContext.for_test(
        git=git, github=github, prompt_executor=executor, repo_root=tmp_path, cwd=tmp_path
    )

    runner = CliRunner()
    result = runner.invoke(
        ci_update_pr_body_command,
        ["--issue-number", "456"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 123


def test_cli_with_workflow_run(tmp_path: Path) -> None:
    """Test CLI command with workflow run info."""
    git = FakeGit(current_branches={tmp_path: "feature-branch"})

    pr_details = PRDetails(
        number=123,
        url="https://github.com/owner/repo/pull/123",
        title="Test PR",
        body="Old body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )

    github = FakeGitHub(
        prs={
            "feature-branch": PullRequestInfo(
                number=123,
                state="OPEN",
                url="https://github.com/owner/repo/pull/123",
                is_draft=False,
                title="Test PR",
                checks_passing=True,
                owner="test-owner",
                repo="test-repo",
            )
        },
        pr_details={123: pr_details},
        pr_diffs={123: "+added line"},
    )

    executor = FakePromptExecutor(output="Generated summary")

    ctx = ErkContext.for_test(
        git=git, github=github, prompt_executor=executor, repo_root=tmp_path, cwd=tmp_path
    )

    runner = CliRunner()
    result = runner.invoke(
        ci_update_pr_body_command,
        [
            "--issue-number",
            "456",
            "--run-id",
            "789",
            "--run-url",
            "https://github.com/owner/repo/actions/runs/789",
        ],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True


def test_cli_error_exit_code(tmp_path: Path) -> None:
    """Test CLI command exits with error code on failure."""
    git = FakeGit(current_branches={tmp_path: "feature-branch"})
    # No PR configured
    github = FakeGitHub()
    executor = FakePromptExecutor()

    ctx = ErkContext.for_test(
        git=git, github=github, prompt_executor=executor, repo_root=tmp_path, cwd=tmp_path
    )

    runner = CliRunner()
    result = runner.invoke(
        ci_update_pr_body_command,
        ["--issue-number", "456"],
        obj=ctx,
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "pr_not_found"


def test_cli_requires_issue_number() -> None:
    """Test that --issue-number is required."""
    runner = CliRunner()

    result = runner.invoke(ci_update_pr_body_command, [])

    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()


def test_cli_json_output_structure_success(tmp_path: Path) -> None:
    """Test that JSON output has expected structure on success."""
    git = FakeGit(current_branches={tmp_path: "feature-branch"})

    pr_details = PRDetails(
        number=123,
        url="https://github.com/owner/repo/pull/123",
        title="Test PR",
        body="Old body",
        state="OPEN",
        is_draft=False,
        base_ref_name="main",
        head_ref_name="feature-branch",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
    )

    github = FakeGitHub(
        prs={
            "feature-branch": PullRequestInfo(
                number=123,
                state="OPEN",
                url="https://github.com/owner/repo/pull/123",
                is_draft=False,
                title="Test PR",
                checks_passing=True,
                owner="test-owner",
                repo="test-repo",
            )
        },
        pr_details={123: pr_details},
        pr_diffs={123: "+added line"},
    )

    executor = FakePromptExecutor(output="Summary")

    ctx = ErkContext.for_test(
        git=git, github=github, prompt_executor=executor, repo_root=tmp_path, cwd=tmp_path
    )

    runner = CliRunner()
    result = runner.invoke(
        ci_update_pr_body_command,
        ["--issue-number", "456"],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "pr_number" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["pr_number"], int)


def test_cli_json_output_structure_error(tmp_path: Path) -> None:
    """Test that JSON output has expected structure on error."""
    git = FakeGit(current_branches={tmp_path: "feature-branch"})
    github = FakeGitHub()
    executor = FakePromptExecutor()

    ctx = ErkContext.for_test(
        git=git, github=github, prompt_executor=executor, repo_root=tmp_path, cwd=tmp_path
    )

    runner = CliRunner()
    result = runner.invoke(
        ci_update_pr_body_command,
        ["--issue-number", "456"],
        obj=ctx,
    )

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
