"""Unit tests for autolearn helper module."""

from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from erk.cli.commands.autolearn import maybe_create_autolearn_issue
from erk.core.context import context_for_test
from erk_shared.context.types import GlobalConfig
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.metadata.plan_header import format_plan_header_body


def _create_plan_issue(
    number: int,
    title: str,
    *,
    plan_type: str | None = None,
    created_from_session: str | None = None,
    source_plan_issues: list[int] | None = None,
    extraction_session_ids: list[str] | None = None,
) -> IssueInfo:
    """Create a test plan issue with optional plan_type in metadata."""
    body = format_plan_header_body(
        created_at=datetime.now(UTC).isoformat(),
        created_by="testuser",
        plan_type=plan_type,
        created_from_session=created_from_session,
        source_plan_issues=source_plan_issues,
        extraction_session_ids=extraction_session_ids,
    )
    return IssueInfo(
        number=number,
        title=title,
        body=body,
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["erk-plan"] if plan_type is None else ["erk-plan", "erk-learn"],
        assignees=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        author="testuser",
    )


def test_autolearn_disabled_does_nothing(tmp_path: Path) -> None:
    """Test that autolearn does nothing when config disabled."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})
    global_config = GlobalConfig.test(erk_root=tmp_path, autolearn=False)

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        global_config=global_config,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        maybe_create_autolearn_issue(
            ctx, repo_root=tmp_path, branch="P42-feature-branch", pr_number=100
        )

    # No issues created
    assert issues_ops.created_issues == []
    assert captured.getvalue() == ""


def test_autolearn_no_plan_prefix_does_nothing(tmp_path: Path) -> None:
    """Test that autolearn does nothing for branches without plan prefix."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})
    global_config = GlobalConfig.test(erk_root=tmp_path, autolearn=True)

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        global_config=global_config,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        maybe_create_autolearn_issue(
            ctx, repo_root=tmp_path, branch="feature-branch", pr_number=100
        )

    # No issues created
    assert issues_ops.created_issues == []
    assert captured.getvalue() == ""


def test_autolearn_skips_learn_plans(tmp_path: Path) -> None:
    """Test that autolearn skips branches from learn plan issues."""
    # Learn plan issues require source_plan_issues and extraction_session_ids to be set
    issue = _create_plan_issue(
        42,
        "Learn: Some Topic",
        plan_type="learn",
        source_plan_issues=[10],
        extraction_session_ids=["session-123"],
    )
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: issue})
    global_config = GlobalConfig.test(erk_root=tmp_path, autolearn=True)

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        global_config=global_config,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        maybe_create_autolearn_issue(
            ctx, repo_root=tmp_path, branch="P42-learn-topic", pr_number=100
        )

    # No issues created (source was already a learn plan)
    assert issues_ops.created_issues == []


def test_autolearn_creates_learn_issue(tmp_path: Path) -> None:
    """Test that autolearn creates learn issue for standard plan branches."""
    # Include created_from_session so find_sessions_for_plan finds sessions
    source_issue = _create_plan_issue(
        42,
        "Add Feature [erk-plan]",
        created_from_session="abc-123-session-id",
    )
    issues_ops = FakeGitHubIssues(username="testuser", issues={42: source_issue})
    global_config = GlobalConfig.test(erk_root=tmp_path, autolearn=True)

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        global_config=global_config,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        maybe_create_autolearn_issue(
            ctx, repo_root=tmp_path, branch="P42-add-feature", pr_number=100
        )

    # Verify an issue was created
    # created_issues is a list of (title, body, labels) tuples
    assert len(issues_ops.created_issues) == 1
    title, _body, labels = issues_ops.created_issues[0]
    assert "Learn: Add Feature" in title
    assert "erk-plan" in labels
    assert "erk-learn" in labels

    # Verify success message
    output = captured.getvalue()
    assert "Created learn plan" in output


def test_autolearn_handles_source_issue_not_found(tmp_path: Path) -> None:
    """Test that autolearn handles missing source issue gracefully."""
    # No issues exist
    issues_ops = FakeGitHubIssues(username="testuser", issues={})
    global_config = GlobalConfig.test(erk_root=tmp_path, autolearn=True)

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        global_config=global_config,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        maybe_create_autolearn_issue(
            ctx, repo_root=tmp_path, branch="P42-feature-branch", pr_number=100
        )

    # No issues created
    assert issues_ops.created_issues == []
    # Warning should be displayed
    output = captured.getvalue()
    assert "Could not fetch source issue" in output


def test_autolearn_with_none_global_config_does_nothing(tmp_path: Path) -> None:
    """Test that autolearn does nothing when global_config is None."""
    issues_ops = FakeGitHubIssues(username="testuser", issues={})

    ctx = context_for_test(
        issues=issues_ops,
        cwd=tmp_path,
        global_config=None,
    )

    captured = StringIO()
    with patch("sys.stderr", captured):
        maybe_create_autolearn_issue(
            ctx, repo_root=tmp_path, branch="P42-feature-branch", pr_number=100
        )

    # No issues created
    assert issues_ops.created_issues == []
    assert captured.getvalue() == ""
