"""Unit tests for maybe_advance_lifecycle_to_impl shared helper."""

from datetime import UTC, datetime
from pathlib import Path

from erk.cli.commands.pr.shared import maybe_advance_lifecycle_to_impl
from erk_shared.context.testing import context_for_test
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.plan_helpers import (
    create_plan_store_with_plans,
    format_plan_header_body_for_test,
)


def _make_plan(*, number: int, lifecycle_stage: str | None = None) -> Plan:
    """Create a Plan object with plan-header metadata for testing."""
    body = format_plan_header_body_for_test(lifecycle_stage=lifecycle_stage)
    now = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
    return Plan(
        plan_identifier=str(number),
        title=f"Plan #{number}",
        body=body,
        state=PlanState.OPEN,
        url=f"https://github.com/owner/repo/pull/{number}",
        labels=["erk-planned-pr", "erk-plan"],
        assignees=[],
        created_at=now,
        updated_at=now,
        metadata={},
        objective_id=None,
        header_fields={},
    )


def test_advances_planned_to_impl(tmp_path: Path) -> None:
    """Plan at 'planned' stage gets updated to 'impl'."""
    plan = _make_plan(number=100, lifecycle_stage="planned")
    backend, fake_github = create_plan_store_with_plans({"100": plan})
    ctx = context_for_test(cwd=tmp_path, github=fake_github, plan_store=backend)

    maybe_advance_lifecycle_to_impl(ctx, repo_root=tmp_path, plan_id="100", quiet=False)

    # Verify metadata was updated via PR body
    pr = fake_github.get_pr(Path("/repo"), 100)
    assert "lifecycle_stage: impl" in pr.body


def test_advances_none_stage_to_impl(tmp_path: Path) -> None:
    """Plan with None stage gets updated to 'impl'."""
    plan = _make_plan(number=100, lifecycle_stage=None)
    backend, fake_github = create_plan_store_with_plans({"100": plan})
    ctx = context_for_test(cwd=tmp_path, github=fake_github, plan_store=backend)

    maybe_advance_lifecycle_to_impl(ctx, repo_root=tmp_path, plan_id="100", quiet=False)

    pr = fake_github.get_pr(Path("/repo"), 100)
    assert "lifecycle_stage: impl" in pr.body


def test_skips_when_already_impl(tmp_path: Path) -> None:
    """Plan already at 'impl' is not updated (idempotent)."""
    plan = _make_plan(number=100, lifecycle_stage="impl")
    backend, fake_github = create_plan_store_with_plans({"100": plan})
    ctx = context_for_test(cwd=tmp_path, github=fake_github, plan_store=backend)

    maybe_advance_lifecycle_to_impl(ctx, repo_root=tmp_path, plan_id="100", quiet=False)

    # No body update should have been made - PR body should still have original lifecycle
    # The function should be idempotent and not issue update calls
    # We check that the lifecycle is still "impl" (no change needed)
    pr = fake_github.get_pr(Path("/repo"), 100)
    assert "lifecycle_stage: impl" in pr.body


def test_skips_when_plan_not_found(tmp_path: Path) -> None:
    """PlanNotFound result causes graceful return."""
    ctx = context_for_test(cwd=tmp_path)

    # Should not raise
    maybe_advance_lifecycle_to_impl(ctx, repo_root=tmp_path, plan_id="999", quiet=False)


def test_advances_planning_stage_to_impl(tmp_path: Path) -> None:
    """Plan at 'planning' stage gets updated to 'impl'."""
    plan = _make_plan(number=100, lifecycle_stage="planning")
    backend, fake_github = create_plan_store_with_plans({"100": plan})
    ctx = context_for_test(cwd=tmp_path, github=fake_github, plan_store=backend)

    maybe_advance_lifecycle_to_impl(ctx, repo_root=tmp_path, plan_id="100", quiet=False)

    pr = fake_github.get_pr(Path("/repo"), 100)
    assert "lifecycle_stage: impl" in pr.body
