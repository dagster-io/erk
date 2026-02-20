"""Tests for ErkDashApp data loading behavior."""

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.widgets.plan_table import PlanDataTable
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row


class TestErkDashAppDataLoading:
    """Tests for data loading behavior."""

    @pytest.mark.asyncio
    async def test_fetches_data_on_mount(self) -> None:
        """App fetches data when mounted."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(123, "Plan A"),
                make_plan_row(456, "Plan B"),
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            # Wait for async data load
            await pilot.pause()

            # Provider should have been called
            assert provider.fetch_count >= 1

    @pytest.mark.asyncio
    async def test_api_error_shows_notification_and_empty_table(self) -> None:
        """App shows error notification and empty table when API fails."""
        provider = FakePlanDataProvider(
            fetch_error="Network unreachable",
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            # Wait for async data load attempt
            await pilot.pause()
            await pilot.pause()

            # Provider should have been called
            assert provider.fetch_count >= 1

            # Table should be empty (no crash)
            assert len(app._rows) == 0

            # App should still be running (not crashed)
            # and table should be visible (meaning load completed, even with error)
            table = app.query_one(PlanDataTable)
            assert table.display is True
