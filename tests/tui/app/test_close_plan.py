"""Tests for close plan functionality."""

import pytest

from erk.tui.app import ErkDashApp, PlanDetailScreen
from erk.tui.data.types import PlanFilters
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row


class TestClosePlanViaCommandPalette:
    """Tests for close plan functionality via command palette.

    Note: The top-level 'c' binding was removed. Close plan is now accessible
    via the command palette in the plan detail modal (Space -> Ctrl+P -> "Close Plan").
    The execute_command tests in tests/tui/commands/test_execute_command.py
    cover the close_plan command execution. These tests verify the integration.
    """

    @pytest.mark.asyncio
    async def test_close_plan_not_accessible_via_c_key(self) -> None:
        """Top-level 'c' key should no longer close plans."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(123, "Feature A"),
                make_plan_row(456, "Feature B"),
            ],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            # Wait for data to load
            await pilot.pause()
            await pilot.pause()

            # Initially should have 2 plans
            assert len(provider._plans) == 2

            # Press 'c' - should NOT close plan (binding removed)
            await pilot.press("c")
            await pilot.pause()
            await pilot.pause()

            # Plans should remain unchanged
            assert len(provider._plans) == 2


class TestClosePlanInProcess:
    """Tests for run_close_plan_in_process functionality.

    This tests the in-process close plan action which uses the HTTP client
    directly rather than spawning a subprocess.
    """

    @pytest.mark.asyncio
    async def test_close_plan_in_process_creates_output_panel(self) -> None:
        """In-process close plan creates and mounts output panel."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Test Plan",
                    plan_url="https://github.com/test/repo/issues/123",
                )
            ],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Open detail screen
            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            detail_screen = app.screen_stack[-1]
            assert isinstance(detail_screen, PlanDetailScreen)

            # Run close plan in-process
            detail_screen.run_close_plan_in_process(123, "https://github.com/test/repo/issues/123")

            # Output panel should be created
            assert detail_screen._output_panel is not None
            assert detail_screen._command_running is True

            # Wait for worker to complete
            await pilot.pause(0.3)

            # Command should complete
            assert detail_screen._command_running is False

    @pytest.mark.asyncio
    async def test_close_plan_in_process_removes_plan_from_list(self) -> None:
        """In-process close plan removes the plan from provider."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(123, "Plan A"),
                make_plan_row(456, "Plan B"),
            ],
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Should have 2 plans
            assert len(provider._plans) == 2

            # Open detail screen
            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            detail_screen = app.screen_stack[-1]
            assert isinstance(detail_screen, PlanDetailScreen)

            # Close plan 123
            detail_screen.run_close_plan_in_process(123, "https://github.com/test/repo/issues/123")
            await pilot.pause(0.3)

            # Plan should be removed from provider
            assert len(provider._plans) == 1
            assert provider._plans[0].plan_id == 456
