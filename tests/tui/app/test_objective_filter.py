"""Tests for ErkDashApp - objective filter."""

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.widgets.status_bar import StatusBar
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row


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
