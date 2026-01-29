"""Tests for review PR cleanup helper."""

from datetime import UTC, datetime
from pathlib import Path

from erk.cli.commands.review_pr_cleanup import cleanup_review_pr
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo


def _make_plan_header_body(
    *,
    review_pr: int | None,
) -> str:
    """Create a test issue body with plan-header metadata block including review_pr."""
    review_pr_line = f"review_pr: {review_pr}" if review_pr is not None else "review_pr: null"

    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2025-11-25T14:37:43.513418+00:00'
created_by: testuser
plan_comment_id: null
{review_pr_line}
last_dispatched_run_id: null
last_dispatched_at: null

```

</details>
<!-- /erk:metadata-block:plan-header -->

## Plan Content

Some plan body text."""


def _make_issue_info(
    number: int,
    body: str,
) -> IssueInfo:
    """Create test IssueInfo with given number and body."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=f"Test Plan #{number}",
        body=body,
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )


REPO_ROOT = Path("/fake/repo")


def test_cleanup_review_pr_closes_and_comments() -> None:
    """Happy path: comment added, PR closed, metadata cleared."""
    body = _make_plan_header_body(review_pr=99)
    issue = _make_issue_info(42, body)
    review_pr_issue = _make_issue_info(99, "Review PR body")
    fake_issues = FakeGitHubIssues(issues={42: issue, 99: review_pr_issue})
    fake_github = FakeGitHub()

    ctx = ErkContext.for_test(
        github_issues=fake_issues,
        github=fake_github,
        repo_root=REPO_ROOT,
    )

    result = cleanup_review_pr(
        ctx,
        repo_root=REPO_ROOT,
        issue_number=42,
        reason="the plan (issue #42) was closed",
    )

    assert result == 99
    # Comment was added to the review PR
    assert any(
        num == 99 and "automatically closed" in comment_body
        for num, comment_body, _ in fake_issues.added_comments
    )
    # PR was closed
    assert 99 in fake_github.closed_prs
    # Metadata was updated (review_pr cleared)
    updated_issue = fake_issues.get_issue(REPO_ROOT, 42)
    assert "review_pr: null" in updated_issue.body


def test_cleanup_review_pr_no_review_pr() -> None:
    """review_pr is None - no-op."""
    body = _make_plan_header_body(review_pr=None)
    issue = _make_issue_info(42, body)
    fake_issues = FakeGitHubIssues(issues={42: issue})
    fake_github = FakeGitHub()

    ctx = ErkContext.for_test(
        github_issues=fake_issues,
        github=fake_github,
        repo_root=REPO_ROOT,
    )

    result = cleanup_review_pr(
        ctx,
        repo_root=REPO_ROOT,
        issue_number=42,
        reason="test",
    )

    assert result is None
    assert fake_github.closed_prs == []
    assert fake_issues.added_comments == []


def test_cleanup_review_pr_no_plan_header() -> None:
    """No plan-header block - no-op."""
    body = "Just a regular issue body with no metadata block."
    issue = _make_issue_info(42, body)
    fake_issues = FakeGitHubIssues(issues={42: issue})
    fake_github = FakeGitHub()

    ctx = ErkContext.for_test(
        github_issues=fake_issues,
        github=fake_github,
        repo_root=REPO_ROOT,
    )

    result = cleanup_review_pr(
        ctx,
        repo_root=REPO_ROOT,
        issue_number=42,
        reason="test",
    )

    assert result is None
    assert fake_github.closed_prs == []


def test_cleanup_review_pr_issue_not_found() -> None:
    """Issue doesn't exist - no-op."""
    fake_issues = FakeGitHubIssues(issues={})
    fake_github = FakeGitHub()

    ctx = ErkContext.for_test(
        github_issues=fake_issues,
        github=fake_github,
        repo_root=REPO_ROOT,
    )

    result = cleanup_review_pr(
        ctx,
        repo_root=REPO_ROOT,
        issue_number=999,
        reason="test",
    )

    assert result is None
    assert fake_github.closed_prs == []


def test_cleanup_review_pr_close_failure_preserves_metadata() -> None:
    """close_pr fails - metadata NOT cleared."""
    body = _make_plan_header_body(review_pr=99)
    issue = _make_issue_info(42, body)
    review_pr_issue = _make_issue_info(99, "Review PR body")
    fake_issues = FakeGitHubIssues(issues={42: issue, 99: review_pr_issue})

    # Create a FakeGitHub that raises on close_pr
    fake_github = FakeGitHub()

    def failing_close(repo_root: Path, pr_number: int) -> None:
        raise RuntimeError("Failed to close PR")

    fake_github.close_pr = failing_close  # type: ignore[method-assign]

    ctx = ErkContext.for_test(
        github_issues=fake_issues,
        github=fake_github,
        repo_root=REPO_ROOT,
    )

    result = cleanup_review_pr(
        ctx,
        repo_root=REPO_ROOT,
        issue_number=42,
        reason="test",
    )

    assert result is None
    # Metadata should NOT have been cleared since close failed
    unchanged_issue = fake_issues.get_issue(REPO_ROOT, 42)
    assert "review_pr: 99" in unchanged_issue.body
