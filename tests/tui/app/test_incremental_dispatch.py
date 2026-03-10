"""Tests for the incremental dispatch action in ErkDashApp."""

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from tests.fakes.gateway.plan_data_provider import FakePlanDataProvider, make_plan_row
from tests.fakes.gateway.pr_service import FakePrService


class TestIncrementalDispatch:
    """Tests for the incremental dispatch flow."""

    @pytest.mark.asyncio
    async def test_callback_with_none_does_not_dispatch(self) -> None:
        """_on_incremental_dispatch_result with None does not start an operation."""
        provider = FakePlanDataProvider(plans=[make_plan_row(123, "Test Plan", pr_number=456)])
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Directly call the callback with None
            app._on_incremental_dispatch_result(None)

            # No operations should be running
            status_bar = app._status_bar
            assert status_bar is not None
            assert not status_bar._operations

    @pytest.mark.asyncio
    async def test_callback_without_pending_pr_does_not_dispatch(self) -> None:
        """_on_incremental_dispatch_result without pending PR does not start an operation."""
        provider = FakePlanDataProvider(plans=[make_plan_row(123, "Test Plan", pr_number=456)])
        filters = PlanFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Call without setting _pending_dispatch_pr
            app._on_incremental_dispatch_result("some plan text")

            # No operations should be running
            status_bar = app._status_bar
            assert status_bar is not None
            assert not status_bar._operations
