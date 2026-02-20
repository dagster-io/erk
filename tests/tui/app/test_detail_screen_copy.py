"""Tests for PlanDetailScreen copy keyboard shortcuts."""

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk_shared.gateway.clipboard.fake import FakeClipboard
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row


class TestPlanDetailScreenCopyActions:
    """Tests for PlanDetailScreen copy keyboard shortcuts."""

    @pytest.mark.asyncio
    async def test_copy_prepare_shortcut_1(self) -> None:
        """Pressing '1' in detail screen copies prepare command."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
            clipboard=clipboard,
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

            # Press '1' to copy prepare command
            await pilot.press("1")
            await pilot.pause()

            assert clipboard.last_copied == "erk prepare 123"

    @pytest.mark.asyncio
    async def test_copy_submit_shortcut_3(self) -> None:
        """Pressing '3' in detail screen copies submit command."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            plans=[make_plan_row(123, "Test Plan")],
            clipboard=clipboard,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            await pilot.press("3")
            await pilot.pause()

            assert clipboard.last_copied == "erk plan submit 123"

    @pytest.mark.asyncio
    async def test_copy_checkout_shortcut_c_with_local_worktree(self) -> None:
        """Pressing 'c' in detail screen copies checkout command for local worktree."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Test Plan",
                    worktree_name="feature-123",
                    worktree_branch="feature-123",
                    exists_locally=True,
                )
            ],
            clipboard=clipboard,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            await pilot.press("c")
            await pilot.pause()

            assert clipboard.last_copied == "erk br co feature-123"

    @pytest.mark.asyncio
    async def test_copy_pr_checkout_shortcut_e(self) -> None:
        """Pressing 'e' in detail screen copies PR checkout command."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Test Plan",
                    pr_number=456,
                    exists_locally=False,
                )
            ],
            clipboard=clipboard,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            await pilot.press("e")
            await pilot.pause()

            assert clipboard.last_copied == "erk pr co 456"
