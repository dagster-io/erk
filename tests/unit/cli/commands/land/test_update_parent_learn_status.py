"""Unit tests for _update_parent_learn_status_if_learn_plan in land command."""

from pathlib import Path

import pytest

from erk.cli.commands.land_cmd import _update_parent_learn_status_if_learn_plan
from erk.core.context import context_for_test
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.metadata.plan_header import (
    extract_plan_header_learn_plan_pr,
    extract_plan_header_learn_status,
)
from tests.test_utils.github_helpers import create_test_issue
from tests.test_utils.plan_helpers import format_plan_header_body_for_test


def test_update_parent_learn_status_skips_non_learn_plan(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Regular plans (without learned_from_issue) should do nothing."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create a regular plan issue (no learned_from_issue)
    plan_number = 100
    plan_body = format_plan_header_body_for_test()
    plan_issue = create_test_issue(
        number=plan_number,
        title="Regular plan",
        body=plan_body,
        labels=["erk-plan"],
    )

    fake_issues = FakeGitHubIssues(issues={plan_number: plan_issue})
    ctx = context_for_test(cwd=repo_root, issues=fake_issues)

    # Call the function
    _update_parent_learn_status_if_learn_plan(
        ctx,
        repo_root=repo_root,
        plan_issue_number=plan_number,
        pr_number=42,
    )

    # Verify no output (nothing was updated)
    captured = capsys.readouterr()
    assert "Updated learn status" not in captured.err

    # Verify no issues were updated (updated_bodies is a list of tuples)
    assert fake_issues.updated_bodies == []


def test_update_parent_learn_status_updates_parent(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Learn plan updates parent's learn_status and learn_plan_pr."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    parent_number = 100
    learn_plan_number = 200
    pr_number = 42

    # Create parent plan issue (the original plan)
    parent_body = format_plan_header_body_for_test(
        learn_status="pending",
        learn_plan_issue=learn_plan_number,
    )
    parent_issue = create_test_issue(
        number=parent_number,
        title="Parent plan",
        body=parent_body,
        labels=["erk-plan"],
    )

    # Create learn plan issue (points back to parent via learned_from_issue)
    learn_body = format_plan_header_body_for_test(
        learned_from_issue=parent_number,
    )
    learn_issue = create_test_issue(
        number=learn_plan_number,
        title="Learn: Extract patterns",
        body=learn_body,
        labels=["erk-plan", "erk-learn"],
    )

    fake_issues = FakeGitHubIssues(
        issues={parent_number: parent_issue, learn_plan_number: learn_issue}
    )
    ctx = context_for_test(cwd=repo_root, issues=fake_issues)

    # Call the function
    _update_parent_learn_status_if_learn_plan(
        ctx,
        repo_root=repo_root,
        plan_issue_number=learn_plan_number,
        pr_number=pr_number,
    )

    # Verify success message
    captured = capsys.readouterr()
    assert f"Updated learn status on parent plan #{parent_number}" in captured.err

    # Verify parent issue was updated (updated_bodies is a list of tuples)
    assert len(fake_issues.updated_bodies) == 1
    updated_number, updated_body = fake_issues.updated_bodies[0]
    assert updated_number == parent_number

    # Verify learn_status is now "plan_completed"
    learn_status = extract_plan_header_learn_status(updated_body)
    assert learn_status == "plan_completed"

    # Verify learn_plan_pr was set
    learn_plan_pr = extract_plan_header_learn_plan_pr(updated_body)
    assert learn_plan_pr == pr_number


def test_update_parent_learn_status_handles_missing_parent(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Gracefully handles case where parent issue doesn't exist."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    parent_number = 100  # Does NOT exist
    learn_plan_number = 200

    # Create learn plan that references non-existent parent
    learn_body = format_plan_header_body_for_test(
        learned_from_issue=parent_number,
    )
    learn_issue = create_test_issue(
        number=learn_plan_number,
        title="Learn: Extract patterns",
        body=learn_body,
        labels=["erk-plan", "erk-learn"],
    )

    # Only the learn plan exists, not the parent
    fake_issues = FakeGitHubIssues(issues={learn_plan_number: learn_issue})
    ctx = context_for_test(cwd=repo_root, issues=fake_issues)

    # Should not raise - gracefully returns early
    _update_parent_learn_status_if_learn_plan(
        ctx,
        repo_root=repo_root,
        plan_issue_number=learn_plan_number,
        pr_number=42,
    )

    # Verify no update was made (since parent doesn't exist)
    captured = capsys.readouterr()
    assert "Updated learn status" not in captured.err
    assert fake_issues.updated_bodies == []


def test_update_parent_learn_status_handles_missing_plan_issue(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Gracefully handles case where the plan issue being landed doesn't exist."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    plan_number = 100  # Does NOT exist
    fake_issues = FakeGitHubIssues(issues={})
    ctx = context_for_test(cwd=repo_root, issues=fake_issues)

    # Should not raise - gracefully returns early
    _update_parent_learn_status_if_learn_plan(
        ctx,
        repo_root=repo_root,
        plan_issue_number=plan_number,
        pr_number=42,
    )

    # Verify no update was made (since plan doesn't exist)
    captured = capsys.readouterr()
    assert "Updated learn status" not in captured.err
    assert fake_issues.updated_bodies == []
