"""Tests for ErkDashApp using Textual Pilot."""

import pytest
from erk_shared.integrations.clipboard.fake import FakeClipboard

from erk.tui.app import ErkDashApp, HelpScreen, PlanDetailScreen
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

            assert clipboard.last_copied == "erk pr co 456"

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


class TestFilterMode:
    """Tests for '/' filter mode functionality."""

    @pytest.mark.asyncio
    async def test_slash_activates_filter_mode(self) -> None:
        """Pressing '/' shows filter input and focuses it."""
        provider = FakePlanDataProvider([make_plan_row(123, "Plan A")])
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Press / to activate filter
            await pilot.press("slash")
            await pilot.pause()

            # Filter input should be visible and focused
            from textual.widgets import Input

            filter_input = app.query_one("#filter-input", Input)
            assert filter_input.has_class("visible")
            assert app.focused == filter_input

    @pytest.mark.asyncio
    async def test_filter_narrows_results(self) -> None:
        """Typing in filter input narrows displayed results."""
        provider = FakePlanDataProvider(
            [
                make_plan_row(123, "Add user authentication"),
                make_plan_row(456, "Fix login bug"),
                make_plan_row(789, "Refactor database"),
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Verify all rows are displayed initially
            assert len(app._rows) == 3

            # Activate filter and type query
            await pilot.press("slash")
            await pilot.pause()
            await pilot.press("l", "o", "g", "i", "n")
            await pilot.pause()

            # Only matching row should be visible
            assert len(app._rows) == 1
            assert app._rows[0].issue_number == 456

    @pytest.mark.asyncio
    async def test_escape_clears_then_exits(self) -> None:
        """First escape clears text, second exits filter mode."""
        provider = FakePlanDataProvider([make_plan_row(123, "Plan A")])
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Activate filter and type
            await pilot.press("slash")
            await pilot.pause()
            await pilot.press("t", "e", "s", "t")
            await pilot.pause()

            from textual.widgets import Input

            from erk.tui.filtering.types import FilterMode

            filter_input = app.query_one("#filter-input", Input)
            assert filter_input.value == "test"
            assert app._filter_state.mode == FilterMode.ACTIVE

            # First escape clears text
            await pilot.press("escape")
            await pilot.pause()
            assert filter_input.value == ""
            assert app._filter_state.mode == FilterMode.ACTIVE

            # Second escape exits filter mode
            await pilot.press("escape")
            await pilot.pause()
            assert app._filter_state.mode == FilterMode.INACTIVE
            assert not filter_input.has_class("visible")

    @pytest.mark.asyncio
    async def test_enter_returns_focus_to_table(self) -> None:
        """Pressing Enter in filter input returns focus to table."""
        provider = FakePlanDataProvider([make_plan_row(123, "Plan A")])
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Activate filter
            await pilot.press("slash")
            await pilot.pause()

            from textual.widgets import Input

            filter_input = app.query_one("#filter-input", Input)
            assert app.focused == filter_input

            # Press Enter to return to table
            await pilot.press("enter")
            await pilot.pause()

            table = app.query_one(PlanDataTable)
            assert app.focused == table

    @pytest.mark.asyncio
    async def test_filter_by_issue_number(self) -> None:
        """Filter can match by issue number."""
        provider = FakePlanDataProvider(
            [
                make_plan_row(123, "Plan A"),
                make_plan_row(456, "Plan B"),
                make_plan_row(789, "Plan C"),
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("slash")
            await pilot.pause()
            await pilot.press("4", "5", "6")
            await pilot.pause()

            assert len(app._rows) == 1
            assert app._rows[0].issue_number == 456

    @pytest.mark.asyncio
    async def test_filter_by_pr_number(self) -> None:
        """Filter can match by PR number."""
        provider = FakePlanDataProvider(
            [
                make_plan_row(1, "Plan A", pr_number=100),
                make_plan_row(2, "Plan B", pr_number=200),
                make_plan_row(3, "Plan C"),
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("slash")
            await pilot.pause()
            await pilot.press("2", "0", "0")
            await pilot.pause()

            assert len(app._rows) == 1
            assert app._rows[0].issue_number == 2


class TestOpenRow:
    """Tests for Enter/o key open behavior (PR-first, then issue)."""

    @pytest.mark.asyncio
    async def test_enter_opens_pr_when_available(self) -> None:
        """Enter opens PR URL when PR is available."""
        provider = FakePlanDataProvider(
            [
                make_plan_row(
                    123,
                    "Feature",
                    pr_number=456,
                    pr_url="https://github.com/test/repo/pull/456",
                    issue_url="https://github.com/test/repo/issues/123",
                )
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Press Enter - should open PR (we can't actually open URL in test,
            # but we can check the status bar message)
            await pilot.press("enter")
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            # Message should indicate PR was opened, not issue
            assert status_bar._message == "Opened PR #456"

    @pytest.mark.asyncio
    async def test_enter_opens_issue_when_no_pr(self) -> None:
        """Enter opens issue URL when no PR is available."""
        provider = FakePlanDataProvider(
            [
                make_plan_row(
                    123,
                    "Feature",
                    issue_url="https://github.com/test/repo/issues/123",
                )
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("enter")
            await pilot.pause()

            status_bar = app.query_one(StatusBar)
            # Message should indicate issue was opened
            assert status_bar._message == "Opened issue #123"


class TestPlanDetailScreen:
    """Tests for PlanDetailScreen modal."""

    @pytest.mark.asyncio
    async def test_space_opens_detail_screen(self) -> None:
        """Pressing space opens the plan detail modal."""
        provider = FakePlanDataProvider(
            [make_plan_row(123, "Test Plan", pr_number=456, pr_title="Test PR")]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Press space to show detail
            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            # Detail screen should be in the screen stack
            assert len(app.screen_stack) > 1
            assert isinstance(app.screen_stack[-1], PlanDetailScreen)

    @pytest.mark.asyncio
    async def test_detail_modal_dismisses_on_escape(self) -> None:
        """Detail modal closes when pressing escape."""
        provider = FakePlanDataProvider([make_plan_row(123, "Test Plan")])
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Open detail modal
            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            # Should be showing detail
            assert isinstance(app.screen_stack[-1], PlanDetailScreen)

            # Press escape to close
            await pilot.press("escape")
            await pilot.pause()

            # Should be back to main screen
            assert not isinstance(app.screen_stack[-1], PlanDetailScreen)

    @pytest.mark.asyncio
    async def test_detail_modal_dismisses_on_q(self) -> None:
        """Detail modal closes when pressing q."""
        provider = FakePlanDataProvider([make_plan_row(123, "Test Plan")])
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            assert isinstance(app.screen_stack[-1], PlanDetailScreen)

            await pilot.press("q")
            await pilot.pause()

            assert not isinstance(app.screen_stack[-1], PlanDetailScreen)

    @pytest.mark.asyncio
    async def test_detail_modal_dismisses_on_space(self) -> None:
        """Detail modal closes when pressing space again."""
        provider = FakePlanDataProvider([make_plan_row(123, "Test Plan")])
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            assert isinstance(app.screen_stack[-1], PlanDetailScreen)

            await pilot.press("space")
            await pilot.pause()

            assert not isinstance(app.screen_stack[-1], PlanDetailScreen)

    @pytest.mark.asyncio
    async def test_detail_modal_displays_full_title(self) -> None:
        """Detail modal shows full untruncated title."""
        long_title = (
            "This is a very long plan title that would normally be truncated "
            "in the table view but should be fully visible in the detail modal"
        )
        provider = FakePlanDataProvider([make_plan_row(123, long_title)])
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            detail_screen = app.screen_stack[-1]
            assert isinstance(detail_screen, PlanDetailScreen)
            # The modal stores the full row data which contains full_title
            assert detail_screen._row.full_title == long_title

    @pytest.mark.asyncio
    async def test_detail_modal_shows_pr_info_when_linked(self) -> None:
        """Detail modal shows PR information when PR is linked."""
        provider = FakePlanDataProvider(
            [
                make_plan_row(
                    123,
                    "Test Plan",
                    pr_number=456,
                    pr_title="Test PR Title",
                    pr_state="OPEN",
                    pr_url="https://github.com/test/repo/pull/456",
                )
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider, filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            detail_screen = app.screen_stack[-1]
            assert isinstance(detail_screen, PlanDetailScreen)
            assert detail_screen._row.pr_number == 456
            assert detail_screen._row.pr_title == "Test PR Title"
            assert detail_screen._row.pr_state == "OPEN"
