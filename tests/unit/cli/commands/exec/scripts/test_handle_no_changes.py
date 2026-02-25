"""Unit tests for handle_no_changes exec CLI command.

Tests the no-changes scenario handling for plan-implement workflow.
Uses FakeGitHub for dependency injection.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.handle_no_changes import (
    HandleNoChangesError,
    HandleNoChangesSuccess,
    _build_issue_comment,
    _build_no_changes_title,
    _build_pr_body,
)
from erk.cli.commands.exec.scripts.handle_no_changes import (
    handle_no_changes as handle_no_changes_command,
)
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.metadata.plan_header import format_plan_header_body
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.planned_pr import PlannedPRBackend


def _make_plan_header_body() -> str:
    """Create a plan-header metadata body for test PRs."""
    return format_plan_header_body(
        created_at="2024-01-15T10:30:00Z",
        created_by="test-user",
        worktree_name=None,
        branch_name=None,
        plan_comment_id=None,
        last_dispatched_run_id=None,
        last_dispatched_node_id=None,
        last_dispatched_at=None,
        last_local_impl_at=None,
        last_local_impl_event=None,
        last_local_impl_session=None,
        last_local_impl_user=None,
        last_remote_impl_at=None,
        last_remote_impl_run_id=None,
        last_remote_impl_session_id=None,
        source_repo=None,
        objective_issue=None,
        created_from_session=None,
        created_from_workflow_run_url=None,
        last_learn_session=None,
        last_learn_at=None,
        learn_status=None,
        learn_plan_issue=None,
        learn_plan_pr=None,
        learned_from_issue=None,
        lifecycle_stage=None,
    )


def _create_github_with_plan_pr(
    plan_id: int,
) -> tuple[FakeGitHub, FakeGitHubIssues, PlannedPRBackend]:
    """Create FakeGitHub with a draft PR configured as a plan for PlannedPRBackend.

    Returns:
        Tuple of (FakeGitHub, FakeGitHubIssues, PlannedPRBackend).
    """
    body = _make_plan_header_body()
    issues_gateway = FakeGitHubIssues()
    fake_github = FakeGitHub(
        issues_gateway=issues_gateway,
        pr_details={
            plan_id: PRDetails(
                number=plan_id,
                url=f"https://github.com/test-owner/test-repo/pull/{plan_id}",
                title="Test Plan",
                body=body,
                state="OPEN",
                is_draft=True,
                base_ref_name="master",
                head_ref_name=f"plan-test-{plan_id}",
                is_cross_repository=False,
                mergeable="MERGEABLE",
                merge_state_status="CLEAN",
                owner="test-owner",
                repo="test-repo",
            ),
        },
    )
    backend = PlannedPRBackend(fake_github, issues_gateway, time=FakeTime())
    return fake_github, issues_gateway, backend


# ============================================================================
# 1. Helper Function Tests
# ============================================================================


def test_build_pr_body_includes_all_sections() -> None:
    """Test that _build_pr_body includes all required sections."""
    body = _build_pr_body(
        plan_id=456,
        behind_count=5,
        base_branch="master",
        recent_commits="abc1234 Fix bug\ndef5678 Add feature",
        run_url="https://github.com/owner/repo/actions/runs/789",
    )

    assert "## No Code Changes" in body
    assert "Implementation completed but produced no code changes" in body
    assert "### Diagnosis" in body
    assert "Duplicate plan" in body
    assert "5 commits" in body
    assert "master" in body
    assert "Recent commits" in body
    assert "abc1234 Fix bug" in body
    assert "def5678 Add feature" in body
    assert "### Next Steps" in body
    assert "Close this PR" in body
    assert "https://github.com/owner/repo/actions/runs/789" in body


def test_build_pr_body_without_recent_commits() -> None:
    """Test that _build_pr_body works without recent commits."""
    body = _build_pr_body(
        plan_id=456,
        behind_count=0,
        base_branch="main",
        recent_commits=None,
        run_url=None,
    )

    assert "## No Code Changes" in body
    assert "### Diagnosis" in body
    assert "Close this PR" in body
    # Should not include commits section when behind_count is 0
    assert "commits** behind" not in body
    # Should not include run URL
    assert "View workflow run" not in body


def test_build_pr_body_with_empty_recent_commits() -> None:
    """Test that _build_pr_body handles empty recent commits string."""
    body = _build_pr_body(
        plan_id=123,
        behind_count=3,
        base_branch="master",
        recent_commits="",
        run_url=None,
    )

    assert "## No Code Changes" in body
    assert "3 commits" in body
    # Should not include recent commits section with empty string
    assert "Recent commits" not in body


def test_build_issue_comment() -> None:
    """Test that _build_issue_comment returns no-changes message."""
    comment = _build_issue_comment(pr_number=123)

    assert "no code changes" in comment.lower()
    assert "close this pr" in comment.lower()


def test_build_no_changes_title() -> None:
    """Test that _build_no_changes_title formats correctly."""
    title = _build_no_changes_title(
        plan_id=5799, original_title="Fix RealGraphite Cache Invalidation"
    )

    assert title == "[no-changes] #5799 Impl Attempt: Fix RealGraphite Cache Invalidation"


def test_build_no_changes_title_preserves_original() -> None:
    """Test that _build_no_changes_title preserves the original title exactly."""
    title = _build_no_changes_title(plan_id=123, original_title="Add [feature] flag support")

    assert title == "[no-changes] #123 Impl Attempt: Add [feature] flag support"


# ============================================================================
# 2. CLI Command Tests
# ============================================================================


def test_cli_success(tmp_path: Path) -> None:
    """Test CLI command succeeds with valid inputs."""
    github, fake_gh_issues, backend = _create_github_with_plan_pr(456)

    ctx = ErkContext.for_test(github=github, plan_store=backend, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--plan-id",
            "456",
            "--behind-count",
            "5",
            "--base-branch",
            "master",
            "--original-title",
            "Fix Some Bug",
            "--recent-commits",
            "abc1234 Fix bug\ndef5678 Add feature",
            "--run-url",
            "https://github.com/owner/repo/actions/runs/789",
        ],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 123
    assert output["plan_id"] == 456


def test_cli_success_minimal_options(tmp_path: Path) -> None:
    """Test CLI command succeeds with only required options."""
    github, fake_gh_issues, backend = _create_github_with_plan_pr(456)

    ctx = ErkContext.for_test(github=github, plan_store=backend, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--plan-id",
            "456",
            "--behind-count",
            "0",
            "--base-branch",
            "main",
            "--original-title",
            "Simple Fix",
        ],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True


def test_cli_updates_pr_title_and_body(tmp_path: Path) -> None:
    """Test that CLI command updates PR title and body."""
    github, fake_gh_issues, backend = _create_github_with_plan_pr(456)

    ctx = ErkContext.for_test(github=github, plan_store=backend, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--plan-id",
            "456",
            "--behind-count",
            "5",
            "--base-branch",
            "master",
            "--original-title",
            "Fix Cache Issue",
        ],
        obj=ctx,
    )

    # Verify PR title was updated
    assert len(github.updated_pr_titles) == 1
    pr_number, title = github.updated_pr_titles[0]
    assert pr_number == 123
    assert title == "[no-changes] #456 Impl Attempt: Fix Cache Issue"

    # Verify PR body was updated for the impl PR
    # PlannedPRBackend.update_metadata also updates the plan PR body
    no_changes_bodies = [(n, b) for n, b in github.updated_pr_bodies if n == 123]
    assert len(no_changes_bodies) == 1
    pr_number, body = no_changes_bodies[0]
    assert "No Code Changes" in body
    assert "Close this PR" in body


def test_cli_adds_label_to_pr(tmp_path: Path) -> None:
    """Test that CLI command adds no-changes label to PR."""
    github, fake_gh_issues, backend = _create_github_with_plan_pr(456)

    ctx = ErkContext.for_test(github=github, plan_store=backend, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--plan-id",
            "456",
            "--behind-count",
            "0",
            "--base-branch",
            "main",
            "--original-title",
            "Some Feature",
        ],
        obj=ctx,
    )

    # Verify label was added (added_labels is list of (pr_number, label) tuples)
    assert len(github.added_labels) == 1
    pr_number, label = github.added_labels[0]
    assert pr_number == 123
    assert label == "no-changes"


def test_cli_adds_comment_to_issue(tmp_path: Path) -> None:
    """Test that CLI command adds comment to plan issue."""
    github, fake_gh_issues, backend = _create_github_with_plan_pr(456)

    ctx = ErkContext.for_test(github=github, plan_store=backend, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--plan-id",
            "456",
            "--behind-count",
            "0",
            "--base-branch",
            "main",
            "--original-title",
            "Some Feature",
        ],
        obj=ctx,
    )

    # Verify comment was added to plan PR via PlannedPRBackend
    # _pr_comments is list of (pr_number, body) tuples
    assert len(github.pr_comments) == 1
    pr_number, body = github.pr_comments[0]
    assert pr_number == 456
    assert "no code changes" in body.lower()


def test_cli_requires_pr_number() -> None:
    """Test that --pr-number is required."""
    runner = CliRunner()

    result = runner.invoke(
        handle_no_changes_command,
        [
            "--plan-id",
            "456",
            "--behind-count",
            "0",
            "--base-branch",
            "main",
        ],
    )

    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()


def test_cli_requires_plan_id() -> None:
    """Test that --plan-id is required."""
    runner = CliRunner()

    result = runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--behind-count",
            "0",
            "--base-branch",
            "main",
        ],
    )

    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()


def test_cli_requires_behind_count() -> None:
    """Test that --behind-count is required."""
    runner = CliRunner()

    result = runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--plan-id",
            "456",
            "--base-branch",
            "main",
        ],
    )

    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()


def test_cli_requires_base_branch() -> None:
    """Test that --base-branch is required."""
    runner = CliRunner()

    result = runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--plan-id",
            "456",
            "--behind-count",
            "0",
            "--original-title",
            "Some Title",
        ],
    )

    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()


def test_cli_requires_original_title() -> None:
    """Test that --original-title is required."""
    runner = CliRunner()

    result = runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--plan-id",
            "456",
            "--behind-count",
            "0",
            "--base-branch",
            "main",
        ],
    )

    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()


def test_cli_json_output_structure_success(tmp_path: Path) -> None:
    """Test that JSON output has expected structure on success."""
    github, fake_gh_issues, backend = _create_github_with_plan_pr(456)

    ctx = ErkContext.for_test(github=github, plan_store=backend, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--plan-id",
            "456",
            "--behind-count",
            "0",
            "--base-branch",
            "main",
            "--original-title",
            "Some Feature",
        ],
        obj=ctx,
    )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "pr_number" in output
    assert "plan_id" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["pr_number"], int)
    assert isinstance(output["plan_id"], int)


def test_cli_exits_with_code_0_on_success(tmp_path: Path) -> None:
    """Test that CLI exits with code 0 on success (workflow succeeds)."""
    github, fake_gh_issues, backend = _create_github_with_plan_pr(456)

    ctx = ErkContext.for_test(github=github, plan_store=backend, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        handle_no_changes_command,
        [
            "--pr-number",
            "123",
            "--plan-id",
            "456",
            "--behind-count",
            "5",
            "--base-branch",
            "master",
            "--original-title",
            "Some Feature",
        ],
        obj=ctx,
    )

    # Critical: exit code 0 means workflow succeeds
    assert result.exit_code == 0


# ============================================================================
# 3. Dataclass Tests
# ============================================================================


def test_success_dataclass_frozen() -> None:
    """Test that HandleNoChangesSuccess is immutable."""
    success = HandleNoChangesSuccess(success=True, pr_number=123, plan_id=456)
    assert success.success is True
    assert success.pr_number == 123
    assert success.plan_id == 456


def test_error_dataclass_frozen() -> None:
    """Test that HandleNoChangesError is immutable."""
    error = HandleNoChangesError(
        success=False, error="github-api-failed", message="Failed to update PR"
    )
    assert error.success is False
    assert error.error == "github-api-failed"
    assert error.message == "Failed to update PR"
