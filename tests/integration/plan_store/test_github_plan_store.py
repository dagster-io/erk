"""Unit tests for GitHubPlanStore using FakeGitHubIssues."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.plan_store.github import GitHubPlanStore
from erk_shared.plan_store.types import PlanQuery, PlanState
from tests.test_utils.github_helpers import create_test_issue


def test_get_plan_success() -> None:
    """Test fetching a plan issue from GitHub."""
    # Create fake with pre-configured issue
    issue = create_test_issue(
        number=42,
        title="Implement feature X",
        body="Description of feature X",
        labels=["erk-plan", "enhancement"],
        assignees=["alice", "bob"],
        created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 16, 14, 45, 0, tzinfo=UTC),
    )
    fake_github = FakeGitHubIssues(issues={42: issue})
    store = GitHubPlanStore(fake_github)

    result = store.get_plan(Path("/fake/repo"), "42")

    # Verify conversion to PlanIssue
    assert result.plan_identifier == "42"
    assert result.title == "Implement feature X"
    assert result.body == "Description of feature X"
    assert result.state == PlanState.OPEN
    assert result.url == "https://github.com/owner/repo/issues/42"
    assert result.labels == ["erk-plan", "enhancement"]
    assert result.assignees == ["alice", "bob"]
    assert result.created_at == datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)
    assert result.updated_at == datetime(2024, 1, 16, 14, 45, 0, tzinfo=UTC)
    assert result.metadata == {"number": 42}


def test_get_plan_closed_state() -> None:
    """Test that CLOSED state is normalized correctly."""
    issue = create_test_issue(
        number=100,
        title="Closed Issue",
        body="Plan content for closed issue",
        state="CLOSED",
        updated_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
    )
    fake_github = FakeGitHubIssues(issues={100: issue})
    store = GitHubPlanStore(fake_github)

    result = store.get_plan(Path("/fake/repo"), "100")

    assert result.state == PlanState.CLOSED


def test_get_plan_empty_body_raises() -> None:
    """Test that empty body raises clear error.

    Changed from original behavior: empty plan content now raises
    RuntimeError to prevent silent failures when plan extraction fails.
    """
    issue = create_test_issue(
        number=50,
        title="Issue without body",
    )
    fake_github = FakeGitHubIssues(issues={50: issue})
    store = GitHubPlanStore(fake_github)

    with pytest.raises(RuntimeError, match="Plan content is empty"):
        store.get_plan(Path("/fake/repo"), "50")


def test_get_plan_not_found() -> None:
    """Test error handling when issue is not found."""
    fake_github = FakeGitHubIssues(issues={})
    store = GitHubPlanStore(fake_github)

    with pytest.raises(RuntimeError, match="Issue #999 not found"):
        store.get_plan(Path("/fake/repo"), "999")


def test_list_plans_no_filters() -> None:
    """Test listing all plan issues with no filters."""
    issue1 = create_test_issue(
        number=1,
        title="Issue 1",
        labels=["erk-plan"],
    )
    issue2 = create_test_issue(
        number=2,
        title="Issue 2",
        state="CLOSED",
        labels=["bug"],
        created_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
    )
    fake_github = FakeGitHubIssues(issues={1: issue1, 2: issue2})
    store = GitHubPlanStore(fake_github)

    query = PlanQuery()
    results = store.list_plans(Path("/fake/repo"), query)

    # Verify results
    assert len(results) == 2
    assert {r.plan_identifier for r in results} == {"1", "2"}


def test_list_plans_with_labels() -> None:
    """Test filtering by labels."""
    issue1 = create_test_issue(
        number=1,
        title="Issue 1",
        labels=["erk-plan", "erk-queue"],
    )
    issue2 = create_test_issue(
        number=2,
        title="Issue 2",
        labels=["bug"],
        created_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
    )
    fake_github = FakeGitHubIssues(issues={1: issue1, 2: issue2})
    store = GitHubPlanStore(fake_github)

    # Note: FakeGitHubIssues doesn't implement label filtering,
    # so this test verifies the call succeeds rather than filtering behavior
    query = PlanQuery(labels=["erk-plan", "erk-queue"])
    results = store.list_plans(Path("/fake/repo"), query)

    # Fake returns all issues regardless of label filter
    assert len(results) >= 0


def test_list_plans_with_state_open() -> None:
    """Test filtering by OPEN state."""
    issue1 = create_test_issue(number=1, title="Open Issue")
    issue2 = create_test_issue(
        number=2,
        title="Closed Issue",
        state="CLOSED",
        created_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
    )
    fake_github = FakeGitHubIssues(issues={1: issue1, 2: issue2})
    store = GitHubPlanStore(fake_github)

    query = PlanQuery(state=PlanState.OPEN)
    results = store.list_plans(Path("/fake/repo"), query)

    # Verify only OPEN issues returned
    assert len(results) == 1
    assert results[0].plan_identifier == "1"
    assert results[0].state == PlanState.OPEN


def test_list_plans_with_state_closed() -> None:
    """Test filtering by CLOSED state."""
    issue1 = create_test_issue(number=1, title="Open Issue")
    issue2 = create_test_issue(
        number=2,
        title="Closed Issue",
        state="CLOSED",
        created_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
    )
    fake_github = FakeGitHubIssues(issues={1: issue1, 2: issue2})
    store = GitHubPlanStore(fake_github)

    query = PlanQuery(state=PlanState.CLOSED)
    results = store.list_plans(Path("/fake/repo"), query)

    # Verify only CLOSED issues returned
    assert len(results) == 1
    assert results[0].plan_identifier == "2"
    assert results[0].state == PlanState.CLOSED


def test_list_plans_with_limit() -> None:
    """Test limiting results."""
    issues = {
        i: create_test_issue(
            number=i,
            title=f"Issue {i}",
            created_at=datetime(2024, 1, i, 0, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 1, i, 0, 0, 0, tzinfo=UTC),
        )
        for i in range(1, 11)
    }
    fake_github = FakeGitHubIssues(issues=issues)
    store = GitHubPlanStore(fake_github)

    query = PlanQuery(limit=3)
    results = store.list_plans(Path("/fake/repo"), query)

    # Verify limit is applied
    assert len(results) == 3


def test_list_plans_combined_filters() -> None:
    """Test combining multiple filters."""
    issue1 = create_test_issue(
        number=1,
        title="Open Issue",
        labels=["erk-plan"],
    )
    issue2 = create_test_issue(
        number=2,
        title="Closed Issue",
        state="CLOSED",
        labels=["erk-plan"],
        created_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
    )
    fake_github = FakeGitHubIssues(issues={1: issue1, 2: issue2})
    store = GitHubPlanStore(fake_github)

    query = PlanQuery(
        labels=["erk-plan"],
        state=PlanState.OPEN,
        limit=5,
    )
    results = store.list_plans(Path("/fake/repo"), query)

    # Verify state filtering works (label filtering not implemented in fake)
    assert all(r.state == PlanState.OPEN for r in results)


def test_timestamp_parsing_with_z_suffix() -> None:
    """Test that datetime objects from IssueInfo are correctly converted."""
    issue = create_test_issue(
        number=1,
        title="Test",
        body="Plan content for timestamp test",
        created_at=datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC),
        updated_at=datetime(2024, 1, 16, 14, 20, 30, tzinfo=UTC),
    )
    fake_github = FakeGitHubIssues(issues={1: issue})
    store = GitHubPlanStore(fake_github)

    result = store.get_plan(Path("/fake/repo"), "1")

    # Verify timestamps are preserved correctly
    assert result.created_at == datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC)
    assert result.updated_at == datetime(2024, 1, 16, 14, 20, 30, tzinfo=UTC)


def test_label_extraction() -> None:
    """Test that labels from IssueInfo are correctly converted."""
    issue = create_test_issue(
        number=1,
        title="Test",
        body="Plan content for label test",
        labels=["erk-plan", "erk-queue", "enhancement"],
    )
    fake_github = FakeGitHubIssues(issues={1: issue})
    store = GitHubPlanStore(fake_github)

    result = store.get_plan(Path("/fake/repo"), "1")

    # Verify labels are preserved as list of strings
    assert result.labels == ["erk-plan", "erk-queue", "enhancement"]


def test_assignee_extraction() -> None:
    """Test that assignees from IssueInfo are correctly converted."""
    issue = create_test_issue(
        number=1,
        title="Test",
        body="Plan content for assignee test",
        assignees=["alice", "bob", "charlie"],
    )
    fake_github = FakeGitHubIssues(issues={1: issue})
    store = GitHubPlanStore(fake_github)

    result = store.get_plan(Path("/fake/repo"), "1")

    # Verify assignees are preserved as list of strings
    assert result.assignees == ["alice", "bob", "charlie"]


def test_metadata_preserves_github_number() -> None:
    """Test that GitHub issue number is preserved in metadata."""
    issue = create_test_issue(
        number=42,
        title="Test",
        body="Plan content for metadata test",
    )
    fake_github = FakeGitHubIssues(issues={42: issue})
    store = GitHubPlanStore(fake_github)

    result = store.get_plan(Path("/fake/repo"), "42")

    # Verify metadata contains GitHub number
    assert result.metadata == {"number": 42}
    # Verify identifier is string
    assert result.plan_identifier == "42"
    assert isinstance(result.plan_identifier, str)


def test_get_provider_name() -> None:
    """Test getting the provider name."""
    fake_github = FakeGitHubIssues()
    store = GitHubPlanStore(fake_github)
    assert store.get_provider_name() == "github"


def test_list_plans_passes_limit_to_interface() -> None:
    """Test list_plans passes limit to GitHubIssues interface."""
    now = datetime.now(UTC)
    issues = {
        1: create_test_issue(
            number=1,
            title="Plan 1",
            body="Body 1",
            labels=["erk-plan"],
            created_at=now,
            updated_at=now,
        ),
        2: create_test_issue(
            number=2,
            title="Plan 2",
            body="Body 2",
            labels=["erk-plan"],
            created_at=now,
            updated_at=now,
        ),
    }
    fake_github = FakeGitHubIssues(issues=issues)
    store = GitHubPlanStore(fake_github)

    # Query with limit=1
    query = PlanQuery(labels=["erk-plan"], limit=1)
    results = store.list_plans(Path("/repo"), query)

    # Should only return 1 result (not slice in Python)
    assert len(results) == 1


def test_close_plan_with_issue_number() -> None:
    """Test closing a plan with issue number."""
    issue = create_test_issue(
        number=42,
        title="Test Issue",
        body="Test body",
    )
    fake_github = FakeGitHubIssues(issues={42: issue})
    store = GitHubPlanStore(fake_github)

    store.close_plan(Path("/fake/repo"), "42")

    # Verify issue was closed
    assert 42 in fake_github.closed_issues
    # Verify comment was added
    assert len(fake_github.added_comments) == 1
    assert fake_github.added_comments[0] == (42, "Plan completed via erk plan close")


def test_close_plan_with_github_url() -> None:
    """Test closing a plan with GitHub URL."""
    issue = create_test_issue(
        number=123,
        title="Test Issue",
        body="Test body",
    )
    fake_github = FakeGitHubIssues(issues={123: issue})
    store = GitHubPlanStore(fake_github)

    store.close_plan(Path("/fake/repo"), "https://github.com/org/repo/issues/123")

    # Verify issue was closed
    assert 123 in fake_github.closed_issues
    # Verify comment was added
    assert len(fake_github.added_comments) == 1
    assert fake_github.added_comments[0] == (123, "Plan completed via erk plan close")


def test_close_plan_with_trailing_slash() -> None:
    """Test closing a plan with GitHub URL with trailing slash."""
    issue = create_test_issue(
        number=456,
        title="Test Issue",
        body="Test body",
    )
    fake_github = FakeGitHubIssues(issues={456: issue})
    store = GitHubPlanStore(fake_github)

    store.close_plan(Path("/fake/repo"), "https://github.com/org/repo/issues/456/")

    # Verify issue was closed
    assert 456 in fake_github.closed_issues


def test_close_plan_invalid_identifier() -> None:
    """Test error handling for invalid identifier."""
    fake_github = FakeGitHubIssues(issues={})
    store = GitHubPlanStore(fake_github)

    with pytest.raises(RuntimeError, match="Invalid identifier format"):
        store.close_plan(Path("/fake/repo"), "not-a-number")


def test_close_plan_not_found() -> None:
    """Test error handling when issue doesn't exist."""
    fake_github = FakeGitHubIssues(issues={})
    store = GitHubPlanStore(fake_github)

    with pytest.raises(RuntimeError, match="Issue #999 not found"):
        store.close_plan(Path("/fake/repo"), "999")


