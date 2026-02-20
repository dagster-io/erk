"""Tests for '/' filter mode functionality."""

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.widgets.plan_table import PlanDataTable
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row


class TestFilterMode:
    """Tests for '/' filter mode functionality."""

    @pytest.mark.asyncio
    async def test_slash_activates_filter_mode(self) -> None:
        """Pressing '/' shows filter input and focuses it."""
        provider = FakePlanDataProvider(plans=[make_plan_row(123, "Plan A")])
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Press / to activate filter
            await pilot.press("slash")
            await pilot.pause()

            # Filter input should be visible and focused
            from textual.widgets import Input

            filter_input = app.query_one("#filter-input", Input)
            assert filter_input.has_class("visible")
            assert app.focused == filter_input

    @pytest.mark.asyncio
    async def test_filter_narrows_results(self) -> None:
        """Typing in filter input narrows displayed results."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(123, "Add user authentication"),
                make_plan_row(456, "Fix login bug"),
                make_plan_row(789, "Refactor database"),
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Verify all rows are displayed initially
            assert len(app._rows) == 3

            # Activate filter and type query
            await pilot.press("slash")
            await pilot.pause()
            await pilot.press("l", "o", "g", "i", "n")
            await pilot.pause()

            # Only matching row should be visible
            assert len(app._rows) == 1
            assert app._rows[0].plan_id == 456

    @pytest.mark.asyncio
    async def test_escape_clears_then_exits(self) -> None:
        """First escape clears text, second exits filter mode."""
        provider = FakePlanDataProvider(plans=[make_plan_row(123, "Plan A")])
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Activate filter and type
            await pilot.press("slash")
            await pilot.pause()
            await pilot.press("t", "e", "s", "t")
            await pilot.pause()

            from textual.widgets import Input

            from erk.tui.filtering.types import FilterMode

            filter_input = app.query_one("#filter-input", Input)
            assert filter_input.value == "test"
            assert app._filter_state.mode == FilterMode.ACTIVE

            # First escape clears text
            await pilot.press("escape")
            await pilot.pause()
            assert filter_input.value == ""
            assert app._filter_state.mode == FilterMode.ACTIVE

            # Second escape exits filter mode
            await pilot.press("escape")
            await pilot.pause()
            assert app._filter_state.mode == FilterMode.INACTIVE
            assert not filter_input.has_class("visible")

    @pytest.mark.asyncio
    async def test_enter_returns_focus_to_table(self) -> None:
        """Pressing Enter in filter input returns focus to table."""
        provider = FakePlanDataProvider(plans=[make_plan_row(123, "Plan A")])
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Activate filter
            await pilot.press("slash")
            await pilot.pause()

            from textual.widgets import Input

            filter_input = app.query_one("#filter-input", Input)
            assert app.focused == filter_input

            # Press Enter to return to table
            await pilot.press("enter")
            await pilot.pause()

            table = app.query_one(PlanDataTable)
            assert app.focused == table

    @pytest.mark.asyncio
    async def test_filter_by_issue_number(self) -> None:
        """Filter can match by issue number."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(123, "Plan A"),
                make_plan_row(456, "Plan B"),
                make_plan_row(789, "Plan C"),
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("slash")
            await pilot.pause()
            await pilot.press("4", "5", "6")
            await pilot.pause()

            assert len(app._rows) == 1
            assert app._rows[0].plan_id == 456

    @pytest.mark.asyncio
    async def test_filter_by_pr_number(self) -> None:
        """Filter can match by PR number."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(1, "Plan A", pr_number=100),
                make_plan_row(2, "Plan B", pr_number=200),
                make_plan_row(3, "Plan C"),
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("slash")
            await pilot.pause()
            await pilot.press("2", "0", "0")
            await pilot.pause()

            assert len(app._rows) == 1
            assert app._rows[0].plan_id == 2
