"""Tests for 'o' key open behavior and learn click handlers."""

import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.widgets.plan_table import PlanDataTable
from erk.tui.widgets.status_bar import StatusBar
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row


class TestOpenRow:
    """Tests for 'o' key open behavior (PR-first, then issue)."""

    @pytest.mark.asyncio
    async def test_o_opens_pr_when_available(self) -> None:
        """'o' key opens PR URL when PR is available."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Feature",
                    pr_number=456,
                    pr_url="https://github.com/test/repo/pull/456",
                    plan_url="https://github.com/test/repo/issues/123",
                )
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Press 'o' - should open PR (we can't actually open URL in test,
            # but we can check the status bar message)
            await pilot.press("o")
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            # Message should indicate PR was opened, not issue
            assert status_bar._message == "Opened PR #456"

    @pytest.mark.asyncio
    async def test_o_opens_issue_when_no_pr(self) -> None:
        """'o' key opens issue URL when no PR is available."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Feature",
                    plan_url="https://github.com/test/repo/issues/123",
                )
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("o")
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            # Message should indicate issue was opened
            assert status_bar._message == "Opened issue #123"


class TestOnLearnClicked:
    """Tests for on_learn_clicked event handler (learn cell click)."""

    @pytest.mark.asyncio
    async def test_learn_click_opens_pr_when_both_pr_and_issue_set(self) -> None:
        """Learn click opens PR URL when both PR and issue are set (PR priority)."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Feature",
                    plan_url="https://github.com/test/repo/issues/123",
                    learn_status="plan_completed",
                    learn_plan_issue=456,
                    learn_plan_pr=789,
                )
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Emit LearnClicked event for row 0
            table = app.query_one(PlanDataTable)
            table.post_message(PlanDataTable.LearnClicked(row_index=0))
            await pilot.pause()

            # Browser should have opened PR URL, not issue URL
            assert provider.browser.last_launched == "https://github.com/test/repo/pull/789"

            # Status bar should show PR message
            status_bar = app.query_one(StatusBar)
            assert status_bar._message == "Opened learn PR #789"

    @pytest.mark.asyncio
    async def test_learn_click_opens_issue_when_only_issue_set(self) -> None:
        """Learn click opens issue URL when only learn_plan_issue is set."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Feature",
                    plan_url="https://github.com/test/repo/issues/123",
                    learn_status="completed_with_plan",
                    learn_plan_issue=456,
                )
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Emit LearnClicked event for row 0
            table = app.query_one(PlanDataTable)
            table.post_message(PlanDataTable.LearnClicked(row_index=0))
            await pilot.pause()

            # Browser should have opened issue URL
            assert provider.browser.last_launched == "https://github.com/test/repo/issues/456"

            # Status bar should show issue message
            status_bar = app.query_one(StatusBar)
            assert status_bar._message == "Opened learn issue #456"

    @pytest.mark.asyncio
    async def test_learn_click_does_nothing_when_no_learn_data(self) -> None:
        """Learn click does nothing when no learn fields are set."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Feature",
                    plan_url="https://github.com/test/repo/issues/123",
                )
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Emit LearnClicked event for row 0
            table = app.query_one(PlanDataTable)
            table.post_message(PlanDataTable.LearnClicked(row_index=0))
            await pilot.pause()

            # Browser should NOT have been called
            assert provider.browser.last_launched is None

    @pytest.mark.asyncio
    async def test_learn_click_does_nothing_when_no_issue_url(self) -> None:
        """Learn click does nothing when issue_url is empty (URL can't be constructed)."""
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Feature",
                    plan_url="",  # Empty string to represent no issue URL
                    learn_status="plan_completed",
                    learn_plan_pr=789,
                )
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Emit LearnClicked event for row 0
            table = app.query_one(PlanDataTable)
            table.post_message(PlanDataTable.LearnClicked(row_index=0))
            await pilot.pause()

            # Browser should NOT have been called (can't construct URL)
            assert provider.browser.last_launched is None