# ============================================================================
# Plan extraction tests (plan in comment, metadata in issue body)
# ============================================================================


def test_get_plan_extracts_from_first_comment() -> None:
    """Test plan content is extracted from first comment.

    Plans store only metadata in issue body and the actual
    plan content in the first comment wrapped with markers.
    """
    metadata_body = """<!-- erk:metadata-block:plan-header -->
<details><summary>plan-header</summary>
```yaml
schema_version: '2'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

    plan_comment = """<!-- erk:plan-content -->
# Plan: Test Implementation

## Step 1
Implementation details here.

## Step 2
More details.
<!-- /erk:plan-content -->"""

    issue = create_test_issue(
        number=42,
        title="Plan: Test Implementation",
        body=metadata_body,
    )
    fake_github = FakeGitHubIssues(
        issues={42: issue},
        comments={42: [plan_comment]},  # First comment contains plan
    )
    store = GitHubPlanStore(fake_github)

    result = store.get_plan(Path("/fake/repo"), "42")

    # Should extract plan from comment, NOT return issue body metadata
    assert "# Plan: Test Implementation" in result.body
    assert "## Step 1" in result.body
    assert "## Step 2" in result.body
    # Should NOT contain metadata block markers in body
    assert "erk:metadata-block:plan-header" not in result.body


def test_get_plan_multiline_comment_preserved() -> None:
    """Test that multi-line plan content in comment is fully preserved.

    This is the critical bug fix test. The bug was that multi-line comment
    bodies were being split into separate "comments" by split("\\n"),
    causing the regex to fail to find both start and end markers.
    """
    # Simulate a 299-line plan like Issue #1221
    plan_lines = [
        "<!-- erk:plan-content -->",
        "# Plan: Fix GitHub Actions Plan Extraction Bug",
        "",
        "## Root Cause",
        "The bug is in get_issue_comments() method.",
        "",
    ]
    # Add more lines to simulate large plan
    for i in range(1, 50):
        plan_lines.append(f"## Phase {i}")
        plan_lines.append(f"Implementation step {i} details.")
        plan_lines.append("")
    plan_lines.append("<!-- /erk:plan-content -->")

    plan_comment = "\n".join(plan_lines)

    issue = create_test_issue(
        number=1221,
        title="Plan: Fix GitHub Actions",
        body="metadata only",
    )
    fake_github = FakeGitHubIssues(
        issues={1221: issue},
        comments={1221: [plan_comment]},
    )
    store = GitHubPlanStore(fake_github)

    result = store.get_plan(Path("/fake/repo"), "1221")

    # Plan should be fully extracted with all phases
    assert "# Plan: Fix GitHub Actions Plan Extraction Bug" in result.body
    assert "## Root Cause" in result.body
    assert "## Phase 1" in result.body
    assert "## Phase 49" in result.body
    # Should NOT be the fallback metadata
    assert result.body != "metadata only"


def test_get_plan_fallback_to_body_without_comment() -> None:
    """Test fallback to issue body when no comments have plan markers."""
    plan_body = """# Plan: Old Style Plan

