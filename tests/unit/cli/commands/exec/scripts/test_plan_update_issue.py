"""Unit tests for plan-update-issue command."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.plan_update_issue import plan_update_issue
from erk_shared.context.context import ErkContext
from erk_shared.gateway.claude_installation.fake import FakeClaudeInstallation
from erk_shared.gateway.git.fake import FakeGit
from erk_shared.gateway.git.remote_ops.types import PushError
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueComment, IssueInfo
from erk_shared.gateway.github.types import PRDetails
from erk_shared.gateway.time.fake import FakeTime
from erk_shared.plan_store.github import GitHubPlanStore
from erk_shared.plan_store.planned_pr import PlannedPRBackend
from erk_shared.plan_store.planned_pr_lifecycle import IMPL_CONTEXT_DIR
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


def _make_issue(
    number: int,
    title: str,
    body: str,
) -> IssueInfo:
    """Create a test IssueInfo."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{number}",
        labels=["erk-planned-pr", "erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )


def _make_comment(comment_id: int, body: str) -> IssueComment:
    """Create a test IssueComment."""
    return IssueComment(
        body=body,
        url=f"https://github.com/test/repo/issues/1#issuecomment-{comment_id}",
        id=comment_id,
        author="testuser",
    )


def test_plan_update_issue_success() -> None:
    """Test successful plan update."""
    issue = _make_issue(42, "Test Plan [erk-plan]", "metadata body")
    comment = _make_comment(12345, "old plan content")
    fake_gh = FakeGitHubIssues(
        issues={42: issue},
        comments_with_urls={42: [comment]},
    )
    plan_content = """# Updated Plan

- New step 1
- New step 2"""
    fake_store = FakeClaudeInstallation.for_test(plans={"test-plan": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["--plan-number", "42", "--format", "json"],
        obj=ErkContext.for_test(
            github=FakeGitHub(issues_gateway=fake_gh),
            plan_store=GitHubPlanStore(fake_gh),
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_number"] == 42

    assert output["title"] == "[erk-plan] Updated Plan"

    # Verify update_comment was called
    assert len(fake_gh.updated_comments) == 1
    updated_comment_id, updated_body = fake_gh.updated_comments[0]
    assert updated_comment_id == 12345
    assert "New step 1" in updated_body
    assert "New step 2" in updated_body

    # Verify update_issue_title was called
    assert len(fake_gh.updated_titles) == 1
    assert fake_gh.updated_titles[0] == (42, "[erk-plan] Updated Plan")


def test_plan_update_issue_display_format() -> None:
    """Test display output format."""
    issue = _make_issue(99, "My Feature [erk-plan]", "body")
    comment = _make_comment(55555, "plan content")
    fake_gh = FakeGitHubIssues(
        issues={99: issue},
        comments_with_urls={99: [comment]},
    )
    plan_content = """# Display Test

- Step"""
    fake_store = FakeClaudeInstallation.for_test(plans={"display-test": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["--plan-number", "99", "--format", "display"],
        obj=ErkContext.for_test(
            github=FakeGitHub(issues_gateway=fake_gh),
            plan_store=GitHubPlanStore(fake_gh),
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0
    assert "Plan updated on issue #99" in result.output
    assert "Title: [erk-plan] Display Test" in result.output
    assert "URL: " in result.output


def test_plan_update_issue_no_plan_found() -> None:
    """Test error when no plan found."""
    issue = _make_issue(42, "Test [erk-plan]", "body")
    comment = _make_comment(12345, "plan content")
    fake_gh = FakeGitHubIssues(
        issues={42: issue},
        comments_with_urls={42: [comment]},
    )
    # Empty store - no plans
    fake_store = FakeClaudeInstallation.for_test()
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["--plan-number", "42", "--format", "json"],
        obj=ErkContext.for_test(
            github=FakeGitHub(issues_gateway=fake_gh),
            plan_store=GitHubPlanStore(fake_gh),
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No plan found" in output["error"]


def test_plan_update_issue_issue_not_found() -> None:
    """Test error when issue does not exist."""
    # Empty issues dict - no issues
    fake_gh = FakeGitHubIssues()
    plan_content = """# Test

- Step"""
    fake_store = FakeClaudeInstallation.for_test(plans={"test": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["--plan-number", "999", "--format", "json"],
        obj=ErkContext.for_test(
            github=FakeGitHub(issues_gateway=fake_gh),
            plan_store=GitHubPlanStore(fake_gh),
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "999" in output["error"]


def test_plan_update_issue_formats_plan_content() -> None:
    """Test that plan content is properly formatted with metadata block."""
    issue = _make_issue(42, "Test [erk-plan]", "body")
    comment = _make_comment(12345, "old content")
    fake_gh = FakeGitHubIssues(
        issues={42: issue},
        comments_with_urls={42: [comment]},
    )
    plan_content = """# My Plan

- Step 1"""
    fake_store = FakeClaudeInstallation.for_test(plans={"format-test": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["--plan-number", "42"],
        obj=ErkContext.for_test(
            github=FakeGitHub(issues_gateway=fake_gh),
            plan_store=GitHubPlanStore(fake_gh),
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0

    # Verify the updated content is formatted (wrapped in metadata block)
    _, updated_body = fake_gh.updated_comments[0]
    # The format_plan_content_comment wraps in collapsible metadata block
    assert "plan-body" in updated_body or "erk:metadata-block" in updated_body


def test_plan_update_issue_updates_title_from_plan() -> None:
    """Test that issue title is updated from plan H1 heading."""
    issue = _make_issue(42, "[erk-plan] Old Title", "body")
    comment = _make_comment(12345, "old content")
    fake_gh = FakeGitHubIssues(
        issues={42: issue},
        comments_with_urls={42: [comment]},
    )
    plan_content = """# New Feature Name

- Step 1
- Step 2"""
    fake_store = FakeClaudeInstallation.for_test(plans={"title-test": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["--plan-number", "42", "--format", "json"],
        obj=ErkContext.for_test(
            github=FakeGitHub(issues_gateway=fake_gh),
            plan_store=GitHubPlanStore(fake_gh),
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["title"] == "[erk-plan] New Feature Name"

    # Verify update_issue_title was called
    assert len(fake_gh.updated_titles) == 1
    assert fake_gh.updated_titles[0] == (42, "[erk-plan] New Feature Name")


def test_plan_update_issue_learn_plan_gets_learn_tag() -> None:
    """Test that learn plans get [erk-learn] title tag."""
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=42,
        title="[erk-learn] Old Title",
        body="body",
        state="OPEN",
        url="https://github.com/test/repo/issues/42",
        labels=["erk-planned-pr", "erk-learn"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )
    comment = _make_comment(12345, "old content")
    fake_gh = FakeGitHubIssues(
        issues={42: issue},
        comments_with_urls={42: [comment]},
    )
    plan_content = """# Learn Something New

- Insight 1"""
    fake_store = FakeClaudeInstallation.for_test(plans={"learn-test": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["--plan-number", "42", "--format", "json"],
        obj=ErkContext.for_test(
            github=FakeGitHub(issues_gateway=fake_gh),
            plan_store=GitHubPlanStore(fake_gh),
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["title"] == "[erk-learn] Learn Something New"

    assert fake_gh.updated_titles[0] == (42, "[erk-learn] Learn Something New")


def test_plan_update_issue_strips_plan_prefix_from_title() -> None:
    """Test that 'Plan: ' prefix is stripped from extracted title."""
    issue = _make_issue(42, "[erk-plan] Old Title", "body")
    comment = _make_comment(12345, "old content")
    fake_gh = FakeGitHubIssues(
        issues={42: issue},
        comments_with_urls={42: [comment]},
    )
    plan_content = """# Plan: Add Feature X

- Step 1"""
    fake_store = FakeClaudeInstallation.for_test(plans={"prefix-test": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["--plan-number", "42", "--format", "json"],
        obj=ErkContext.for_test(
            github=FakeGitHub(issues_gateway=fake_gh),
            plan_store=GitHubPlanStore(fake_gh),
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["title"] == "[erk-plan] Add Feature X"


def test_plan_update_issue_display_format_shows_new_title() -> None:
    """Test display format shows the updated title."""
    issue = _make_issue(42, "[erk-plan] Old Title", "body")
    comment = _make_comment(12345, "old content")
    fake_gh = FakeGitHubIssues(
        issues={42: issue},
        comments_with_urls={42: [comment]},
    )
    plan_content = """# Updated Feature

- Step 1"""
    fake_store = FakeClaudeInstallation.for_test(plans={"display-title": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["--plan-number", "42", "--format", "display"],
        obj=ErkContext.for_test(
            github=FakeGitHub(issues_gateway=fake_gh),
            plan_store=GitHubPlanStore(fake_gh),
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0
    assert "Title: [erk-plan] Updated Feature" in result.output


# ============================================================================
# Branch push tests (PR-backed plans with PlannedPRBackend)
# ============================================================================


def _make_pr_details(
    number: int,
    title: str,
    *,
    branch_name: str,
) -> PRDetails:
    """Create PRDetails with a plan-header metadata block containing branch_name."""
    from erk_shared.plan_store.planned_pr_lifecycle import (
        DETAILS_CLOSE,
        DETAILS_OPEN,
        PLAN_CONTENT_SEPARATOR,
    )

    metadata_body = format_plan_header_body_for_test(branch_name=branch_name)
    plan_content = "# Old Plan Content"
    details_section = DETAILS_OPEN + plan_content + DETAILS_CLOSE
    pr_body = metadata_body + PLAN_CONTENT_SEPARATOR + details_section

    return PRDetails(
        number=number,
        url=f"https://github.com/test/repo/pull/{number}",
        title=title,
        body=pr_body,
        state="OPEN",
        is_draft=True,
        base_ref_name="master",
        head_ref_name=branch_name,
        is_cross_repository=False,
        mergeable="UNKNOWN",
        merge_state_status="UNKNOWN",
        owner="test-owner",
        repo="test-repo",
        labels=("erk-plan",),
    )


def test_plan_update_pushes_to_branch() -> None:
    """Test that plan update pushes to branch when branch_name is in header_fields."""
    branch_name = "plnd/my-feature-branch"
    pr = _make_pr_details(42, "[erk-plan] Old Title", branch_name=branch_name)
    fake_github = FakeGitHub(pr_details={42: pr})
    fake_git = FakeGit()
    plan_content = """# Updated Plan

- New step 1
- New step 2"""
    fake_store = FakeClaudeInstallation.for_test(plans={"test-plan": plan_content})
    backend = PlannedPRBackend(fake_github, fake_github.issues, time=FakeTime())
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["--plan-number", "42", "--format", "json"],
        obj=ErkContext.for_test(
            github=fake_github,
            git=fake_git,
            plan_store=backend,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["branch_name"] == branch_name
    assert output["branch_updated"] is True

    # Verify commit_files_to_branch was called with correct args
    assert len(fake_git.branch_commits) == 1
    commit = fake_git.branch_commits[0]
    assert commit.branch == branch_name
    assert f"{IMPL_CONTEXT_DIR}/plan.md" in commit.files
    assert "New step 1" in commit.files[f"{IMPL_CONTEXT_DIR}/plan.md"]

    # Verify push_to_remote was called
    assert len(fake_git.pushed_branches) == 1
    push = fake_git.pushed_branches[0]
    assert push.remote == "origin"
    assert push.branch == branch_name
    assert push.set_upstream is False
    assert push.force is False


def test_plan_update_branch_push_failure_still_succeeds() -> None:
    """Test that push failure still reports success (PR body was updated)."""
    branch_name = "plnd/my-feature-branch"
    pr = _make_pr_details(42, "[erk-plan] Old Title", branch_name=branch_name)
    fake_github = FakeGitHub(pr_details={42: pr})
    fake_git = FakeGit(push_to_remote_error=PushError(message="rejected"))
    plan_content = """# Updated Plan

- Step 1"""
    fake_store = FakeClaudeInstallation.for_test(plans={"test-plan": plan_content})
    backend = PlannedPRBackend(fake_github, fake_github.issues, time=FakeTime())
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["--plan-number", "42", "--format", "json"],
        obj=ErkContext.for_test(
            github=fake_github,
            git=fake_git,
            plan_store=backend,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["branch_name"] == branch_name
    assert output["branch_updated"] is False

    # Commit was still made (before push failed)
    assert len(fake_git.branch_commits) == 1


def test_plan_update_no_branch_skips_push() -> None:
    """Test that issue-backed plans (no branch_name) skip branch push entirely."""
    issue = _make_issue(42, "[erk-plan] Old Title", "body")
    comment = _make_comment(12345, "old content")
    fake_gh = FakeGitHubIssues(
        issues={42: issue},
        comments_with_urls={42: [comment]},
    )
    fake_git = FakeGit()
    plan_content = """# Updated Plan

- Step 1"""
    fake_store = FakeClaudeInstallation.for_test(plans={"test-plan": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_update_issue,
        ["--plan-number", "42", "--format", "json"],
        obj=ErkContext.for_test(
            github=FakeGitHub(issues_gateway=fake_gh),
            git=fake_git,
            plan_store=GitHubPlanStore(fake_gh),
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["branch_name"] is None
    assert output["branch_updated"] is False

    # No git operations attempted
    assert len(fake_git.branch_commits) == 0
    assert len(fake_git.pushed_branches) == 0
