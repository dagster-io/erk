"""Unit tests for _update_parent_learn_status_if_learn_plan in land command."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from erk.cli.commands.land_cmd import _update_parent_learn_status_if_learn_plan
from erk_shared.context.testing import context_for_test
from erk_shared.gateway.github.metadata.plan_header import (
    extract_plan_header_learn_plan_pr,
    extract_plan_header_learn_status,
)
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.plan_helpers import (
    create_plan_store_with_plans,
    format_plan_header_body_for_test,
)


def _make_plan(
    *,
    number: int,
    title: str = "Test plan",
    labels: list[str] | None = None,
    **header_kwargs: object,
) -> Plan:
    """Create a Plan object with plan-header metadata for testing."""
    now = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
    body = format_plan_header_body_for_test(**header_kwargs)
    return Plan(
        plan_identifier=str(number),
        title=title,
        body=body,
        state=PlanState.OPEN,
        url=f"https://github.com/test-owner/test-repo/pull/{number}",
        labels=labels if labels is not None else ["erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        metadata={},
        objective_id=None,
        header_fields={},
    )


def test_update_parent_learn_status_skips_non_learn_plan(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Regular plans (without learned_from_issue) should do nothing."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    plan_number = 100
    plan = _make_plan(number=plan_number, title="Regular plan")
    backend, fake_github = create_plan_store_with_plans({str(plan_number): plan})

    ctx = context_for_test(cwd=repo_root, github=fake_github, plan_store=backend)

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
    parent_plan = _make_plan(
        number=parent_number,
        title="Parent plan",
        learn_status="pending",
        learn_plan_issue=learn_plan_number,
    )

    # Create learn plan issue (points back to parent via learned_from_issue)
    learn_plan = _make_plan(
        number=learn_plan_number,
        title="Learn: Extract patterns",
        labels=["erk-plan", "erk-learn"],
        learned_from_issue=parent_number,
    )

    backend, fake_github = create_plan_store_with_plans(
        {str(parent_number): parent_plan, str(learn_plan_number): learn_plan}
    )
    ctx = context_for_test(cwd=repo_root, github=fake_github, plan_store=backend)

    # Call the function
    _update_parent_learn_status_if_learn_plan(
        ctx,
        repo_root=repo_root,
        plan_issue_number=learn_plan_number,
        pr_number=pr_number,
    )

    # Verify success message
    captured = capsys.readouterr()
    assert f"Updated learn status on parent plan {parent_number}" in captured.err

    # Verify parent PR body was updated
    parent_pr = fake_github.get_pr(Path("/repo"), parent_number)
    learn_status = extract_plan_header_learn_status(parent_pr.body)
    assert learn_status == "plan_completed"

    learn_plan_pr = extract_plan_header_learn_plan_pr(parent_pr.body)
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
    learn_plan = _make_plan(
        number=learn_plan_number,
        title="Learn: Extract patterns",
        labels=["erk-plan", "erk-learn"],
        learned_from_issue=parent_number,
    )

    # Only the learn plan exists, not the parent
    backend, fake_github = create_plan_store_with_plans({str(learn_plan_number): learn_plan})
    ctx = context_for_test(cwd=repo_root, github=fake_github, plan_store=backend)

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


def test_update_parent_learn_status_handles_missing_plan_issue(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Gracefully handles case where the plan issue being landed doesn't exist."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    ctx = context_for_test(cwd=repo_root)

    # Should not raise - gracefully returns early
    _update_parent_learn_status_if_learn_plan(
        ctx,
        repo_root=repo_root,
        plan_issue_number=100,
        pr_number=42,
    )

    # Verify no update was made (since plan doesn't exist)
    captured = capsys.readouterr()
    assert "Updated learn status" not in captured.err
