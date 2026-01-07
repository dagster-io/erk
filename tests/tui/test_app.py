"""Tests for ErkDashApp using Textual Pilot."""

from pathlib import Path

import pytest

from erk.tui.app import ErkDashApp, HelpScreen, PlanDetailScreen
from erk.tui.data.types import PlanFilters
from erk.tui.widgets.plan_table import PlanDataTable
from erk.tui.widgets.status_bar import StatusBar
from erk_shared.gateway.clipboard.fake import FakeClipboard
from tests.fakes.plan_data_provider import FakePlanDataProvider, make_plan_row


class TestErkDashAppCompose:
    """Tests for app composition and layout."""

    @pytest.mark.asyncio
    async def test_app_has_required_widgets(self) -> None:
        """App composes all required widgets."""
        provider = FakePlanDataProvider()
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

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


class TestErkDashAppNavigation:
    """Tests for keyboard navigation."""

    @pytest.mark.asyncio
    async def test_quit_on_q(self) -> None:
        """Pressing q quits the app."""
        provider = FakePlanDataProvider()
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.press("q")
            # App should have exited (no assertion needed - would hang if not)

    @pytest.mark.asyncio
    async def test_quit_on_escape(self) -> None:
        """Pressing escape quits the app."""
        provider = FakePlanDataProvider()
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.press("escape")
            # App should have exited

    @pytest.mark.asyncio
    async def test_help_on_question_mark(self) -> None:
        """Pressing ? shows help screen."""
        provider = FakePlanDataProvider()
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

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
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

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


