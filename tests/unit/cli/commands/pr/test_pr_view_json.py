"""Tests for erk pr view --json output helpers."""

import json
from datetime import UTC, datetime

import click
from click.testing import CliRunner

from erk.cli.commands.pr.view_cmd import _emit_plan_json, _serialize_header
from erk_shared.plan_store.types import Plan, PlanState


def _make_plan(
    *,
    plan_id: str = "42",
    title: str = "Test Plan",
    body: str = "Plan body content",
    state: PlanState = PlanState.OPEN,
    labels: list[str] | None = None,
    objective_id: int | None = None,
) -> Plan:
    """Create a Plan for testing."""
    return Plan(
        plan_identifier=plan_id,
        title=title,
        body=body,
        state=state,
        url=f"https://github.com/test/repo/issues/{plan_id}",
        labels=labels or ["erk-plan"],
        assignees=[],
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        updated_at=datetime(2025, 1, 2, tzinfo=UTC),
        metadata={},
        objective_id=objective_id,
    )


# --- Helper command for testing _emit_plan_json via CliRunner ---


@click.command("capture")
@click.pass_obj
def _capture_emit_plan_json(obj: dict) -> None:  # type: ignore[type-arg]
    """Helper command to invoke _emit_plan_json in CliRunner context."""
    _emit_plan_json(
        obj["plan"],
        plan_id=obj["plan_id"],
        header_info=obj["header_info"],
    )


# --- Tests ---


def test_serialize_header_converts_datetime() -> None:
    """Datetime values in header_info are converted to ISO 8601 strings."""
    header = {
        "last_local_impl_at": datetime(2025, 3, 15, 10, 0, 0, tzinfo=UTC),
        "created_by": "test-user",
        "worktree_name": "my-plan",
    }

    result = _serialize_header(header)

    assert result["last_local_impl_at"] == "2025-03-15T10:00:00Z"
    assert result["created_by"] == "test-user"
    assert result["worktree_name"] == "my-plan"


def test_serialize_header_preserves_non_datetime() -> None:
    """Non-datetime values are preserved as-is."""
    header = {
        "schema_version": 2,
        "objective_issue": 9009,
        "source_repo": "dagster-io/erk",
    }

    result = _serialize_header(header)

    assert result["schema_version"] == 2
    assert result["objective_issue"] == 9009
    assert result["source_repo"] == "dagster-io/erk"


def test_emit_plan_json_includes_body() -> None:
    """JSON output always includes the full plan body (agents always want full content)."""
    runner = CliRunner()
    plan = _make_plan(body="## Step 1\nDo the thing")

    result = runner.invoke(
        _capture_emit_plan_json,
        [],
        obj={"plan": plan, "plan_id": "42", "header_info": {}},
    )

    data = json.loads(result.output)
    assert data["success"] is True
    assert data["body"] == "## Step 1\nDo the thing"


def test_emit_plan_json_output_shape() -> None:
    """JSON output has the expected fields matching get-plan-info shape."""
    runner = CliRunner()
    plan = _make_plan(
        title="Add JSON output",
        objective_id=9009,
        labels=["erk-plan", "erk-pr"],
    )
    header = {"created_by": "schrockn", "worktree_name": "json-output"}

    result = runner.invoke(
        _capture_emit_plan_json,
        [],
        obj={"plan": plan, "plan_id": "42", "header_info": header},
    )

    data = json.loads(result.output)
    assert data["success"] is True
    assert data["plan_id"] == "42"
    assert data["title"] == "Add JSON output"
    assert data["state"] == "OPEN"
    assert data["labels"] == ["erk-plan", "erk-pr"]
    assert data["objective_id"] == 9009
    assert data["header"]["created_by"] == "schrockn"
    assert data["header"]["worktree_name"] == "json-output"
    assert data["url"] == "https://github.com/test/repo/issues/42"
    assert "created_at" in data
    assert "updated_at" in data


def test_emit_plan_json_closed_state() -> None:
    """Closed plans show CLOSED state in JSON."""
    runner = CliRunner()
    plan = _make_plan(state=PlanState.CLOSED)

    result = runner.invoke(
        _capture_emit_plan_json,
        [],
        obj={"plan": plan, "plan_id": "42", "header_info": {}},
    )

    data = json.loads(result.output)
    assert data["state"] == "CLOSED"
