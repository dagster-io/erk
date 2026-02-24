"""Tests for plan output models and builders."""

import json
from datetime import UTC, datetime

from erk.cli.commands.plan.output_builders import build_plan_list_entry, build_plan_view_entry
from erk_shared.gateway.plan_data_provider.fake import make_plan_row
from erk_shared.plan_store.types import Plan, PlanState


class TestBuildPlanListEntry:
    """Tests for build_plan_list_entry builder."""

    def test_minimal_row(self) -> None:
        """Minimal PlanRowData produces correct fields."""
        row = make_plan_row(42, "Test Plan")
        entry = build_plan_list_entry(row)

        assert entry.plan_id == 42
        assert entry.title == "Test Plan"
        assert entry.author == "test-user"
        assert entry.pr is None
        assert entry.workflow_run is None
        assert entry.objective is None

    def test_pr_fields(self) -> None:
        """PlanRowData with PR fields produces nested PR object."""
        row = make_plan_row(
            42,
            "Test Plan",
            pr_number=100,
            pr_url="https://github.com/test/repo/pull/100",
            pr_state="OPEN",
            pr_title="Fix something",
            pr_head_branch="fix-something",
            comment_counts=(3, 5),
        )
        entry = build_plan_list_entry(row)

        assert entry.pr is not None
        assert entry.pr.number == 100
        assert entry.pr.url == "https://github.com/test/repo/pull/100"
        assert entry.pr.state == "OPEN"
        assert entry.pr.title == "Fix something"
        assert entry.pr.head_branch == "fix-something"
        assert entry.pr.resolved_comments == 3
        assert entry.pr.total_comments == 5

    def test_workflow_run(self) -> None:
        """PlanRowData with run fields produces nested WorkflowRun object."""
        row = make_plan_row(
            42,
            "Test Plan",
            run_id="12345",
            run_status="completed",
            run_conclusion="success",
            run_url="https://github.com/test/repo/actions/runs/12345",
        )
        entry = build_plan_list_entry(row)

        assert entry.workflow_run is not None
        assert entry.workflow_run.run_id == "12345"
        assert entry.workflow_run.status == "completed"
        assert entry.workflow_run.conclusion == "success"
        assert entry.has_cloud_run is True

    def test_objective(self) -> None:
        """PlanRowData with objective produces nested Objective object."""
        row = make_plan_row(
            42,
            "Test Plan",
            objective_issue=88,
            objective_done_nodes=3,
            objective_total_nodes=7,
        )
        entry = build_plan_list_entry(row)

        assert entry.objective is not None
        assert entry.objective.issue == 88
        assert entry.objective.done_nodes == 3
        assert entry.objective.total_nodes == 7

    def test_branch_priority(self) -> None:
        """Branch prefers pr_head_branch over worktree_branch."""
        row = make_plan_row(
            42,
            "Test Plan",
            pr_head_branch="pr-branch",
            worktree_branch="wt-branch",
        )
        entry = build_plan_list_entry(row)
        assert entry.branch == "pr-branch"

    def test_branch_fallback_to_worktree(self) -> None:
        """Branch falls back to worktree_branch when pr_head_branch is None."""
        row = make_plan_row(42, "Test Plan", worktree_branch="wt-branch")
        entry = build_plan_list_entry(row)
        assert entry.branch == "wt-branch"

    def test_iso_timestamps(self) -> None:
        """Timestamps are formatted as ISO 8601."""
        row = make_plan_row(
            42,
            "Test Plan",
            created_at=datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC),
            updated_at=datetime(2025, 1, 16, 12, 0, 0, tzinfo=UTC),
        )
        entry = build_plan_list_entry(row)
        assert "2025-01-15" in entry.created_at
        assert "2025-01-16" in entry.updated_at

    def test_learn_status(self) -> None:
        """Learn status is preserved in nested Learn object."""
        row = make_plan_row(
            42,
            "Test Plan",
            learn_status="completed_with_plan",
            learn_plan_issue=99,
        )
        entry = build_plan_list_entry(row)
        assert entry.learn.status == "completed_with_plan"
        assert entry.learn.plan_issue == 99

    def test_serializable_to_json(self) -> None:
        """PlanListEntry can be serialized to JSON via dataclasses.asdict."""
        from dataclasses import asdict

        row = make_plan_row(
            42,
            "Test Plan",
            pr_number=100,
            run_id="12345",
            objective_issue=88,
        )
        entry = build_plan_list_entry(row)
        data = asdict(entry)
        json_str = json.dumps(data, default=str)
        parsed = json.loads(json_str)
        assert parsed["plan_id"] == 42
        assert parsed["pr"]["number"] == 100
        assert parsed["workflow_run"]["run_id"] == "12345"
        assert parsed["objective"]["issue"] == 88


