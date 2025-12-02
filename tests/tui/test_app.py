"""Tests for ErkDashApp using Textual Pilot."""

import pytest
from erk_shared.integrations.browser.fake import FakeBrowserLauncher
from erk_shared.integrations.clipboard.fake import FakeClipboard

from erk.core.context import ErkContext
from erk.tui.app import ErkDashApp, HelpScreen
from erk.tui.context import ErkDashContext
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


class TestCopyCheckoutCommand:
    """Tests for the 'c' key copy checkout command functionality."""

    @pytest.mark.asyncio
    async def test_copy_checkout_with_local_worktree(self) -> None:
        """Pressing 'c' on row with local worktree copies 'erk co {worktree_name}'."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Feature",
                    worktree_name="feature-branch",
                    exists_locally=True,
                )
            ],
            clipboard=clipboard,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            # Wait for data to load
            await pilot.pause()
            await pilot.pause()

            # Press 'c' to copy checkout command
            await pilot.press("c")
            await pilot.pause()

            # Should have copied the worktree checkout command
            assert clipboard.last_copied == "erk co feature-branch"

    @pytest.mark.asyncio
    async def test_copy_checkout_with_only_pr(self) -> None:
        """Pressing 'c' on row with only PR copies 'erk pr co #{pr_number}'."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Feature",
                    pr_number=456,
                    exists_locally=False,
                )
            ],
            clipboard=clipboard,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("c")
            await pilot.pause()

            assert clipboard.last_copied == "erk pr co #456"

    @pytest.mark.asyncio
    async def test_copy_checkout_with_neither_shows_error(self) -> None:
        """Pressing 'c' on row with neither worktree nor PR shows error message."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Feature",
                    exists_locally=False,
                )
            ],
            clipboard=clipboard,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("c")
            await pilot.pause()

            # No copy should have been made
            assert clipboard.last_copied is None
            # Status bar should show error message (tested via internal state)
            status_bar = app.query_one(StatusBar)
            assert status_bar._message == "No worktree or PR available for checkout"

    @pytest.mark.asyncio
    async def test_copy_checkout_prefers_local_worktree_over_pr(self) -> None:
        """When both worktree and PR exist, prefers local worktree command."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Feature",
                    worktree_name="feature-branch",
                    exists_locally=True,
                    pr_number=456,
                )
            ],
            clipboard=clipboard,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("c")
            await pilot.pause()

            # Should prefer worktree over PR
            assert clipboard.last_copied == "erk co feature-branch"

    @pytest.mark.asyncio
    async def test_copy_checkout_clipboard_failure_shows_fallback(self) -> None:
        """When clipboard fails, shows fallback message with command."""
        clipboard = FakeClipboard(should_succeed=False)
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Feature",
                    worktree_name="feature-branch",
                    exists_locally=True,
                )
            ],
            clipboard=clipboard,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("c")
            await pilot.pause()

            # Clipboard was called but failed
            assert clipboard.last_copied == "erk co feature-branch"
            # Status bar should show fallback message
            status_bar = app.query_one(StatusBar)
            assert (
                status_bar._message == "Clipboard unavailable. Copy manually: erk co feature-branch"
            )

    @pytest.mark.asyncio
    async def test_copy_checkout_success_shows_confirmation(self) -> None:
        """When clipboard succeeds, shows confirmation message."""
        clipboard = FakeClipboard(should_succeed=True)
        provider = FakePlanDataProvider(
            plans=[
                make_plan_row(
                    123,
                    "Feature",
                    worktree_name="feature-branch",
                    exists_locally=True,
                )
            ],
            clipboard=clipboard,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("c")
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            assert status_bar._message == "Copied: erk co feature-branch"


class TestErkDashAppBrowserActions:
    """Tests for browser launching via injected ErkDashContext."""

    @pytest.mark.asyncio
    async def test_open_issue_uses_injected_browser(self) -> None:
        """Pressing 'o' on a row launches issue URL via injected browser."""
        provider = FakePlanDataProvider(
            [make_plan_row(123, "Test Plan", issue_url="https://github.com/test/repo/issues/123")]
        )
        filters = PlanFilters.default()

        # Create dash_ctx with fake browser
        ctx = ErkContext.for_test()
        browser = FakeBrowserLauncher()
        dash_ctx = ErkDashContext.for_test(ctx, browser=browser)

        app = ErkDashApp(provider, filters, refresh_interval=0, dash_ctx=dash_ctx)

        async with app.run_test() as pilot:
            # Wait for data load
            await pilot.pause()
            await pilot.pause()

            # Select first row and press 'o' to open issue
            await pilot.press("o")
            await pilot.pause()

            # Browser should have been called with issue URL
            assert browser.launched_urls == ["https://github.com/test/repo/issues/123"]

    @pytest.mark.asyncio
    async def test_open_pr_uses_injected_browser(self) -> None:
        """Pressing 'p' on a row launches PR URL via injected browser."""
        provider = FakePlanDataProvider(
            [
                make_plan_row(
                    123,
                    "Test Plan",
                    pr_number=456,
                    pr_url="https://github.com/test/repo/pull/456",
                )
            ]
        )
        filters = PlanFilters.default()

        # Create dash_ctx with fake browser
        ctx = ErkContext.for_test()
        browser = FakeBrowserLauncher()
        dash_ctx = ErkDashContext.for_test(ctx, browser=browser)

        app = ErkDashApp(provider, filters, refresh_interval=0, dash_ctx=dash_ctx)

        async with app.run_test() as pilot:
            # Wait for data load
            await pilot.pause()
            await pilot.pause()

            # Select first row and press 'p' to open PR
            await pilot.press("p")
            await pilot.pause()

            # Browser should have been called with PR URL
            assert browser.launched_urls == ["https://github.com/test/repo/pull/456"]

    @pytest.mark.asyncio
    async def test_enter_on_row_opens_issue(self) -> None:
        """Pressing Enter on a row launches issue URL via injected browser."""
        provider = FakePlanDataProvider(
            [make_plan_row(123, "Test Plan", issue_url="https://github.com/test/repo/issues/123")]
        )
        filters = PlanFilters.default()

        ctx = ErkContext.for_test()
        browser = FakeBrowserLauncher()
        dash_ctx = ErkDashContext.for_test(ctx, browser=browser)

        app = ErkDashApp(provider, filters, refresh_interval=0, dash_ctx=dash_ctx)

        async with app.run_test() as pilot:
            # Wait for data load
            await pilot.pause()
            await pilot.pause()

            # Press Enter to open selected issue
            await pilot.press("enter")
            await pilot.pause()

            # Browser should have been called with issue URL
            assert browser.launched_urls == ["https://github.com/test/repo/issues/123"]

    @pytest.mark.asyncio
    async def test_browser_not_called_when_no_url(self) -> None:
        """Browser is not called when row has no PR URL."""
        provider = FakePlanDataProvider(
            [make_plan_row(123, "Test Plan", pr_number=None, pr_url=None)]
        )
        filters = PlanFilters.default()

        ctx = ErkContext.for_test()
        browser = FakeBrowserLauncher()
        dash_ctx = ErkDashContext.for_test(ctx, browser=browser)

        app = ErkDashApp(provider, filters, refresh_interval=0, dash_ctx=dash_ctx)

        async with app.run_test() as pilot:
            # Wait for data load
            await pilot.pause()
            await pilot.pause()

            # Press 'p' but there's no PR
            await pilot.press("p")
            await pilot.pause()

            # Browser should NOT have been called
            assert browser.launched_urls == []
