"""Tests for action_view_comments (c key from main)."""

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.screens.unresolved_comments_screen import UnresolvedCommentsScreen
from erk.tui.widgets.status_bar import StatusBar
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row


class TestActionViewComments:
    """Tests for action_view_comments (c key)."""

    @pytest.mark.asyncio
    async def test_no_selected_row_does_nothing(self) -> None:
        """No selected row -> early return, no screen pushed."""
        provider = FakePlanDataProvider(plans=[])
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            initial_stack_len = len(app.screen_stack)

            await pilot.press("c")
            await pilot.pause()

            assert len(app.screen_stack) == initial_stack_len

    @pytest.mark.asyncio
    async def test_no_pr_linked_shows_status_message(self) -> None:
        """Row with pr_number=None -> status bar shows 'No PR linked to this plan'."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")]  # No pr_number
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("c")
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            assert status_bar._message == "No PR linked to this plan"

    @pytest.mark.asyncio
    async def test_zero_unresolved_shows_status_message(self) -> None:
        """Row with 0 unresolved comments -> status bar shows 'No unresolved comments'."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456, comment_counts=(5, 5))]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("c")
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            assert status_bar._message == "No unresolved comments"

    @pytest.mark.asyncio
    async def test_unresolved_comments_pushes_screen(self) -> None:
        """Row with unresolved comments -> pushes UnresolvedCommentsScreen."""
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan", pr_number=456, comment_counts=(3, 5))]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("c")
            await pilot.pause()
            await pilot.pause()

            assert len(app.screen_stack) > 1
            assert isinstance(app.screen_stack[-1], UnresolvedCommentsScreen)
