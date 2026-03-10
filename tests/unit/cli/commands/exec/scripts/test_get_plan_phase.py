"""Tests for get-plan-phase exec command.

Tests both the phase mapping logic (_stage_to_phase) and the CLI command
(get_plan_phase).
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_plan_phase import (
    _stage_to_phase,
    get_plan_phase,
)
from erk_shared.context.context import ErkContext
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.plan_helpers import (
    create_plan_store_with_plans,
    format_plan_header_body_for_test,
)


def _make_plan(
    plan_id: str,
    *,
    lifecycle_stage: str | None = None,
) -> Plan:
    """Create a Plan for testing with minimal required fields.

    Note: create_plan_store_with_plans converts Plan -> PRDetails -> Plan,
    so header_fields on the input Plan are NOT preserved. To set a lifecycle
    stage, use lifecycle_stage= which embeds it in the plan-header metadata
    block in the body.
    """
    body = format_plan_header_body_for_test(lifecycle_stage=lifecycle_stage)
    body += "\n\nTest plan content"
    return Plan(
        plan_identifier=plan_id,
        title="Test plan",
        body=body,
        state=PlanState.OPEN,
        url=f"https://github.com/test/repo/pull/{plan_id}",
        labels=["erk-plan"],
        assignees=[],
        created_at=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
        updated_at=datetime(2024, 1, 16, 12, 0, tzinfo=UTC),
        metadata={},
        objective_id=None,
    )


# --- _stage_to_phase mapping tests ---


def test_stage_to_phase_prompted() -> None:
    """prompted maps to plan phase."""
    assert _stage_to_phase("prompted") == "plan"


def test_stage_to_phase_planning() -> None:
    """planning maps to plan phase."""
    assert _stage_to_phase("planning") == "plan"


def test_stage_to_phase_planned() -> None:
    """planned maps to plan phase."""
    assert _stage_to_phase("planned") == "plan"


def test_stage_to_phase_impl() -> None:
    """impl maps to impl phase."""
    assert _stage_to_phase("impl") == "impl"


def test_stage_to_phase_implementing() -> None:
    """implementing maps to impl phase."""
    assert _stage_to_phase("implementing") == "impl"


def test_stage_to_phase_implemented() -> None:
    """implemented maps to impl phase."""
    assert _stage_to_phase("implemented") == "impl"


def test_stage_to_phase_merged() -> None:
    """merged maps to merged phase."""
    assert _stage_to_phase("merged") == "merged"


def test_stage_to_phase_closed() -> None:
    """closed maps to closed phase."""
    assert _stage_to_phase("closed") == "closed"


def test_stage_to_phase_none() -> None:
    """None maps to unknown phase."""
    assert _stage_to_phase(None) == "unknown"


def test_stage_to_phase_unknown_string() -> None:
    """Unrecognized stage string maps to unknown phase."""
    assert _stage_to_phase("custom-stage") == "unknown"


# --- CLI command tests ---


def test_cli_returns_plan_phase_for_planned_stage(tmp_path: Path) -> None:
    """CLI returns plan phase for a plan with planned lifecycle stage."""
    plan = _make_plan("42", lifecycle_stage="planned")
    backend, _github = create_plan_store_with_plans({"42": plan})
    ctx = ErkContext.for_test(plan_store=backend, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_plan_phase, ["42"], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output == {"success": True, "plan_number": 42, "phase": "plan"}


def test_cli_returns_impl_phase_for_impl_stage(tmp_path: Path) -> None:
    """CLI returns impl phase for a plan with impl lifecycle stage."""
    plan = _make_plan("42", lifecycle_stage="impl")
    backend, _github = create_plan_store_with_plans({"42": plan})
    ctx = ErkContext.for_test(plan_store=backend, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_plan_phase, ["42"], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output == {"success": True, "plan_number": 42, "phase": "impl"}


def test_cli_returns_plan_phase_for_draft_pr_fallback(tmp_path: Path) -> None:
    """CLI returns plan phase when no lifecycle_stage header and PR is draft+open."""
    # create_plan_store_with_plans creates draft PRs by default, so
    # the backend infers planned from is_draft=True + pr_state=OPEN
    plan = _make_plan("42")
    backend, _github = create_plan_store_with_plans({"42": plan})
    ctx = ErkContext.for_test(plan_store=backend, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_plan_phase, ["42"], obj=ctx)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["phase"] == "plan"


def test_cli_returns_exit_code_1_for_missing_plan(tmp_path: Path) -> None:
    """CLI returns exit code 1 when plan is not found."""
    backend, _github = create_plan_store_with_plans({})
    ctx = ErkContext.for_test(plan_store=backend, repo_root=tmp_path, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_plan_phase, ["999"], obj=ctx)

    assert result.exit_code == 1