class TestFormatMethods:
    """Tests for PlanListEntry format methods."""

    def test_format_plan_id(self) -> None:
        row = make_plan_row(42, "Test Plan")
        entry = build_plan_list_entry(row)
        assert entry.format_plan_id() == "#42"

    def test_format_location_local_only(self) -> None:
        row = make_plan_row(42, "Test Plan", exists_locally=True)
        entry = build_plan_list_entry(row)
        assert "\U0001f4bb" in entry.format_location()
        assert "\u2601" not in entry.format_location()

    def test_format_location_cloud_only(self) -> None:
        row = make_plan_row(42, "Test Plan", run_url="https://example.com")
        entry = build_plan_list_entry(row)
        assert "\u2601" in entry.format_location()
        assert "\U0001f4bb" not in entry.format_location()

    def test_format_location_both(self) -> None:
        row = make_plan_row(42, "Test Plan", exists_locally=True, run_url="https://example.com")
        entry = build_plan_list_entry(row)
        loc = entry.format_location()
        assert "\U0001f4bb" in loc
        assert "\u2601" in loc

    def test_format_location_neither(self) -> None:
        row = make_plan_row(42, "Test Plan")
        entry = build_plan_list_entry(row)
        assert entry.format_location() == "-"

    def test_format_run_state_success(self) -> None:
        row = make_plan_row(
            42, "Test Plan", run_id="1", run_status="completed", run_conclusion="success"
        )
        entry = build_plan_list_entry(row)
        assert entry.format_run_state() == "\u2705"

    def test_format_run_state_failure(self) -> None:
        row = make_plan_row(
            42, "Test Plan", run_id="1", run_status="completed", run_conclusion="failure"
        )
        entry = build_plan_list_entry(row)
        assert entry.format_run_state() == "\u274c"

    def test_format_run_state_no_run(self) -> None:
        row = make_plan_row(42, "Test Plan")
        entry = build_plan_list_entry(row)
        assert entry.format_run_state() == "-"

    def test_format_objective_present(self) -> None:
        row = make_plan_row(42, "Test Plan", objective_issue=88)
        entry = build_plan_list_entry(row)
        assert entry.format_objective() == "#88"

    def test_format_objective_absent(self) -> None:
        row = make_plan_row(42, "Test Plan")
        entry = build_plan_list_entry(row)
        assert entry.format_objective() == "-"


class TestBuildPlanViewEntry:
    """Tests for build_plan_view_entry builder."""

    def test_basic_plan(self) -> None:
        """Basic Plan produces correct view entry."""
        plan = Plan(
            plan_identifier="42",
            title="Test Plan",
            body="Plan body",
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/42",
            labels=["erk-plan"],
            assignees=["alice"],
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=datetime(2025, 1, 2, tzinfo=UTC),
            metadata={},
            objective_id=None,
        )
        entry = build_plan_view_entry(plan, header_info={}, include_body=False)

        assert entry.plan_id == 42
        assert entry.title == "Test Plan"
        assert entry.state == "OPEN"
        assert entry.body is None  # include_body=False
        assert entry.labels == ["erk-plan"]
        assert entry.assignees == ["alice"]

    def test_with_body(self) -> None:
        """include_body=True includes plan body."""
        plan = Plan(
            plan_identifier="42",
            title="Test Plan",
            body="Plan body content",
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/42",
            labels=[],
            assignees=[],
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=datetime(2025, 1, 2, tzinfo=UTC),
            metadata={},
            objective_id=None,
        )
        entry = build_plan_view_entry(plan, header_info={}, include_body=True)
        assert entry.body == "Plan body content"

    def test_with_header_info(self) -> None:
        """Header info populates nested header object."""
        plan = Plan(
            plan_identifier="42",
            title="Test Plan",
            body="",
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/42",
            labels=[],
            assignees=[],
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=datetime(2025, 1, 2, tzinfo=UTC),
            metadata={},
            objective_id=None,
        )
        header = {
            "created_by": "schrockn",
            "schema_version": "2",
            "worktree_name": "P42-test",
            "objective_issue": 88,
            "branch_name": "P42-test-plan",
        }
        entry = build_plan_view_entry(plan, header_info=header, include_body=False)

        assert entry.header.created_by == "schrockn"
        assert entry.header.schema_version == "2"
        assert entry.header.worktree == "P42-test"
        assert entry.header.objective_issue == 88
        assert entry.branch == "P42-test-plan"

    def test_learn_status(self) -> None:
        """Learn section populated from header info."""
        plan = Plan(
            plan_identifier="42",
            title="Test Plan",
            body="",
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/42",
            labels=[],
            assignees=[],
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=datetime(2025, 1, 2, tzinfo=UTC),
            metadata={},
            objective_id=None,
        )
        header = {
            "learn_status": "completed_with_plan",
            "learn_plan_issue": 99,
        }
        entry = build_plan_view_entry(plan, header_info=header, include_body=False)
        assert entry.learn.status == "completed_with_plan"
        assert entry.learn.plan_issue == 99

    def test_format_state(self) -> None:
        """format_state returns state value."""
        plan = Plan(
            plan_identifier="42",
            title="Test Plan",
            body="",
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/42",
            labels=[],
            assignees=[],
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=datetime(2025, 1, 2, tzinfo=UTC),
            metadata={},
            objective_id=None,
        )
        entry = build_plan_view_entry(plan, header_info={}, include_body=False)
        assert entry.format_state() == "OPEN"

    def test_format_learn_status_not_started(self) -> None:
        plan = Plan(
            plan_identifier="42",
            title="Test",
            body="",
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/42",
            labels=[],
            assignees=[],
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=datetime(2025, 1, 2, tzinfo=UTC),
            metadata={},
            objective_id=None,
        )
        entry = build_plan_view_entry(plan, header_info={}, include_body=False)
        assert entry.format_learn_status() == "- not started"

    def test_format_learn_status_completed_with_plan(self) -> None:
        plan = Plan(
            plan_identifier="42",
            title="Test",
            body="",
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/42",
            labels=[],
            assignees=[],
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=datetime(2025, 1, 2, tzinfo=UTC),
            metadata={},
            objective_id=None,
        )
        header = {"learn_status": "completed_with_plan", "learn_plan_issue": 99}
        entry = build_plan_view_entry(plan, header_info=header, include_body=False)
        assert entry.format_learn_status() == "#99"
