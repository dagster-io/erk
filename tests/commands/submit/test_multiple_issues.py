"""Tests for submitting multiple issues."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import ERK_PLAN_LABEL, submit_cmd
from erk_shared.gateway.github.types import PRDetails
from erk_shared.plan_store.types import PlanState
from tests.commands.submit.conftest import (
    create_plan,
    create_pr_details_for_plan,
    make_plan_body,
    setup_submit_context,
)


def test_submit_multiple_issues_success(tmp_path: Path) -> None:
    """Test submit successfully handles multiple issue numbers (happy path)."""
    plan_123 = create_plan("123", "Feature A", body=make_plan_body("Implementation for A..."))
    plan_456 = create_plan("456", "Feature B", body=make_plan_body("Implementation for B..."))

    ctx, fake_git, fake_github, _, _, _ = setup_submit_context(
        tmp_path,
        {"123": plan_123, "456": plan_456},
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123", "456"], obj=ctx)

    assert result.exit_code == 0, result.output
    assert "2 issue(s) submitted successfully!" in result.output
    assert "#123: Feature A" in result.output
    assert "#456: Feature B" in result.output

    # Verify both workflows were triggered
    assert len(fake_github.triggered_workflows) == 2


def test_submit_multiple_issues_atomic_validation_failure(tmp_path: Path) -> None:
    """Test atomic validation: if second PR is CLOSED, nothing is submitted."""
    plan_123 = create_plan("123", "Feature A", body=make_plan_body("Implementation for A..."))
    plan_456 = create_plan(
        "456",
        "Feature B",
        body=make_plan_body("Implementation for B..."),
        state=PlanState.CLOSED,
    )

    # Create PRDetails with second PR in CLOSED state
    pr_123 = create_pr_details_for_plan(plan_123, "plan-123")
    pr_456 = PRDetails(
        number=456,
        url=plan_456.url,
        title=plan_456.title,
        body=plan_456.body,
        state="CLOSED",
        is_draft=True,
        base_ref_name="main",
        head_ref_name="plan-456",
        is_cross_repository=False,
        mergeable="MERGEABLE",
        merge_state_status="CLEAN",
        owner="test-owner",
        repo="test-repo",
        labels=(ERK_PLAN_LABEL,),
    )

    ctx, _, fake_github, _, _, _ = setup_submit_context(
        tmp_path,
        {"123": plan_123, "456": plan_456},
        pr_details_map={123: pr_123, 456: pr_456},
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123", "456"], obj=ctx)

    # Should fail on the second PR validation (CLOSED)
    assert result.exit_code == 1
    assert "CLOSED" in result.output

    # Validation happens before submission — no workflows triggered
    assert len(fake_github.triggered_workflows) == 0
