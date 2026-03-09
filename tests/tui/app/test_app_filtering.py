"""Tests for stack, objective, and author filter functionality."""

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.widgets.status_bar import StatusBar
from erk_shared.fakes.plan_data_provider import FakePlanDataProvider, make_plan_row
from erk_shared.fakes.plan_service import FakePlanService


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
        service = FakePlanService()
        # Every branch in a stack maps to the full stack list (mirrors real Graphite)
        stack_ac = ["branch-a", "branch-c"]
        service.set_branch_stack("branch-a", stack_ac)
        service.set_branch_stack("branch-c", stack_ac)
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

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
        service = FakePlanService()
        stack_ac = ["branch-a", "branch-c"]
        service.set_branch_stack("branch-a", stack_ac)
        service.set_branch_stack("branch-c", stack_ac)
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

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
        service = FakePlanService()
        # Row 0 (selected) is branch-b due to descending sort
        service.set_branch_stack("branch-b", ["branch-b"])
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

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
        service = FakePlanService()
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

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
        service = FakePlanService()
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

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
        service = FakePlanService()
        # branch-a and branch-c share a stack (register both directions)
        stack_ac = ["branch-a", "branch-c"]
        service.set_branch_stack("branch-a", stack_ac)
        service.set_branch_stack("branch-c", stack_ac)
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

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
        service = FakePlanService()
        # Row 0 (selected) is branch-b due to descending sort
        service.set_branch_stack("branch-b", ["branch-b"])
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

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
        service = FakePlanService()
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

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
        service = FakePlanService()
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

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
        service = FakePlanService()
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

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
        service = FakePlanService()
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

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
        service = FakePlanService()
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

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
        service = FakePlanService()
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

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


class TestAuthorFilter:
    """Tests for 'a' author filter (toggle all users) functionality."""

    @pytest.mark.asyncio
    async def test_a_toggles_show_all_users_on(self) -> None:
        """Pressing 'a' sets _show_all_users to True and triggers refresh."""
        provider = FakePlanDataProvider(plans=[make_plan_row(1, "Plan A")])
        service = FakePlanService()
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            assert not app._show_all_users
            initial_fetch_count = provider.fetch_count

            await pilot.press("a")
            await pilot.pause()
            await pilot.pause()

            assert app._show_all_users
            assert provider.fetch_count > initial_fetch_count

    @pytest.mark.asyncio
    async def test_a_toggles_show_all_users_off(self) -> None:
        """Pressing 'a' twice returns to my-plans mode."""
        provider = FakePlanDataProvider(plans=[make_plan_row(1, "Plan A")])
        service = FakePlanService()
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("a")
            await pilot.pause()
            await pilot.pause()
            assert app._show_all_users

            await pilot.press("a")
            await pilot.pause()
            await pilot.pause()
            assert not app._show_all_users

    @pytest.mark.asyncio
    async def test_a_clears_data_cache(self) -> None:
        """Pressing 'a' clears the data cache to force re-fetch."""
        provider = FakePlanDataProvider(plans=[make_plan_row(1, "Plan A")])
        service = FakePlanService()
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # After initial load, cache should have data
            assert len(app._data_cache) > 0

            await pilot.press("a")
            await pilot.pause()

            # Cache was cleared (then refilled by the re-fetch)
            # Verify it was rebuilt from the re-fetch
            assert provider.fetch_count >= 2

    @pytest.mark.asyncio
    async def test_a_updates_status_bar_author_filter(self) -> None:
        """Pressing 'a' updates the status bar author filter indicator."""
        provider = FakePlanDataProvider(plans=[make_plan_row(1, "Plan A")])
        service = FakePlanService()
        filters = PlanFilters(
            labels=("erk-plan",),
            state="open",
            run_state=None,
            limit=None,
            show_prs=False,
            show_runs=False,
            exclude_labels=(),
            creator="testuser",
        )
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            assert status_bar._author_filter is None

            await pilot.press("a")
            await pilot.pause()

            assert status_bar._author_filter == "all"

            await pilot.press("a")
            await pilot.pause()
            await pilot.pause()

            assert status_bar._author_filter == "testuser"

    @pytest.mark.asyncio
    async def test_escape_clears_all_users_filter(self) -> None:
        """Escape clears the all-users filter before other filters."""
        provider = FakePlanDataProvider(plans=[make_plan_row(1, "Plan A")])
        service = FakePlanService()
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("a")
            await pilot.pause()
            await pilot.pause()
            assert app._show_all_users

            # Escape clears all-users filter (not quit)
            await pilot.press("escape")
            await pilot.pause()
            await pilot.pause()
            assert not app._show_all_users

    @pytest.mark.asyncio
    async def test_original_creator_preserved(self) -> None:
        """The original creator value is preserved across toggles."""
        provider = FakePlanDataProvider(plans=[make_plan_row(1, "Plan A")])
        service = FakePlanService()
        filters = PlanFilters(
            labels=("erk-plan",),
            state="open",
            run_state=None,
            limit=None,
            show_prs=False,
            show_runs=False,
            exclude_labels=(),
            creator="myuser",
        )
        app = ErkDashApp(provider=provider, service=service, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            assert app._original_creator == "myuser"

            # Toggle on and off
            await pilot.press("a")
            await pilot.pause()
            await pilot.pause()
            await pilot.press("a")
            await pilot.pause()
            await pilot.pause()

            # Original creator should still be preserved
            assert app._original_creator == "myuser"
