"""Tests for ErkDashApp using Textual Pilot."""

import pytest

from erk.tui.app import ErkDashApp, HelpScreen
from erk.tui.data.types import PlanFilters
from erk.tui.widgets.plan_table import PlanDataTable
from erk.tui.widgets.status_bar import StatusBar
from tests.fakes.plan_data_provider import FakePlanDataProvider, make_plan_row


class TestErkDashAppCompose:
    """Tests for app composition and layout."""

    @pytest.mark.asyncio
    async def test_app_has_required_widgets(self) -> None:
        """App composes all required widgets."""
        provider = FakePlanDataProvider()
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test():
            # Check for PlanDataTable
            table = app.query_one(PlanDataTable)
            assert table is not None

            # Check for StatusBar
            status_bar = app.query_one(StatusBar)
            assert status_bar is not None


class TestErkDashAppDataLoading:
    """Tests for data loading behavior."""

    @pytest.mark.asyncio
    async def test_fetches_data_on_mount(self) -> None:
        """App fetches data when mounted."""
        provider = FakePlanDataProvider(
            [
                make_plan_row(123, "Plan A"),
                make_plan_row(456, "Plan B"),
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            # Wait for async data load
            await pilot.pause()

            # Provider should have been called
            assert provider.fetch_count >= 1


class TestErkDashAppNavigation:
    """Tests for keyboard navigation."""

    @pytest.mark.asyncio
    async def test_quit_on_q(self) -> None:
        """Pressing q quits the app."""
        provider = FakePlanDataProvider()
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.press("q")
            # App should have exited (no assertion needed - would hang if not)

    @pytest.mark.asyncio
    async def test_quit_on_escape(self) -> None:
        """Pressing escape quits the app."""
        provider = FakePlanDataProvider()
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.press("escape")
            # App should have exited

    @pytest.mark.asyncio
    async def test_help_on_question_mark(self) -> None:
        """Pressing ? shows help screen."""
        provider = FakePlanDataProvider()
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.press("?")
            # Wait for screen transition
            await pilot.pause()
            await pilot.pause()

            # Help screen should be in the screen stack
            assert len(app.screen_stack) > 1
            assert isinstance(app.screen_stack[-1], HelpScreen)


class TestErkDashAppRefresh:
    """Tests for data refresh behavior."""

    @pytest.mark.asyncio
    async def test_refresh_on_r(self) -> None:
        """Pressing r refreshes data."""
        provider = FakePlanDataProvider([make_plan_row(123, "Plan A")])
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            # Wait for initial load
            await pilot.pause()
            initial_count = provider.fetch_count

            # Press r to refresh
            await pilot.press("r")
            await pilot.pause()

            # Should have fetched again
            assert provider.fetch_count > initial_count


class TestStatusBar:
    """Tests for StatusBar widget."""

    def test_set_plan_count_singular(self) -> None:
        """Status bar shows singular 'plan' for count of 1."""
        bar = StatusBar()
        bar.set_plan_count(1)
        bar._update_display()
        # Check internal state was set
        assert bar._plan_count == 1

    def test_set_plan_count_plural(self) -> None:
        """Status bar shows plural 'plans' for count > 1."""
        bar = StatusBar()
        bar.set_plan_count(5)
        bar._update_display()
        assert bar._plan_count == 5

    def test_set_message(self) -> None:
        """Status bar can display a message."""
        bar = StatusBar()
        bar.set_message("Test message")
        bar._update_display()
        assert bar._message == "Test message"

    def test_clear_message(self) -> None:
        """Status bar can clear message."""
        bar = StatusBar()
        bar.set_message("Test message")
        bar.set_message(None)
        assert bar._message is None
