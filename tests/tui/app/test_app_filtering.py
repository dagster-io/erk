"""Tests for stack and objective filter functionality."""

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.widgets.status_bar import StatusBar
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row


class TestStackFilter:
    """Tests for 't' stack filter functionality."""

    @pytest.mark.asyncio
    async def test_t_filters_to_stack_members(self) -> None:
        """Pressing 't' filters table to rows sharing the same Graphite stack."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(1, "Plan A", pr_head_branch="branch-a"),
                make_plan_row(2, "Plan B", pr_head_branch="branch-b"),
                make_plan_row(3, "Plan C", pr_head_branch="branch-c"),
            ]
        )
        # Every branch in a stack maps to the full stack list (mirrors real Graphite)
        stack_ac = ["branch-a", "branch-c"]
        provider.set_branch_stack("branch-a", stack_ac)
        provider.set_branch_stack("branch-c", stack_ac)
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            assert len(app._rows) == 3

            # Rows are sorted descending by plan_id; row 0 is branch-c
            await pilot.press("t")
            await pilot.pause()

            assert len(app._rows) == 2
            plan_ids = {r.plan_id for r in app._rows}
            assert plan_ids == {1, 3}

    @pytest.mark.asyncio
    async def test_t_toggles_off(self) -> None:
        """Pressing 't' again restores all rows."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(1, "Plan A", pr_head_branch="branch-a"),
                make_plan_row(2, "Plan B", pr_head_branch="branch-b"),
                make_plan_row(3, "Plan C", pr_head_branch="branch-c"),
            ]
        )
        stack_ac = ["branch-a", "branch-c"]
        provider.set_branch_stack("branch-a", stack_ac)
        provider.set_branch_stack("branch-c", stack_ac)
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Activate stack filter
            await pilot.press("t")
            await pilot.pause()
            assert len(app._rows) == 2

            # Toggle off
            await pilot.press("t")
            await pilot.pause()
            assert len(app._rows) == 3

    @pytest.mark.asyncio
    async def test_escape_clears_stack_filter_before_text_filter(self) -> None:
        """Escape clears stack filter first, then text filter, then quits."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(1, "Plan A", pr_head_branch="branch-a"),
                make_plan_row(2, "Plan B", pr_head_branch="branch-b"),
            ]
        )
        # Row 0 (selected) is branch-b due to descending sort
        provider.set_branch_stack("branch-b", ["branch-b"])
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Activate stack filter
            await pilot.press("t")
            await pilot.pause()
            assert app._stack_filter_branches is not None
            assert len(app._rows) == 1

            # Escape clears stack filter (not quit)
            await pilot.press("escape")
            await pilot.pause()
            assert app._stack_filter_branches is None
            assert len(app._rows) == 2

    @pytest.mark.asyncio
    async def test_t_on_row_without_branch_shows_message(self) -> None:
        """Pressing 't' on row with no pr_head_branch shows status message."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(1, "Plan A")]  # No pr_head_branch
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("t")
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            assert status_bar._message == "No branch for stack filter"
            assert app._stack_filter_branches is None

    @pytest.mark.asyncio
    async def test_t_on_branch_not_in_stack_shows_message(self) -> None:
        """Pressing 't' on branch not in a Graphite stack shows status message."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(1, "Plan A", pr_head_branch="solo-branch")]
            # No stack configured for solo-branch -> get_branch_stack returns None
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("t")
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            assert status_bar._message == "Not in a Graphite stack"
            assert app._stack_filter_branches is None

    @pytest.mark.asyncio
    async def test_stack_filter_composes_with_text_filter(self) -> None:
        """Stack filter and text filter compose -- stack first, then text narrows."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(1, "Add feature alpha", pr_head_branch="branch-a"),
                make_plan_row(2, "Fix bug beta", pr_head_branch="branch-b"),
                make_plan_row(3, "Add feature gamma", pr_head_branch="branch-c"),
            ]
        )
        # branch-a and branch-c share a stack (register both directions)
        stack_ac = ["branch-a", "branch-c"]
        provider.set_branch_stack("branch-a", stack_ac)
        provider.set_branch_stack("branch-c", stack_ac)
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Activate stack filter first
            await pilot.press("t")
            await pilot.pause()
            assert len(app._rows) == 2  # Plans 1 and 3

            # Now activate text filter
            await pilot.press("slash")
            await pilot.pause()
            await pilot.press("g", "a", "m", "m", "a")
            await pilot.pause()

            # Text filter narrows further
            assert len(app._rows) == 1
            assert app._rows[0].plan_id == 3

    @pytest.mark.asyncio
    async def test_view_switch_clears_stack_filter(self) -> None:
        """Switching views clears the stack filter."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(1, "Plan A", pr_head_branch="branch-a"),
                make_plan_row(2, "Plan B", pr_head_branch="branch-b"),
            ]
        )
        # Row 0 (selected) is branch-b due to descending sort
        provider.set_branch_stack("branch-b", ["branch-b"])
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Activate stack filter
            await pilot.press("t")
            await pilot.pause()
            assert app._stack_filter_branches is not None

            # Switch view
            await pilot.press("2")
            await pilot.pause()

            assert app._stack_filter_branches is None
            assert app._stack_filter_label is None


class TestObjectiveFilter:
    """Tests for 'o' objective filter functionality."""

    @pytest.mark.asyncio
    async def test_o_filters_plans_by_objective(self) -> None:
        """Pressing 'o' filters table to rows sharing the same objective_issue."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(1, "Plan A", objective_issue=42),
                make_plan_row(2, "Plan B", objective_issue=99),
                make_plan_row(3, "Plan C", objective_issue=42),
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            assert len(app._rows) == 3

            # Row 0 (selected) is plan_id=3 (descending sort), objective_issue=42
            await pilot.press("o")
            await pilot.pause()

            assert len(app._rows) == 2
            plan_ids = {r.plan_id for r in app._rows}
            assert plan_ids == {1, 3}

    @pytest.mark.asyncio
    async def test_o_toggles_off_objective_filter(self) -> None:
        """Pressing 'o' again restores all rows."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(1, "Plan A", objective_issue=42),
                make_plan_row(2, "Plan B", objective_issue=99),
                make_plan_row(3, "Plan C", objective_issue=42),
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Activate objective filter
            await pilot.press("o")
            await pilot.pause()
            assert len(app._rows) == 2

            # Toggle off
            await pilot.press("o")
            await pilot.pause()
            assert len(app._rows) == 3

    @pytest.mark.asyncio
    async def test_o_on_plan_without_objective_shows_message(self) -> None:
        """Pressing 'o' on plan with no objective_issue shows status message."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(1, "Plan A")]  # No objective_issue
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("o")
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            assert status_bar._message == "Plan not linked to an objective"
            assert app._objective_filter_issue is None

    @pytest.mark.asyncio
    async def test_escape_clears_objective_filter(self) -> None:
        """Escape clears objective filter."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(1, "Plan A", objective_issue=42),
                make_plan_row(2, "Plan B", objective_issue=99),
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Row 0 (selected) is plan_id=2 (descending sort), objective_issue=99
            await pilot.press("o")
            await pilot.pause()
            assert app._objective_filter_issue is not None
            assert len(app._rows) == 1

            # Escape clears objective filter
            await pilot.press("escape")
            await pilot.pause()
            assert app._objective_filter_issue is None
            assert len(app._rows) == 2

    @pytest.mark.asyncio
    async def test_view_switch_clears_objective_filter(self) -> None:
        """Switching views clears the objective filter."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(1, "Plan A", objective_issue=42),
                make_plan_row(2, "Plan B", objective_issue=99),
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Activate objective filter
            await pilot.press("o")
            await pilot.pause()
            assert app._objective_filter_issue is not None

            # Switch view
            await pilot.press("2")
            await pilot.pause()

            assert app._objective_filter_issue is None
            assert app._objective_filter_label is None

    @pytest.mark.asyncio
    async def test_objective_filter_composes_with_text_filter(self) -> None:
        """Objective filter and text filter compose -- objective first, then text narrows."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(1, "Add feature alpha", objective_issue=42),
                make_plan_row(2, "Fix bug beta", objective_issue=99),
                make_plan_row(3, "Add feature gamma", objective_issue=42),
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Row 0 (selected) is plan_id=3, objective_issue=42
            await pilot.press("o")
            await pilot.pause()
            assert len(app._rows) == 2  # Plans 1 and 3

            # Now activate text filter
            await pilot.press("slash")
            await pilot.pause()
            await pilot.press("g", "a", "m", "m", "a")
            await pilot.pause()

            # Text filter narrows further
            assert len(app._rows) == 1
            assert app._rows[0].plan_id == 3