class TestClosePlanViaCommandPalette:
    """Tests for close plan functionality via command palette.

    Note: The top-level 'c' binding was removed. Close plan is now accessible
    via the command palette in the plan detail modal (Space → Ctrl+P → "Close Plan").
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


class TestFilterMode:
    """Tests for '/' filter mode functionality."""

    @pytest.mark.asyncio
    async def test_slash_activates_filter_mode(self) -> None:
        """Pressing '/' shows filter input and focuses it."""
        provider = FakePlanDataProvider([make_plan_row(123, "Plan A")])
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

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
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

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
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

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
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

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
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

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
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()

            await pilot.press("slash")
            await pilot.pause()
            await pilot.press("2", "0", "0")
            await pilot.pause()

            assert len(app._rows) == 1
            assert app._rows[0].issue_number == 2


class TestOpenRow:
    """Tests for 'o' key open behavior (PR-first, then issue)."""

    @pytest.mark.asyncio
    async def test_o_opens_pr_when_available(self) -> None:
        """'o' key opens PR URL when PR is available."""
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
            [
                make_plan_row(
                    123,
                    "Feature",
                    issue_url="https://github.com/test/repo/issues/123",
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


class TestPlanDetailScreen:
    """Tests for PlanDetailScreen modal."""

    @pytest.mark.asyncio
    async def test_space_opens_detail_screen(self) -> None:
        """Pressing space opens the plan detail modal."""
        provider = FakePlanDataProvider(
            [make_plan_row(123, "Test Plan", pr_number=456, pr_title="Test PR")]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

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
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

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
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

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
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

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
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

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
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

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


class TestPlanDetailScreenCopyActions:
    """Tests for PlanDetailScreen copy keyboard shortcuts."""

    @pytest.mark.asyncio
    async def test_copy_implement_shortcut_1(self) -> None:
        """Pressing '1' in detail screen copies implement command."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            [make_plan_row(123, "Test Plan")],
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

            # Press '1' to copy implement command
            await pilot.press("1")
            await pilot.pause()

            assert clipboard.last_copied == "erk implement 123"

    @pytest.mark.asyncio
    async def test_copy_implement_dangerous_shortcut_2(self) -> None:
        """Pressing '2' in detail screen copies implement --dangerous command."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            [make_plan_row(123, "Test Plan")],
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

            await pilot.press("2")
            await pilot.pause()

            assert clipboard.last_copied == "erk implement 123 --dangerous"

    @pytest.mark.asyncio
    async def test_copy_implement_yolo_shortcut_3(self) -> None:
        """Pressing '3' in detail screen copies implement --yolo command."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            [make_plan_row(123, "Test Plan")],
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

            assert clipboard.last_copied == "erk implement 123 --yolo"

    @pytest.mark.asyncio
    async def test_copy_submit_shortcut_4(self) -> None:
        """Pressing '4' in detail screen copies submit command."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            [make_plan_row(123, "Test Plan")],
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

            await pilot.press("4")
            await pilot.pause()

            assert clipboard.last_copied == "erk plan submit 123"

    @pytest.mark.asyncio
    async def test_copy_checkout_shortcut_c_with_local_worktree(self) -> None:
        """Pressing 'c' in detail screen copies checkout command for local worktree."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            [
                make_plan_row(
                    123,
                    "Test Plan",
                    worktree_name="feature-123",
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

            assert clipboard.last_copied == "erk co feature-123"

    @pytest.mark.asyncio
    async def test_copy_pr_checkout_shortcut_e(self) -> None:
        """Pressing 'e' in detail screen copies PR checkout command."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            [
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


class TestCommandPaletteFromMain:
    """Tests for command palette from main list view.

    Ctrl+P opens the command palette directly from main list (no detail modal).
    The palette shows plan-specific commands for the selected row.
    """

    @pytest.mark.asyncio
    async def test_execute_palette_command_copy_implement(self) -> None:
        """Execute palette command copies implement command."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider(
            [make_plan_row(123, "Test Plan")],
            clipboard=clipboard,
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Execute command directly (simulates palette selection)
            app.execute_palette_command("copy_implement")

            assert clipboard.last_copied == "erk implement 123"

    @pytest.mark.asyncio
    async def test_execute_palette_command_open_pr(self) -> None:
        """Execute palette command opens PR in browser."""
        provider = FakePlanDataProvider(
            [
                make_plan_row(
                    123, "Test Plan", pr_number=456, pr_url="https://github.com/test/pr/456"
                )
            ]
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Execute open_pr command
            app.execute_palette_command("open_pr")

            assert provider.browser.last_launched == "https://github.com/test/pr/456"

    @pytest.mark.asyncio
    async def test_execute_palette_command_with_no_selection(self) -> None:
        """Execute palette command with no selection does nothing."""
        clipboard = FakeClipboard()
        provider = FakePlanDataProvider([], clipboard=clipboard)
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Execute command with no rows selected
            app.execute_palette_command("copy_implement")

            # Nothing should be copied
            assert clipboard.last_copied is None

    @pytest.mark.asyncio
    async def test_space_opens_detail_screen(self) -> None:
        """Space opens detail screen without palette."""
        provider = FakePlanDataProvider([make_plan_row(123, "Test Plan")])
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            # Press space (regular detail view)
            await pilot.press("space")
            await pilot.pause()
            await pilot.pause()

            detail_screen = app.screen_stack[-1]
            assert isinstance(detail_screen, PlanDetailScreen)
            # The flag should NOT be set (space = just detail, no palette)
            assert detail_screen._auto_open_palette is False


class TestExecutePaletteCommandLandPR:
    """Tests for execute_palette_command('land_pr').

    Note: land_pr uses streaming output via subprocess. These tests verify
    the guard conditions. The guard condition test (no PR) doesn't invoke
    subprocess, so it can be tested without a real directory. Testing the
    positive case with actual subprocess execution is done via integration tests.
    """

    @pytest.mark.asyncio
    async def test_execute_palette_command_land_pr_with_no_pr(self) -> None:
        """Execute palette command land_pr does nothing if no PR."""
        provider = FakePlanDataProvider(
            [make_plan_row(123, "Test Plan")]  # No pr_number
        )
        filters = PlanFilters.default()
        app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.pause()

            initial_stack_len = len(app.screen_stack)

            # Execute land_pr command with no PR
            app.execute_palette_command("land_pr")
            await pilot.pause()

            # Should not have pushed a new screen
            assert len(app.screen_stack) == initial_stack_len


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
        provider = FakePlanDataProvider(
            [make_plan_row(123, "Test Plan")],
            repo_root=tmp_path,
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
        provider = FakePlanDataProvider(
            [make_plan_row(123, "Test Plan")],
            repo_root=tmp_path,
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
        provider = FakePlanDataProvider(
            [make_plan_row(123, "Test Plan")],
            repo_root=tmp_path,
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
        provider = FakePlanDataProvider(
            [make_plan_row(123, "Test Plan")],
            repo_root=tmp_path,
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
    """Tests for run_close_plan_in_process functionality.

    This tests the in-process close plan action which uses the HTTP client
    directly rather than spawning a subprocess.
    """

    @pytest.mark.asyncio
    async def test_close_plan_in_process_creates_output_panel(self) -> None:
        """In-process close plan creates and mounts output panel."""
        provider = FakePlanDataProvider(
            [
                make_plan_row(
                    123,
                    "Test Plan",
                    issue_url="https://github.com/test/repo/issues/123",
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
            [
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
            assert provider._plans[0].issue_number == 456
