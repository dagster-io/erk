"""Tests for the one-shot prompt action in ErkDashApp."""

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PrFilters
from erk.tui.screens.one_shot_prompt_screen import OneShotPromptScreen
from tests.fakes.gateway.plan_data_provider import FakePrDataProvider, make_pr_row
from tests.fakes.gateway.pr_service import FakePrService


class TestActionOneShotPrompt:
    """Tests for action_one_shot_prompt (x key)."""

    @pytest.mark.asyncio
    async def test_x_pushes_prompt_screen(self) -> None:
        """Pressing 'x' pushes OneShotPromptScreen even with no rows."""
        provider = FakePrDataProvider(plans=[])
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("x")
            await pilot.pause()
            await pilot.pause()

            assert len(app.screen_stack) > 1
            assert isinstance(app.screen_stack[-1], OneShotPromptScreen)

    @pytest.mark.asyncio
    async def test_x_works_with_rows_present(self) -> None:
        """Pressing 'x' pushes OneShotPromptScreen when rows exist (global action)."""
        provider = FakePrDataProvider(plans=[make_pr_row(123, "Test Plan")])
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("x")
            await pilot.pause()
            await pilot.pause()

            assert isinstance(app.screen_stack[-1], OneShotPromptScreen)

    @pytest.mark.asyncio
    async def test_escape_dismisses_without_dispatch(self) -> None:
        """Pressing Escape in OneShotPromptScreen dismisses without starting an operation."""
        provider = FakePrDataProvider(plans=[])
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("x")
            await pilot.pause()
            await pilot.pause()

            assert isinstance(app.screen_stack[-1], OneShotPromptScreen)

            await pilot.press("escape")
            await pilot.pause()

            assert not isinstance(app.screen_stack[-1], OneShotPromptScreen)

    @pytest.mark.asyncio
    async def test_none_result_does_not_dispatch(self) -> None:
        """_on_one_shot_prompt_result with None does not start an operation."""
        provider = FakePrDataProvider(plans=[])
        filters = PrFilters.default()
        app = ErkDashApp(
            provider=provider, service=FakePrService(), filters=filters, refresh_interval=0
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Directly call the callback with None
            app._on_one_shot_prompt_result(None)

            # No operations should be running — status bar should have no ops
            status_bar = app._status_bar
            assert status_bar is not None
            assert not status_bar._operations
