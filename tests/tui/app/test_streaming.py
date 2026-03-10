"""Tests for streaming command timeout and close plan in-process."""

from pathlib import Path

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PrFilters
from erk.tui.screens.plan_detail_screen import PlanDetailScreen
from tests.fakes.gateway.plan_data_provider import FakePrDataProvider, make_pr_row
from tests.fakes.gateway.pr_service import FakePrService


class TestStreamingCommandTimeout:
    """Tests for streaming command timeout behavior.

    The streaming command timeout feature kills long-running subprocesses
    to prevent the TUI from hanging indefinitely.
    """

    @pytest.mark.asyncio
    async def test_timeout_fires_and_kills_process(self, tmp_path: Path) -> None:
        """Timeout kills subprocess and shows error message.

        Uses a short timeout (0.1s) with a sleep command to verify
        the timeout handler fires and terminates the process.
        """
        provider = FakePrDataProvider(
            plans=[make_pr_row(123, "Test Plan")],
        )
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider,
            service=FakePrService(repo_root=tmp_path),
            filters=filters,
            refresh_interval=0,
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Open detail screen
            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            detail_screen = app.screen_stack[-1]
            assert isinstance(detail_screen, PlanDetailScreen)

            # Run a command with very short timeout - sleep for 10 seconds
            # but timeout after 0.1 seconds
            detail_screen.run_streaming_command(
                ["sleep", "10"],
                cwd=tmp_path,
                title="Test Command",
                timeout=0.1,
            )

            # Wait for timeout to fire (0.1s + buffer)
            await pilot.pause(0.3)

            # Verify timeout was handled
            assert detail_screen._command_running is False
            panel = detail_screen._output_panel
            assert panel is not None
            assert panel.is_completed
            assert panel.succeeded is False

    @pytest.mark.asyncio
    async def test_successful_command_cancels_timer(self, tmp_path: Path) -> None:
        """Fast command completes before timeout and cancels timer."""
        provider = FakePrDataProvider(
            plans=[make_pr_row(123, "Test Plan")],
        )
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider,
            service=FakePrService(repo_root=tmp_path),
            filters=filters,
            refresh_interval=0,
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Open detail screen
            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            detail_screen = app.screen_stack[-1]
            assert isinstance(detail_screen, PlanDetailScreen)

            # Run a fast command with long timeout
            detail_screen.run_streaming_command(
                ["echo", "hello"],
                cwd=tmp_path,
                title="Test Command",
                timeout=30.0,
            )

            # Wait for command to complete
            await pilot.pause(0.3)

            # Command should have completed successfully
            assert detail_screen._command_running is False
            # Timer should have been cancelled (set to None)
            assert detail_screen._stream_timeout_timer is None
            panel = detail_screen._output_panel
            assert panel is not None
            assert panel.is_completed
            assert panel.succeeded is True

    @pytest.mark.asyncio
    async def test_timeout_disabled_when_zero(self, tmp_path: Path) -> None:
        """Setting timeout=0 disables the timeout timer."""
        provider = FakePrDataProvider(
            plans=[make_pr_row(123, "Test Plan")],
        )
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider,
            service=FakePrService(repo_root=tmp_path),
            filters=filters,
            refresh_interval=0,
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Open detail screen
            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            detail_screen = app.screen_stack[-1]
            assert isinstance(detail_screen, PlanDetailScreen)

            # Run command with timeout disabled
            detail_screen.run_streaming_command(
                ["echo", "hello"],
                cwd=tmp_path,
                title="Test Command",
                timeout=0,
            )

            # Timer should never have been set
            # (immediately after run_streaming_command, before async work)
            assert detail_screen._stream_timeout_timer is None

            # Wait for command to complete
            await pilot.pause(0.3)

            # Command should have completed normally
            assert detail_screen._command_running is False
            panel = detail_screen._output_panel
            assert panel is not None
            assert panel.is_completed
            assert panel.succeeded is True

    @pytest.mark.asyncio
    async def test_dismiss_blocked_during_command(self, tmp_path: Path) -> None:
        """Modal cannot be dismissed while command is running."""
        provider = FakePrDataProvider(
            plans=[make_pr_row(123, "Test Plan")],
        )
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider,
            service=FakePrService(repo_root=tmp_path),
            filters=filters,
            refresh_interval=0,
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Open detail screen
            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            detail_screen = app.screen_stack[-1]
            assert isinstance(detail_screen, PlanDetailScreen)

            # Start a long-running command
            detail_screen.run_streaming_command(
                ["sleep", "10"],
                cwd=tmp_path,
                title="Test Command",
                timeout=30.0,  # Won't fire during this test
            )

            # Command is running
            assert detail_screen._command_running is True

            # Try to dismiss - should be blocked
            await pilot.press("escape")
            await pilot.pause()

            # Modal should still be showing
            assert isinstance(app.screen_stack[-1], PlanDetailScreen)


class TestClosePlanInProcess:
    """Tests for run_close_pr_in_process functionality.

    This tests the in-process close plan action which uses the HTTP client
    directly rather than spawning a subprocess.
    """

    @pytest.mark.asyncio
    async def test_close_pr_in_process_creates_output_panel(self) -> None:
        """In-process close plan creates and mounts output panel."""
        provider = FakePrDataProvider(
            plans=[
                make_pr_row(
                    123,
                    "Test Plan",
                    pr_url="https://github.com/test/repo/issues/123",
                )
            ],
        )
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

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
            detail_screen.run_close_pr_in_process(123, "https://github.com/test/repo/issues/123")

            # Output panel should be created
            assert detail_screen._output_panel is not None
            assert detail_screen._command_running is True

            # Wait for worker to complete
            await pilot.pause(0.3)

            # Command should complete
            assert detail_screen._command_running is False

    @pytest.mark.asyncio
    async def test_close_pr_in_process_completes_successfully(self) -> None:
        """In-process close plan completes with success status."""
        provider = FakePrDataProvider(
            plans=[
                make_pr_row(123, "Plan A"),
                make_pr_row(456, "Plan B"),
            ],
        )
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Open detail screen
            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            detail_screen = app.screen_stack[-1]
            assert isinstance(detail_screen, PlanDetailScreen)

            # Close plan 123
            detail_screen.run_close_pr_in_process(123, "https://github.com/test/repo/issues/123")
            await pilot.pause(0.3)

            # Close should complete successfully
            assert detail_screen._command_running is False
            panel = detail_screen._output_panel
            assert panel is not None
            assert panel.is_completed
            assert panel.succeeded is True
