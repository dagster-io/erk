"""Tests for the generic renderer and CLI integration."""

import json
from datetime import UTC, datetime

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.cli.commands.plan.output_builders import build_plan_list_entry, build_plan_view_entry
from erk.cli.output_framework.generic_renderer import render_json_detail, render_json_list
from erk_shared.gateway.github.fake import FakeGitHub
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues
from erk_shared.gateway.github.issues.types import IssueInfo
from erk_shared.gateway.plan_data_provider.fake import make_plan_row
from erk_shared.plan_store.types import Plan, PlanState
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_inmem_env
from tests.test_utils.plan_helpers import create_plan_store_with_plans


class TestRenderJsonList:
    """Tests for render_json_list."""

    def test_basic_structure(self) -> None:
        """JSON list output has correct root key and total_count."""
        rows = [make_plan_row(1, "Plan A"), make_plan_row(2, "Plan B")]
        entries = [build_plan_list_entry(r) for r in rows]
        result = render_json_list(entries)
        parsed = json.loads(result)

        assert "plans" in parsed
        assert parsed["total_count"] == 2
        assert len(parsed["plans"]) == 2
        assert parsed["plans"][0]["plan_id"] == 1
        assert parsed["plans"][1]["plan_id"] == 2

    def test_empty_list(self) -> None:
        """Empty list returns valid JSON with zero count."""
        result = render_json_list([])
        parsed = json.loads(result)
        assert parsed["total_count"] == 0

    def test_nested_pr_in_json(self) -> None:
        """PR fields appear as nested object in JSON."""
        row = make_plan_row(
            42,
            "Test Plan",
            pr_number=100,
            pr_url="https://github.com/test/repo/pull/100",
            pr_state="OPEN",
        )
        entries = [build_plan_list_entry(row)]
        result = render_json_list(entries)
        parsed = json.loads(result)
        plan = parsed["plans"][0]
        assert plan["pr"]["number"] == 100
        assert plan["pr"]["state"] == "OPEN"

    def test_null_pr_in_json(self) -> None:
        """PR is null when no PR linked."""
        row = make_plan_row(42, "Test Plan")
        entries = [build_plan_list_entry(row)]
        result = render_json_list(entries)
        parsed = json.loads(result)
        assert parsed["plans"][0]["pr"] is None


class TestRenderJsonDetail:
    """Tests for render_json_detail."""

    def test_basic_structure(self) -> None:
        """JSON detail output has correct root key."""
        plan = Plan(
            plan_identifier="42",
            title="Test Plan",
            body="Plan body",
            state=PlanState.OPEN,
            url="https://github.com/test/repo/issues/42",
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=datetime(2025, 1, 2, tzinfo=UTC),
            metadata={},
            objective_id=None,
        )
        entry = build_plan_view_entry(plan, header_info={}, include_body=False)
        result = render_json_detail(entry)
        parsed = json.loads(result)

        assert "plan" in parsed
        assert parsed["plan"]["plan_id"] == 42
        assert parsed["plan"]["title"] == "Test Plan"
        assert parsed["plan"]["state"] == "OPEN"

    def test_nested_header_in_json(self) -> None:
        """Header info appears as nested object."""
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
        header = {"created_by": "schrockn", "schema_version": "2"}
        entry = build_plan_view_entry(plan, header_info=header, include_body=False)
        result = render_json_detail(entry)
        parsed = json.loads(result)

        assert parsed["plan"]["header"]["created_by"] == "schrockn"
        assert parsed["plan"]["header"]["schema_version"] == "2"


def _plan_to_issue(plan: Plan) -> IssueInfo:
    """Convert Plan to IssueInfo for test setup."""
    return IssueInfo(
        number=int(plan.plan_identifier),
        title=plan.title,
        body=plan.body,
        state="OPEN" if plan.state == PlanState.OPEN else "CLOSED",
        url=plan.url,
        labels=plan.labels,
        assignees=plan.assignees,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        author="test-user",
    )


class TestCLIIntegration:
    """CLI integration tests for --json-output flag."""

    def test_plan_list_json_output(self) -> None:
        """plan list --json-output produces valid JSON on stdout."""
        plan = Plan(
            plan_identifier="1",
            title="Test Plan",
            body="",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/1",
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
            metadata={},
            objective_id=None,
        )

        runner = CliRunner()
        with erk_inmem_env(runner) as env:
            issues = FakeGitHubIssues(issues={1: _plan_to_issue(plan)})
            github = FakeGitHub(issues_data=[_plan_to_issue(plan)])
            ctx = build_workspace_test_context(env, issues=issues, github=github)

            result = runner.invoke(cli, ["plan", "list", "--json-output"], obj=ctx)

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert "plans" in parsed
            assert parsed["total_count"] == 1
            assert parsed["plans"][0]["plan_id"] == 1
            assert parsed["plans"][0]["title"] == "Test Plan"

    def test_plan_view_json_output(self) -> None:
        """plan view --json-output produces valid JSON on stdout."""
        plan = Plan(
            plan_identifier="42",
            title="Test Plan",
            body="Plan body content",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/42",
            labels=["erk-plan"],
            assignees=["alice"],
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 2, tzinfo=UTC),
            metadata={},
            objective_id=None,
        )

        runner = CliRunner()
        with erk_inmem_env(runner) as env:
            store, _ = create_plan_store_with_plans({"42": plan})
            ctx = build_workspace_test_context(env, plan_store=store)

            result = runner.invoke(cli, ["plan", "view", "--json-output", "42"], obj=ctx)

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert "plan" in parsed
            assert parsed["plan"]["plan_id"] == 42
            assert parsed["plan"]["title"] == "Test Plan"
            assert parsed["plan"]["state"] == "OPEN"
            # Body should be None by default (no --full)
            assert parsed["plan"]["body"] is None

    def test_plan_view_json_output_with_full(self) -> None:
        """plan view --json-output --full includes body."""
        plan = Plan(
            plan_identifier="42",
            title="Test Plan",
            body="Full plan body",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/42",
            labels=[],
            assignees=[],
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 2, tzinfo=UTC),
            metadata={},
            objective_id=None,
        )

        runner = CliRunner()
        with erk_inmem_env(runner) as env:
            store, _ = create_plan_store_with_plans({"42": plan})
            ctx = build_workspace_test_context(env, plan_store=store)

            result = runner.invoke(cli, ["plan", "view", "--json-output", "--full", "42"], obj=ctx)

            assert result.exit_code == 0
            parsed = json.loads(result.output)
            assert parsed["plan"]["body"] == "Full plan body"

    def test_plan_list_no_json_flag_still_works(self) -> None:
        """plan list without --json-output still renders the Rich table."""
        plan = Plan(
            plan_identifier="1",
            title="Normal Plan",
            body="",
            state=PlanState.OPEN,
            url="https://github.com/owner/repo/issues/1",
            labels=["erk-plan"],
            assignees=[],
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            updated_at=datetime(2024, 1, 1, tzinfo=UTC),
            metadata={},
            objective_id=None,
        )

        runner = CliRunner()
        with erk_inmem_env(runner) as env:
            issues = FakeGitHubIssues(issues={1: _plan_to_issue(plan)})
            github = FakeGitHub(issues_data=[_plan_to_issue(plan)])
            ctx = build_workspace_test_context(env, issues=issues, github=github)

            result = runner.invoke(cli, ["plan", "list"], obj=ctx)

            assert result.exit_code == 0
            assert "Found 1 plan(s)" in result.output