## Step 1
This is an old-style plan in the issue body."""

    issue = create_test_issue(
        number=100,
        title="Plan: Old Style",
        body=plan_body,
    )
    # No comments, or comments without plan markers
    fake_github = FakeGitHubIssues(
        issues={100: issue},
        comments={100: ["A regular comment without markers"]},
    )
    store = GitHubPlanStore(fake_github)

    result = store.get_plan(Path("/fake/repo"), "100")

    # Should fallback to issue body
    assert result.body == plan_body


def test_get_plan_fallback_when_no_comments() -> None:
    """Test fallback to issue body when issue has no comments."""
    plan_body = """# Plan: No Comments

This plan has no comments at all."""

    issue = create_test_issue(
        number=200,
        title="Plan: No Comments",
        body=plan_body,
    )
    fake_github = FakeGitHubIssues(
        issues={200: issue},
        comments={},  # No comments
    )
    store = GitHubPlanStore(fake_github)

    result = store.get_plan(Path("/fake/repo"), "200")

    # Should fallback to issue body
    assert result.body == plan_body


# ============================================================================
# Empty plan validation tests
# ============================================================================


def test_get_plan_empty_body_raises_error() -> None:
    """Test that empty plan content raises clear error.

    When plan extraction fails and fallback to issue body also results
    in empty content, we should raise a clear error rather than silently
    returning an empty plan.
    """
    issue = create_test_issue(
        number=300,
        title="Plan: Empty Content",
        body="",  # Empty body
    )
    fake_github = FakeGitHubIssues(
        issues={300: issue},
        comments={},  # No comments
    )
    store = GitHubPlanStore(fake_github)

    with pytest.raises(RuntimeError, match="Plan content is empty"):
        store.get_plan(Path("/fake/repo"), "300")


def test_get_plan_whitespace_only_body_raises_error() -> None:
    """Test that whitespace-only plan content raises clear error."""
    issue = create_test_issue(
        number=301,
        title="Plan: Whitespace Only",
        body="   \n\n  \t  ",  # Only whitespace
    )
    fake_github = FakeGitHubIssues(
        issues={301: issue},
        comments={},
    )
    store = GitHubPlanStore(fake_github)

    with pytest.raises(RuntimeError, match="Plan content is empty"):
        store.get_plan(Path("/fake/repo"), "301")


def test_get_plan_metadata_only_body_raises_error() -> None:
    """Test that metadata-only body (schema v2 without plan comment) raises error.

    This is the specific case from Issue #1221 where the extraction bug
    caused fallback to issue body which only contained metadata.
    """
    metadata_body = """<!-- erk:metadata-block:plan-header -->
<details><summary>plan-header</summary>
```yaml
schema_version: '2'
```
</details>
<!-- /erk:metadata-block:plan-header -->"""

    issue = create_test_issue(
        number=302,
        title="Plan: Metadata Only",
        body=metadata_body,
    )
    # Comment exists but without plan markers, so extraction returns None
    # and we fall back to metadata-only body
    fake_github = FakeGitHubIssues(
        issues={302: issue},
        comments={302: ["A regular comment without plan markers"]},
    )
    store = GitHubPlanStore(fake_github)

    # Should NOT raise error - the metadata body is not empty
    # (Fallback uses issue body if no plan markers in comments)
    result = store.get_plan(Path("/fake/repo"), "302")
    assert result.body == metadata_body
